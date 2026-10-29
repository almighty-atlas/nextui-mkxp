import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from issue_26_proc_variant import generate, ORIGINAL_SHA256

FIXTURES = Path(__file__).resolve().parent/'fixtures'


class ProcVariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.original = (FIXTURES/'triangle-original.c').read_text()
        cls.variant = generate(cls.original)
        source = Path(cls.temp.name)/'proc-variant.c'; source.write_text(cls.variant)
        cls.binary = Path(cls.temp.name)/'host-mock-only'
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        '-I'+str(FIXTURES/'include'), str(source),
                        str(FIXTURES/'mock_proc.c'), '-o', str(cls.binary)], check=True)

    def run_mock(self, case='', **extra):
        result = subprocess.run([self.binary], env={'SDL_VIDEODRIVER':'mali',
                                'MOCK_CASE':case, **extra}, capture_output=True,
                                text=True, timeout=3)
        self.assertEqual(result.stderr, '')
        self.assertLess(len(result.stdout), 4096)
        self.assertTrue(all(len(line)<181 for line in result.stdout.splitlines()))
        self.assertNotIn('PASS', result.stdout)
        self.assertIn('cleanup_complete', result.stdout)
        return result

    def test_original_identity_and_explicit_delta(self):
        self.assertEqual(hashlib.sha256(self.original.encode()).hexdigest(), ORIGINAL_SHA256)
        self.assertNotIn('eglQueryString', self.variant)
        self.assertNotIn('eglGetCurrentDisplay', self.variant)
        self.assertNotIn('#include <EGL/', self.variant)
        self.assertEqual(self.variant.count('SDL_GL_GetProcAddress('), 26)
        with self.assertRaises(ValueError):
            generate(self.original+'\n')

    def test_actual_simulated_shader_draw_swap_and_animation(self):
        result = self.run_mock()
        self.assertEqual(result.returncode, 0)
        self.assertIn('frames=625 elapsed_ms=5000', result.stdout)
        self.assertIn('cleanup=ok swaps=625 draws=625 shaders_deleted=2', result.stdout)

    def test_every_null_lookup_fails_before_gl_calls(self):
        for name in sorted(set(re.findall(r'SDL_GL_GetProcAddress\("(gl\w+)"', self.variant))):
            with self.subTest(name=name):
                result = self.run_mock(MOCK_MISSING=name)
                self.assertEqual(result.returncode, 32)
                self.assertIn('stage=gl_proc_missing', result.stdout)
                self.assertIn('cleanup=ok swaps=0 draws=0 shaders_deleted=0', result.stdout)

    def test_profile_version_and_gl_failure_cleanup(self):
        for case, code in {'wrong_profile':33, 'bad_gl':19, 'shader_fail':20,
                           'link_fail':21, 'uniform_fail':22, 'buffer_fail':23,
                           'bad_size':24, 'draw_fail':25, 'swap_fail':27,
                           'context_fail':16, 'current_fail':17}.items():
            with self.subTest(case=case):
                result = self.run_mock(case)
                self.assertEqual(result.returncode, code)
                self.assertIn('cleanup=ok', result.stdout)

    def test_signals_clock_wrap_deadline_and_metadata(self):
        for case in ('term', 'int', 'quit'):
            self.assertEqual(self.run_mock(case).returncode, 30)
        self.assertEqual(self.run_mock('clock_stuck').returncode, 26)
        for case in ('wrap', 'event_flood', 'long_metadata'):
            self.assertEqual(self.run_mock(case).returncode, 0)
        self.assertNotIn('\x01', self.run_mock('long_metadata').stdout)
