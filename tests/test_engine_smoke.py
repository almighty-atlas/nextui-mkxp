# SPDX-License-Identifier: MIT
"""Offline synthetic packaging/config guards; no engine or hardware execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('engine_smoke', ROOT / 'scripts/prepare_h700_engine_smoke.py')
M = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    SPEC.loader.exec_module(M)
finally:
    sys.path.remove(str(ROOT / 'scripts'))


class EngineSmoke(unittest.TestCase):
    def test_v2_result_and_staged_v3_fixture_hashes(self):
        evidence = json.loads((ROOT / 'build/h700-engine/engine-smoke-evidence.json').read_text())
        self.assertEqual(evidence['status'], 'PASS; V3_AUDIO_INPUT_RETURN_CONFIRMED')
        self.assertTrue(evidence['video'].startswith('PASS'))
        self.assertTrue(evidence['ruby_embedding'].startswith('PASS'))
        self.assertTrue(evidence['audio'].startswith('PASS in v3'))
        self.assertFalse(evidence['engine_main_executed_by_agent'])
        log = (ROOT / evidence['log_excerpt']).read_text()
        self.assertEqual(log.count('SMOKE_RUNNER_PASS'), 4)
        self.assertNotRegex(log, r'0x[0-9a-fA-F]+|/tmp/')
        followup = evidence['followup']
        self.assertEqual(followup['status'], 'PASS; OWNER_OBSERVED')
        for name, expected in followup['fixture_sha256'].items():
            self.assertEqual(M.digest(ROOT / 'tests/hardware/engine-smoke' / name), expected)
        self.assertIn(followup['device_stage'], (ROOT / 'tests/hardware/engine-smoke/launch.sh').read_text())
        for feature in ('audio', 'input_visual_feedback', 'nextui_navigation_after_return'):
            self.assertTrue(followup[feature].startswith('PASS'))
        self.assertTrue(followup['hold_cancel'].startswith('NOT_TESTED'))
        v3_log = (ROOT / followup['log_excerpt']).read_text()
        self.assertEqual(v3_log.count('SMOKE_RUNNER_PASS'), len(followup['raw_log_sha256']))
        self.assertNotRegex(v3_log, r'0x[0-9a-fA-F]+|/tmp/')

    def fixture(self, temp):
        root, prefix = Path(temp) / 'repo', Path(temp) / 'prefix'
        shutil.copytree(ROOT / 'tests/hardware/engine-smoke', root / 'tests/hardware/engine-smoke')
        (root / 'build/h700-engine').mkdir(parents=True)
        (prefix / 'stdlib').mkdir(parents=True)
        (prefix / 'mkxp-z.aarch64').write_bytes(b'synthetic non-executable fixture')
        (prefix / 'LICENSE.txt').write_text('Synthetic notice')
        (prefix / 'stdlib/a.rb').write_text('# synthetic source')
        (prefix / 'stdlib/foreign.so').write_bytes(b'not an ELF, must not ship')
        evidence = {'status': 'STATIC_ABI_CANDIDATES_PASS',
                    'loader_test': {'status': 'ENGINE_LOADER_PASS'},
                    'engine_sha256': M.digest(prefix / 'mkxp-z.aarch64')}
        (root / 'build/h700-engine/engine-abi-evidence.json').write_text(json.dumps(evidence))
        return root, prefix

    def test_private_archive_allowlist_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root, prefix = self.fixture(temp)
            output = Path(temp) / 'payload'
            with patch.object(M, 'ROOT', root), patch.object(M.shutil, 'disk_usage') as disk:
                disk.return_value.free = 6 * 1024**3
                result = M.prepare(prefix, output)
            self.assertEqual(result['status'], 'PRIVATE_SMOKE_PREPARED')
            self.assertFalse((output / 'stdlib/foreign.so').exists())
            self.assertEqual(output.with_suffix('.tar.gz').stat().st_mode & 0o777, 0o600)
            receipt = json.loads(output.with_suffix('.receipt.json').read_text())
            for name, expected in receipt['files'].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), expected)
            with tarfile.open(output.with_suffix('.tar.gz')) as tar:
                self.assertNotIn('work', tar.getnames())
                self.assertFalse(any(m.issym() or m.islnk() for m in tar))
                self.assertTrue(all(m.uid == m.gid == m.mtime == 0 for m in tar))

    def test_engine_hash_and_fresh_output_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            root, prefix = self.fixture(temp)
            output = Path(temp) / 'payload'
            with patch.object(M, 'ROOT', root), patch.object(M.shutil, 'disk_usage') as disk:
                disk.return_value.free = 6 * 1024**3
                (prefix / 'mkxp-z.aarch64').write_text('changed')
                with self.assertRaisesRegex(ValueError, 'ENGINE_HASH'):
                    M.prepare(prefix, output)
                self.assertFalse(output.exists())
                output.mkdir()
                with self.assertRaisesRegex(ValueError, 'FRESH_OUTPUT_REQUIRED'):
                    M.prepare(prefix, output)

    def test_shell_syntax_and_host_refusal(self):
        fixture = ROOT / 'tests/hardware/engine-smoke'
        for name in ('run.sh', 'launch.sh'):
            subprocess.run(['sh', '-n', str(fixture / name)], check=True, timeout=5)
        result = subprocess.run(['sh', str(fixture / 'run.sh')], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), 'INVALID_STAGING_DIRECTORY')

    def test_config_no_games_rtp_jit_or_unbounded_run(self):
        fixture = ROOT / 'tests/hardware/engine-smoke'
        config = json.loads((fixture / 'mkxp.json').read_text())
        self.assertEqual(config['rgssVersion'], 1)
        self.assertEqual(config['RTP'], [])
        self.assertEqual(config['customScript'], 'smoke.rb')
        self.assertFalse(config['pathCache'])
        self.assertFalse(config['JITEnable'])
        self.assertFalse(config['YJITEnable'])
        shell = (fixture / 'run.sh').read_text()
        self.assertIn('/usr/bin/timeout -k 3 45', shell)
        self.assertIn('LD_BIND_NOW=1', shell)
        self.assertIn('pidof nextui.elf', shell)
        self.assertIn('grep -qx SMOKE_SCRIPT_PASS', shell)
        smoke = (fixture / 'smoke.rb').read_text()
        self.assertIn('1800.times', smoke)
        self.assertIn("Audio.se_play('tone.wav', 85, 100)", smoke)
        self.assertIn('cancel_frames >= 60', smoke)


if __name__ == '__main__':
    unittest.main()
