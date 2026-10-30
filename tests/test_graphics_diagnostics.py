# SPDX-License-Identifier: MIT
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GraphicsDiagnostics(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('RMXP_RUBY') or shutil.which('ruby'), 'Ruby unavailable')
    def test_stress_completion_and_memory_stop(self):
        ruby = os.environ.get('RMXP_RUBY') or shutil.which('ruby')
        for high in ('0', '1'):
            result = subprocess.run([ruby, str(ROOT / 'tests/graphics_stress_mock.rb')],
                                    env={**os.environ, 'STRESS_HIGH_RSS': high},
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('STRESS_CONTROL_FLOW_PASS', result.stdout)
            self.assertIn('GRAPHICS_STRESS_' + ('STOP' if high == '1' else 'COMPLETE'), result.stdout)

    @unittest.skipUnless(shutil.which('c++'), 'host C++ compiler unavailable')
    def test_texture_ledger_and_opt_in(self):
        code = r'''
#include "graphics_diagnostics.hpp"
#include <cassert>
int main() {
    using namespace NextUIGraphics;
    Ledger s;
    assert(s.pixels(-1, 2) == 0);
    assert(s.pixels(65536, 65536) == 17179869184ULL);
    s.gen(5); s.bound = 5; s.image(64, 64, false);
    assert(s.liveBytes == 16384 && s.images == 1);
    s.image(32, 32, true);
    assert(s.liveBytes == 4096 && s.peakBytes == 16384);
    assert(s.imageBytes == 20480 && s.uploadBytes == 4096);
    s.subimage(8, 8); assert(s.uploadBytes == 4352);
    s.erase(5); assert(s.liveBytes == 0 && s.textures.empty());
    s.erase(5); assert(s.liveBytes == 0);
    s.bound = 9; s.image(1, 1, false); assert(s.overflow);
    gen(7); bind(7); image(8, 8, false); subimage(4, 4); blit(); pool(256, 1);
    report(true);
    assert(ledger().generated == (enabled() ? 1U : 0U));
}
'''
        with tempfile.TemporaryDirectory() as temp:
            source, binary = Path(temp) / 'test.cpp', Path(temp) / 'test'
            source.write_text(code)
            result = subprocess.run(['c++', '-std=c++11', '-Wall', '-Wextra', '-Werror',
                                     '-I', str(ROOT / 'native'), str(source), '-o', str(binary)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for flag in ('0', '1'):
                result = subprocess.run([str(binary)], env={**os.environ, 'NEXTUI_GL_DIAGNOSTICS': flag},
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual('NEXTUI_GL' in result.stderr, flag == '1')
                if flag == '1':
                    self.assertIn('bytes=256', result.stderr)
                    self.assertIn('incomplete=0', result.stderr)

    def test_unknown_source_is_rejected_before_writes(self):
        spec = importlib.util.spec_from_file_location('instrument_graphics',
                                                     ROOT / 'scripts/instrument_h700_graphics.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            path = source / 'src/display/gl/gl-util.h'
            path.parent.mkdir(parents=True)
            path.write_text('not the pinned source')
            with self.assertRaises(ValueError):
                module.instrument(source)
            self.assertEqual(path.read_text(), 'not the pinned source')
            self.assertFalse((path.parent / 'nextui-graphics-diagnostics.hpp').exists())
