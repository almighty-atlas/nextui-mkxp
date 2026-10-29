# SPDX-License-Identifier: MIT
"""Offline simulated API/launcher tests. Never renders or contacts hardware."""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
PAK = BASE / 'Tools/h700/RMXP-Video-Test.pak'


class VideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary = Path(cls.temp.name) / 'mock-video-host-only'
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        '-I', str(BASE/'tests/include'), str(BASE/'triangle.c'),
                        str(BASE/'tests/mock_api.c'), '-o', str(cls.binary)], check=True)

    def run_mock(self, case='', **extra):
        env = {'SDL_VIDEODRIVER': 'mali', 'MOCK_CASE': case, **extra}
        result = subprocess.run([str(self.binary)], env=env, capture_output=True,
                                text=True, timeout=3)
        self.assertEqual(result.stderr, '')
        self.assertLess(len(result.stdout), 4096)
        self.assertLessEqual(len(result.stdout.splitlines()), 24)
        self.assertTrue(all(len(s)<=180 for s in result.stdout.splitlines()))
        self.assertNotIn('PASS', result.stdout)
        self.assertIn('exit_owner_verification_required', result.stdout)
        return result

    def test_draws_animated_shader_triangle_and_stops_at_deadline(self):
        r = self.run_mock()
        self.assertEqual(r.returncode, 0)
        self.assertIn('stage=draw_end code=0 frames=625 elapsed_ms=5000', r.stdout)
        self.assertIn('cleanup=ok swaps=625 draws=625 shaders_deleted=2', r.stdout)

    def test_each_failure_stage_cleans_up(self):
        for case, code in {'init_fail':12,'wrong_driver':13,'attribute_fail':14,
                           'window_fail':15,'context_fail':16,'current_fail':17,
                           'egl_fail':18,'bad_gl':19,'shader_fail':20,'link_fail':21,
                           'uniform_fail':22,'buffer_fail':23,'bad_size':24,
                           'draw_fail':25,'swap_fail':27}.items():
            with self.subTest(case=case):
                r=self.run_mock(case)
                self.assertEqual(r.returncode,code)
                self.assertIn('cleanup=ok',r.stdout)
                self.assertNotIn('stage=draw_end code=0',r.stdout)

    def test_quit_and_own_signals(self):
        for case in ('quit','term','int'):
            with self.subTest(case=case):
                r=self.run_mock(case)
                self.assertEqual(r.returncode,30)
                self.assertIn('cleanup=ok swaps=2 draws=2',r.stdout)

    def test_stalled_clock_is_bounded_and_wrap_is_supported(self):
        r=self.run_mock('clock_stuck')
        self.assertEqual(r.returncode,26)
        self.assertIn('frames=625 elapsed_ms=0',r.stdout)
        self.assertEqual(self.run_mock('wrap').returncode,0)
        self.assertEqual(self.run_mock('event_flood').returncode,0)

    def test_metadata_sanitized_and_no_backend_fallback(self):
        r=self.run_mock('long_metadata')
        self.assertEqual(r.returncode,0)
        self.assertIn('line?control?',r.stdout)
        self.assertNotIn('\x01',r.stdout)
        self.assertEqual(self.run_mock(SDL_VIDEODRIVER='kmsdrm').returncode,11)
        self.assertEqual(self.run_mock(SSH_CONNECTION='PRIVATE_SENTINEL').returncode,31)
        self.assertNotIn('PRIVATE_SENTINEL',self.run_mock(SSH_TTY='PRIVATE_SENTINEL').stdout)

    def test_launcher_guards_and_owned_log_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            card=root/'card'
            pak=root/'RMXP-Video-Test.pak'
            shutil.copytree(PAK,pak)
            script=pak/'launch.sh'
            source=script.read_text().replace('/mnt/SDCARD',str(card))
            # Device checks point to a harmless existing character device in
            # this host-only test copy. Production has fixed fb0/ION paths.
            source=source.replace('/dev/fb0','/dev/null').replace('/dev/ion','/dev/null')
            script.write_text(source)
            toolbin=root/'bin';toolbin.mkdir()
            for tool in ('dirname','od','awk','mkdir'):
                os.symlink(shutil.which(tool),toolbin/tool)
            user=card/'.userdata/h700'
            env={'PATH':str(toolbin),'PLATFORM':'h700','DEVICE':'rg35xxpro',
                 'SDCARD_PATH':str(card),'USERDATA_PATH':str(user),
                 'SYSTEM_PATH':str(card/'.system/h700'),'SDL_VIDEODRIVER':'mali'}
            def run(**update):
                return subprocess.run(['/bin/sh',str(script)],env={**env,**update},
                                      text=True,capture_output=True,timeout=3)
            self.assertEqual(run(SSH_CONNECTION='secret').returncode,81)
            self.assertEqual(run(PLATFORM='desktop').returncode,82)
            self.assertEqual(run().returncode,90)  # committed source-only guard
            self.assertFalse(user.exists())
            (pak/'SOURCE_ONLY').unlink()
            self.assertEqual(run().returncode,91)  # no binary
            (pak/'bin').mkdir()
            binary=pak/'bin/triangle'
            shutil.copyfile(self.binary,binary);binary.chmod(0o755)
            self.assertEqual(run().returncode,93)  # real host x86 ELF rejected
            self.assertFalse(user.exists())
            # Explicit metadata simulation to exercise final exec/logging path;
            # no simulated ELF is ever placed in a distributable package.
            (toolbin/'od').unlink()
            (toolbin/'od').write_text('#!/bin/sh\nprintf "127 69 76 70 2 1 1 0 0 0 0 0 0 0 0 0 3 0 183 0\\n"\n')
            (toolbin/'od').chmod(0o755)
            logdir=user/'RMXP-Video-Test';logdir.mkdir(parents=True)
            external=root/'unowned';external.write_text('preserve')
            (logdir/'latest.log').symlink_to(external)
            self.assertEqual(run().returncode,95)
            self.assertEqual(external.read_text(),'preserve')
            (logdir/'latest.log').unlink()
            r=run()
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertIn('MOCK_NOT_REAL_GPU',(logdir/'latest.log').read_text())
            self.assertEqual(external.read_text(),'preserve')
            noisy=run(MOCK_CASE='noisy')
            self.assertNotEqual(noisy.returncode,0)
            self.assertLessEqual((logdir/'latest.log').stat().st_size,16*1024)
            self.assertFalse(list(pak.glob('core*')))

    def test_source_only_layout_and_safety_contract(self):
        subprocess.run(['/bin/sh','-n',str(PAK/'launch.sh')],check=True)
        tokens=set(shlex.shlex((PAK/'launch.sh').read_text(),posix=True,punctuation_chars=True))
        forbidden={'sudo','su','eval','.','source','kill','killall','reboot','mount',
                   'umount','sysctl','swapon','swapoff','chmod','curl','wget','ssh',
                   'apt','opkg','rm','mv','cp','dd','timeout'}
        self.assertFalse(tokens & forbidden)
        code=(BASE/'triangle.c').read_text()
        for call in ('system','popen','fopen','open','socket','fork','execve','kill','ioctl'):
            self.assertIsNone(re.search(r'\b'+call+r'\s*\(',code))
        self.assertIn('frames<MAX_FRAMES && !stopping',code)
        self.assertIn('elapsed>=RUN_MS',code)
        self.assertTrue((PAK/'SOURCE_ONLY').is_file())
        self.assertFalse((PAK/'bin').exists())
        self.assertEqual({p.name for p in PAK.iterdir()},{'SOURCE_ONLY','launch.sh'})
        manifest=json.loads((BASE/'provenance.json').read_text())
        self.assertEqual(manifest['status'],'SOURCE_ONLY_BLOCKED')
        self.assertTrue(all(v=='UNKNOWN' for v in manifest['unresolved'].values()))
        for entry in manifest['sources']:
            self.assertRegex(entry['commit'],r'^[a-f0-9]{40}$')
        # No generated ELF/archive can silently join source files or CI artifacts.
        for path in BASE.rglob('*'):
            if path.is_file():
                self.assertNotEqual(path.read_bytes()[:4],b'\x7fELF',str(path))
                self.assertNotIn(path.suffix,('.zip','.so','.a'))


if __name__=='__main__':
    unittest.main()
