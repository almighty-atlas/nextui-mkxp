# SPDX-License-Identifier: MIT
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SupervisorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / 'session'
        cls.production = Path(cls.temp.name) / 'production'
        for output, flags in ((cls.binary, ['-DRMXP_TEST_INPUT']), (cls.production, [])):
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2', *flags,
                            str(ROOT / 'native/rmxp-session.c'), '-o', str(output)], check=True)

    def spawn(self, code, events=False):
        read_fd, write_fd = os.pipe()
        args = [str(self.binary), '--grace-ms', '150', '--hold-ms', '500']
        if events:
            args += ['--test-fd', str(read_fd), '--keys', '314', '315']
        proc = subprocess.Popen(args + ['--', 'python3', '-u', '-c', code],
                                pass_fds=(read_fd,) if events else (), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=False)
        os.close(read_fd)
        def close_pipe():
            try:
                os.close(write_fd)
            except OSError:
                pass
        self.addCleanup(close_pipe)
        def cleanup():
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate(timeout=2)
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
        self.addCleanup(cleanup)
        return proc, write_fd

    def ready(self, proc):
        self.assertTrue(select.select([proc.stdout], [], [], 3)[0], 'child startup timed out')
        self.assertEqual(proc.stdout.readline(), b'READY\n')

    def event(self, fd, code, value, kind=1):
        os.write(fd, struct.pack('@llHHi', 0, 0, kind, code, value))

    def release(self, fd):
        self.event(fd, 314, 0)
        self.event(fd, 315, 0)

    def press(self, fd):
        self.event(fd, 314, 1)
        self.event(fd, 315, 1)

    def test_real_wait_status_distinguishes_exit_from_signal(self):
        for code, result in [('raise SystemExit(143)', b'RMXP_RESULT=exit CODE=143'),
                             ('import os,signal; os.kill(os.getpid(),signal.SIGTERM)', b'RMXP_RESULT=signal SIGNAL=15')]:
            proc, _ = self.spawn(code)
            _, log = proc.communicate(timeout=3)
            self.assertEqual(proc.returncode, 143)
            self.assertIn(result, log)

    def test_normal_exit_and_exec_failure(self):
        result = subprocess.run([str(self.production), '--', '/bin/true'], capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'RMXP_RESULT=exit CODE=0 REASON=natural', result.stderr)
        result = subprocess.run([str(self.production), '--', '/missing-private-executable'], capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 127)
        self.assertNotIn(b'missing-private-executable', result.stderr)

    def test_supervisor_signal_escalates_ignoring_child(self):
        proc, _ = self.spawn('import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print("READY"); time.sleep(20)')
        self.ready(proc)
        start = time.monotonic()
        proc.terminate()
        _, log = proc.communicate(timeout=3)
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual(proc.returncode, 137)
        self.assertIn(b'RMXP_STOP=kill', log)
        self.assertIn(b'REASON=supervisor_signal', log)

    def test_hold_chord_requests_graceful_exit(self):
        proc, fd = self.spawn('import signal,time; signal.signal(signal.SIGTERM,lambda *a: exit(0)); print("READY"); time.sleep(20)', events=True)
        self.ready(proc)
        self.release(fd)
        self.press(fd)
        _, log = proc.communicate(timeout=3)
        self.assertEqual(proc.returncode, 0)
        self.assertIn(b'REASON=chord', log)
        self.assertNotIn(b'RMXP_STOP=kill', log)

    def test_startup_hold_short_press_and_repeat_do_not_exit(self):
        proc, fd = self.spawn('import time; print("READY"); time.sleep(20)', events=True)
        self.ready(proc)
        self.press(fd)
        time.sleep(0.65)
        self.assertIsNone(proc.poll())
        self.release(fd)
        self.event(fd, 314, 2)
        self.event(fd, 315, 2)
        time.sleep(0.55)
        self.assertIsNone(proc.poll())
        self.press(fd)
        time.sleep(0.15)
        self.release(fd)
        time.sleep(0.55)
        self.assertIsNone(proc.poll())
        proc.terminate()
        proc.communicate(timeout=3)

    def test_syn_dropped_disarms_until_release(self):
        proc, fd = self.spawn('import time; print("READY"); time.sleep(20)', events=True)
        self.ready(proc)
        self.release(fd)
        self.press(fd)
        self.event(fd, 3, 0, kind=0)  # SYN_DROPPED
        self.event(fd, 0, 0, kind=0)  # SYN_REPORT; synthetic fd cannot resync
        time.sleep(0.65)
        self.assertIsNone(proc.poll())
        self.release(fd)
        self.press(fd)
        _, log = proc.communicate(timeout=3)
        self.assertIn(b'REASON=chord', log)

    def test_invalid_input_does_not_launch_and_test_option_is_absent(self):
        for options in (['--test-fd', '0', '--keys', '314', '315'],
                        ['--input', '/dev/null', '--keys', '314', '315'],
                        ['--hold-ms', '1'], ['--keys', '1', '1']):
            result = subprocess.run([str(self.production), *options, '--', '/bin/echo', 'CHILD_LAUNCHED'],
                                    capture_output=True, timeout=3)
            self.assertEqual(result.returncode, 125)
            self.assertEqual(result.stdout, b'')

    def test_input_disconnect_disarms_without_killing_game(self):
        proc, fd = self.spawn('import time; print("READY"); time.sleep(20)', events=True)
        self.ready(proc)
        self.release(fd)
        self.press(fd)
        os.close(fd)
        time.sleep(0.65)
        self.assertIsNone(proc.poll())
        proc.terminate()
        _, log = proc.communicate(timeout=3)
        self.assertIn(b'RMXP_INPUT=lost', log)
        self.assertNotIn(b'REASON=chord', log)

    def test_owned_descendant_cleanup_does_not_signal_unrelated_process(self):
        unrelated = subprocess.Popen(['sleep', '20'])
        self.addCleanup(lambda: unrelated.wait(timeout=3))
        self.addCleanup(unrelated.terminate)
        code = ('import subprocess; p=subprocess.Popen(["sleep","20"], '
                'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid)')
        proc, _ = self.spawn(code)
        out, log = proc.communicate(timeout=3)
        descendant = int(out.strip())
        self.assertEqual(proc.returncode, 0)
        self.assertIn(b'REASON=natural', log)
        self.assertIsNone(unrelated.poll())
        self.assertFalse(Path('/proc', str(descendant)).exists())


if __name__ == '__main__':
    unittest.main()
