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
    def test_rocket_guard_memory_time_and_alias_chaining(self):
        ruby = os.environ.get('RMXP_RUBY') or shutil.which('ruby')
        code = r'''
module Graphics
  @updates = 0
  class << self
    attr_reader :updates
    def update = @updates += 1
  end
end
class << File
  def read(*) = ENV['MODE'] == 'memory' ? '200000 120000' : '20000 10000'
end
class << Process
  def clock_gettime(*)
    @calls = (@calls || 0) + 1
    ENV['MODE'] == 'time' && @calls > 1 ? 91 : 0
  end
end
load ARGV[0]
class << Graphics
  alias game_update update
  def update = game_update
end
begin
  10.times { Graphics.update }
rescue SystemExit => e
  raise unless e.status == 0 && ENV['MODE'] != 'normal'
end
raise unless Graphics.updates == (ENV['MODE'] == 'normal' ? 10 : 9)
puts 'GUARD_PASS'
'''
        for mode in ('normal', 'memory', 'time'):
            result = subprocess.run([ruby, '-e', code, str(ROOT / 'tests/hardware/rocket-native/memory_guard.rb')],
                                    env={**os.environ, 'MODE': mode}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('GUARD_PASS', result.stdout)
            self.assertEqual('ROCKET_DIAGNOSTIC_STOP' in result.stderr, mode != 'normal')

    def test_rocket_diagnostic_preserves_original_config(self):
        import json
        spec = importlib.util.spec_from_file_location('prepare_rocket',
                                                     ROOT / 'scripts/prepare_rocket_native_diagnostic.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / 'original.json', Path(temp) / 'diagnostic'
            config = {'rgssVersion': 1, 'gameFolder': module.STATE + '/game',
                      'preloadScript': [module.STATE + '/compat/essentials_win32_compat.rb'],
                      'fontHeightReporting': 1}
            source.write_text(json.dumps(config))
            before = source.read_bytes()
            module.prepare(source, output)
            self.assertEqual(source.read_bytes(), before)
            prepared = json.loads((output / 'mkxp.json').read_text())
            self.assertEqual(prepared['gameFolder'], config['gameFolder'])
            self.assertEqual(len(prepared['preloadScript']), 2)
            self.assertEqual(prepared['fontHeightReporting'], 1)
            with self.assertRaises(FileExistsError):
                module.prepare(source, output)
            config['gameFolder'] = '/wrong/game'
            source.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                module.prepare(source, Path(temp) / 'bad')
            self.assertFalse((Path(temp) / 'bad').exists())

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
    gen(8); bind(8); image(1024, 1024, false); erase(8);
    report(true);
    assert(ledger().generated == (enabled() ? 2U : 0U));
}
'''
        with tempfile.TemporaryDirectory() as temp:
            source, binary = Path(temp) / 'test.cpp', Path(temp) / 'test'
            source.write_text(code)
            result = subprocess.run(['c++', '-std=c++11', '-Wall', '-Wextra', '-Werror',
                                     '-I', str(ROOT / 'native'), str(source), '-o', str(binary), '-ldl'],
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
                    self.assertIn('NEXTUI_GL_IMAGE id=8 w=1024 h=1024', result.stderr)

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
