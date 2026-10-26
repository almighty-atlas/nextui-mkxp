"""Host-only checks for the fixed-path H700 runtime metadata inventory.

Fixtures rewrite the probe's fixed system roots into a fresh temporary directory.
They never invoke the script against a physical device or installed firmware.
"""
import hashlib
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
        source = SCRIPT.read_text()
        # Descending path specificity prevents partial substitution, and
        # targets only source-owned fixed library roots, not /dev/null.
        substitutions = (
            ('/mnt/SDCARD/.system/h700/lib/', str(self.root / 'nextui') + '/'),
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
