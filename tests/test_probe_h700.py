"""Host fixtures only: no H700 claims, device opens or privileged setup."""
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/probe-h700.sh'


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.fs = self.base / 'fixture'
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        # Rewrite fixed paths in a temporary copy, never support arbitrary root
        # overrides in the production probe. All fixture I/O stays in tempdir.
        source = SCRIPT.read_text()
        source = re.sub(r'/(?:mnt|proc|etc|dev(?!/null)|lib64|lib|usr/lib64|usr/lib|bin/sh)(?=[/\s;\]"\']|$)',
                        lambda m: str(self.fs) + m[0], source)
        self.copy = self.base / 'probe.sh'
        self.copy.write_text(source)
        for tool in ('awk', 'od'):
            shutil.copyfile(shutil.which(tool), self.bin / tool)
            (self.bin / tool).chmod(0o755)
        for tool, body in {
            'uname': 'case "$1" in -m) echo aarch64;; -r) echo fixture-kernel;; *) exit 1;; esac',
            'getconf': 'case "$1" in LONG_BIT) echo 64;; GNU_LIBC_VERSION) echo "glibc fixture";; *) exit 1;; esac',
            'readelf': 'echo "[Requesting program interpreter: /lib/ld-linux-aarch64.so.1]"',
        }.items():
            path = self.bin / tool
            path.write_text('#!/bin/sh\n' + body + '\n')
            path.chmod(0o755)
        self.write('/etc/os-release', 'PRETTY_NAME="Fixture OS"\nTOKEN=PRIVATE_SENTINEL\n')
        self.write('/mnt/SDCARD/.system/version.txt', 'NextUI-fixture\n0123456789abcdef\nPRIVATE_SENTINEL\n')
        self.write('/proc/meminfo', 'MemTotal: 1024000 kB\nMemAvailable: 123456 kB\nSwapTotal: 0 kB\n')
        self.write('/proc/swaps', 'Filename Type Size Used Priority\n/private/PRIVATE_SENTINEL file 512 10 -2\n')
        self.write('/proc/bus/input/devices', 'I: Bus=0019 Vendor=0001 Product=0001 Version=0100\nN: Name="PRIVATE_SENTINEL"\nP: Phys=PRIVATE_SENTINEL\nU: Uniq=PRIVATE_SENTINEL\nH: Handlers=kbd event0 js0 PRIVATE_SENTINEL\n')
        self.write('/lib/libSDL2-fixture.so.0', '')
        self.elf(2, 1, 183)

    def write(self, path, content):
        dest = self.fs / path.lstrip('/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)

    def elf(self, bits, endian, machine):
        header = bytearray(20)
        header[:6] = bytes([127, 69, 76, 70, bits, endian])
        header[18:20] = machine.to_bytes(2, 'little' if endian == 1 else 'big')
        dest = self.fs / 'bin/sh'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(header)

    def run_probe(self, *args, empty_path=False):
        env = {'PATH': str(self.base / 'missing') if empty_path else str(self.bin),
               'PLATFORM': 'h700', 'DEVICE': 'rg35xxpro',
               'TOKEN': 'PRIVATE_SENTINEL', 'SAVES_PATH': '/private/PRIVATE_SENTINEL',
               'SYSTEM_PATH': '/private/PRIVATE_SENTINEL', 'LC_ALL': 'C'}
        return subprocess.run(['/bin/sh', str(self.copy), *args], env=env,
                              capture_output=True, text=True, timeout=10)

    def test_sanitized_fixture(self):
        before = {p: p.read_bytes() for p in self.fs.rglob('*') if p.is_file()}
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        for expected in ('NextUI-fixture', 'ELF64', 'AArch64', 'MemTotal: 1024000',
                         'handlers: kbd event0 js0', 'swap type=file size_kB=512',
                         'SAVES_PATH=set (value suppressed)', 'libSDL2-fixture.so.0'):
            self.assertIn(expected, result.stdout)
        self.assertNotIn('PRIVATE_SENTINEL', result.stdout)
        self.assertEqual(before, {p: p.read_bytes() for p in self.fs.rglob('*') if p.is_file()})

    def test_device_fifo_is_not_opened(self):
        node = self.fs / "dev/input/event0"
        node.parent.mkdir(parents=True)
        os.mkfifo(node)
        result = self.run_probe()
        self.assertEqual(result.returncode, 0)
        self.assertIn("/dev/input/event0: present", result.stdout)

    def test_no_optional_commands_or_files(self):
        shutil.rmtree(self.fs)
        result = self.run_probe(empty_path=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('NOT_TESTED', result.stdout)
        self.assertIn('UNKNOWN', result.stdout)
        self.assertIn('readelf: UNKNOWN (missing)', result.stdout)

    def test_elf32_big_endian_and_non_elf(self):
        self.elf(1, 2, 40)
        self.assertIn('class=ELF32 endian=big e_machine=40 (ARM)', self.run_probe().stdout)
        self.write('/bin/sh', 'not an executable')
        self.assertIn('UNKNOWN (not a readable ELF header)', self.run_probe().stdout)

    def test_failed_optional_tools(self):
        for tool in ('awk', 'od', 'uname', 'getconf', 'readelf'):
            (self.bin / tool).write_text('#!/bin/sh\nexit 1\n')
        result = self.run_probe()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, '')
        self.assertIn('UNKNOWN', result.stdout)

    def test_rejects_caller_file(self):
        result = self.run_probe('/private/PRIVATE_SENTINEL')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('PRIVATE_SENTINEL', result.stdout + result.stderr)

    def test_static_safety_contract_and_syntax(self):
        source = SCRIPT.read_text()
        tokens = list(shlex.shlex(source, posix=True, punctuation_chars=True))
        forbidden = {'sudo', 'su', 'eval', '.', 'source', 'env', 'printenv', 'curl',
                     'wget', 'ssh', 'mount', 'umount', 'dd', 'rm', 'cp', 'mv',
                     'touch', 'mkdir', 'tee', 'chmod', 'chown', 'sysctl', 'swapon',
                     'swapoff', 'apt', 'apt-get', 'opkg', 'kill', 'reboot'}
        self.assertFalse(forbidden.intersection(tokens))
        # All shell output redirection targets are /dev/null or stderr.
        for i, token in enumerate(tokens):
            if token in ('>', '>>', '>&'):
                self.assertIn((token, tokens[i+1]), [('>', '/dev/null'), ('>&', '2'), ('>&', '1')])
        self.assertNotIn('/proc/self/environ', source)
        self.assertNotIn('/proc/net/', source)
        self.assertNotIn('uname -a\n', source)
        subprocess.run(['/bin/sh', '-n', str(SCRIPT)], check=True)
        busybox = shutil.which('busybox')
        if busybox:
            subprocess.run([busybox, 'sh', '-n', str(SCRIPT)], check=True)
        self.assertTrue(os.access(SCRIPT, os.X_OK))


if __name__ == '__main__':
    unittest.main()
