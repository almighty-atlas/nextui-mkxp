"""Host-only checks for the fixed-path H700 runtime metadata inventory.

Fixtures rewrite the probe's fixed system roots into a fresh temporary directory.
They never invoke the script against a physical device or installed firmware.
"""
import hashlib
import os
import shutil
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/probe-h700-runtime.sh'


class MetadataProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.joinpath('dev').mkdir()
        self.root.joinpath('lib/aarch64-linux-gnu').mkdir(parents=True)
        self.root.joinpath('usr-lib').mkdir()
        self.root.joinpath('vendor').mkdir()
        self.root.joinpath('nextui').mkdir()
        self.root.joinpath('nextui-real').mkdir()
        source = SCRIPT.read_text()
        # Descending path specificity prevents partial substitution, and
        # targets only source-owned fixed library roots, not /dev/null.
        substitutions = (
            ('/mnt/SDCARD/.system/h700/lib/', str(self.root / 'nextui') + '/'),
            ('/mnt/sdcard/.system/h700/lib/', str(self.root / 'nextui-real') + '/'),
            ('/mnt/vendor/lib64/', str(self.root / 'vendor') + '/'),
            ('/usr/lib/', str(self.root / 'usr-lib') + '/'),
            ('/lib/', str(self.root / 'lib') + '/'),
        )
        for old, new in substitutions:
            source = source.replace(old, new)
        for name in ('ion', 'fb0', 'mali', 'mali0'):
            source = source.replace('/dev/' + name, str(self.root/'dev'/name))
        for name in ('card0', 'renderD128'):
            source = source.replace('/dev/dri/' + name, str(self.root/'dev'/'dri'/name))
        self.program = self.root / 'probe-fixture.sh'
        self.program.write_text(source)

    def run_probe(self, *arguments):
        return subprocess.run(['/bin/sh', str(self.program), *arguments],
                              capture_output=True, text=True, timeout=10, check=False)

    def write_elf(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        head = bytearray(64)
        head[:7] = b'\x7fELF\x02\x01\x01'
        head[18:20] = (183).to_bytes(2, 'little')
        path.write_bytes(head)
        return hashlib.sha256(head).hexdigest()

    def test_syntax_and_no_args(self):
        self.assertEqual(subprocess.run(['/bin/sh', '-n', str(self.program)], check=False).returncode, 0)
        result = self.run_probe('/tmp/other')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('== FIXED LIBRARY', result.stdout)

    def test_fallback_with_missing_libraries(self):
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('NOT_TESTED', result.stdout)
        self.assertIn('UNKNOWN (not a readable regular file)', result.stdout)
        self.assertNotIn('GLIBC_2.27 confirmed', result.stdout)
        self.assertFalse(list(self.root.rglob('*.log')))

    def test_elf_header_and_hash_are_only_metadata(self):
        path = self.root / 'lib/aarch64-linux-gnu/libc.so.6'
        digest = self.write_elf(path)
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('ELF64 little machine=183 AArch64', result.stdout)
        self.assertIn('sha256: ' + digest, result.stdout)
        self.assertIn('UNKNOWN (none reported or unsupported)', result.stdout)
        self.assertEqual(path.read_bytes()[:7], b'\x7fELF\x02\x01\x01')

    def test_symlink_outside_allowlist_is_not_read(self):
        secret = self.root / 'private-secret'
        secret.write_text('DONTREAD_CONFIDENTIAL_DUMMY_TOKEN\n')
        (self.root/'lib/libEGL.so.1').symlink_to(secret)
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('outside fixed system roots; not read', result.stdout)
        self.assertNotIn('DONTREAD_CONFIDENTIAL_DUMMY_TOKEN', result.stdout)
        self.assertNotIn(hashlib.sha256(secret.read_bytes()).hexdigest(), result.stdout)

    def test_symlink_to_allowlisted_library_is_hashed(self):
        target = self.root/'lib/libEGL.so.1.real'
        digest = self.write_elf(target)
        (self.root/'lib/libEGL.so.1').symlink_to(target.name)
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(digest, result.stdout)

    def test_baseos_harvested_aarch64_loader_candidate(self):
        """BaseOS harvest.list includes /usr/lib/aarch64-linux-gnu loader."""
        path = self.root / 'usr-lib/aarch64-linux-gnu/ld-linux-aarch64.so.1'
        expected = self.write_elf(path)
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('sha256: ' + expected, result.stdout)

    def test_nextui_uppercase_alias_canonical_lowercase_is_read(self):
        """Owner observed /mnt/SDCARD => canonical /mnt/sdcard NextUI lib root."""
        actual = self.root / 'nextui-real/libSDL2-2.0.so.0'
        digest = self.write_elf(actual)
        alias = self.root / 'nextui/libSDL2-2.0.so.0'
        alias.symlink_to(actual)
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('sha256: ' + digest, result.stdout)
        self.assertNotIn('outside fixed system roots; not read', result.stdout)

    def test_nextui_alias_other_root_stays_blocked(self):
        """Allowlisting /mnt/sdcard does not allow unrelated resolved roots."""
        secret = self.root / 'private-secret-sdl'
        secret.write_bytes(b'CONFIDENTIAL_DUMMY_TEST')
        alias = self.root / 'nextui/libSDL2-2.0.so.0'
        alias.symlink_to(secret)
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('outside fixed system roots; not read', result.stdout)
        self.assertNotIn(hashlib.sha256(secret.read_bytes()).hexdigest(), result.stdout)

    def test_filtered_readelf_output_and_redaction(self):
        """Synthetic readelf text: verify no RPATH or odd dependency contents leak."""
        path = self.root / 'lib/aarch64-linux-gnu/libc.so.6'
        self.write_elf(path)
        bindir = self.root / 'fake-bin'
        bindir.mkdir()
        fake = bindir / 'readelf'
        fake.write_text(
            '#!/bin/sh\n'
            'case "$2" in\n'
            ' -d)\n'
            "   printf '%s\\n' ' 0x1 (NEEDED) Shared library: [libSDL2-2.0.so.0]'"
            " ' 0x1 (NEEDED) Shared library: [../PRIVATE-SENTINEL]'"
            " ' 0x1d (RUNPATH) Library runpath: [/PRIVATE-PATH-SENTINEL]' ;;\n"
            ' -V)\n'
            "   printf '%s\\n' \"Version needs section '.gnu.version_r' contains 1 entry:\""
            " '  0x0010:   Name: GLIBC_2.27  Flags: none  Version: 2'"
            " \"Version definition section '.gnu.version_d' contains 1 entry:\""
            " '  0x001c: Rev: 1  Flags: none  Index: 2  Cnt: 1  Name: GLIBC_2.28' ;;\n"
            'esac\n')
        fake.chmod(0o755)
        result = subprocess.run(['/bin/sh', str(self.program)],
                                env=dict(os.environ, PATH=str(bindir) + os.pathsep +
                                         os.environ.get('PATH', '/usr/bin:/bin')),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('    libSDL2-2.0.so.0', result.stdout)
        self.assertIn('    REDACTED', result.stdout)
        self.assertIn('    GLIBC_2.27', result.stdout)
        self.assertIn('    GLIBC_2.28', result.stdout)
        self.assertIn('runtime_search_paths: PRESENT (values suppressed)', result.stdout)
        self.assertNotIn('PRIVATE-SENTINEL', result.stdout)
        self.assertNotIn('PRIVATE-PATH-SENTINEL', result.stdout)

    def test_busybox_ash_applets_if_available(self):
        """Host BusyBox semantics only; does not assert H700 BusyBox availability."""
        busybox = shutil.which('busybox')
        if not busybox:
            self.skipTest('BusyBox not installed on this host')
        bindir = self.root / 'busybox-bin'
        bindir.mkdir()
        for applet in ('awk', 'od', 'readlink', 'sha256sum', 'uname'):
            (bindir / applet).symlink_to(busybox)
        path = self.root / 'lib/aarch64-linux-gnu/libc.so.6'
        expected = self.write_elf(path)
        result = subprocess.run([busybox, 'ash', str(self.program)],
                                env={'PATH': str(bindir), 'LC_ALL': 'C'},
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('ELF64 little machine=183 AArch64', result.stdout)
        self.assertIn('sha256: ' + expected, result.stdout)
        self.assertIn('readelf_available: no', result.stdout)

    def test_static_no_mutating_or_execute_commands(self):
        source = SCRIPT.read_text()
        executable_lines = '\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('#'))
        self.assertNotRegex(executable_lines, r'\b(?:sudo|su|ldd|mount|modprobe|chmod|chown|kill|reboot|eval|source|dd|cp|mv|rm)\b')
        self.assertNotRegex(source, r'\b(?:curl|wget|ssh|scp|nc|netcat)\b')
        self.assertNotIn('readelf --dynamic-syms', source)
        self.assertNotIn('>/mnt/', source)
        self.assertNotRegex(source, r'>/dev/(?!null\b)')
        self.assertNotIn('set -x', source)


if __name__ == '__main__':
    unittest.main()
