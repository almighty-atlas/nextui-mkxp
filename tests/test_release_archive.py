# SPDX-License-Identifier: MIT
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/release_archive.py'
SPEC = importlib.util.spec_from_file_location('release_archive', SCRIPT)
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)
PAK = R.PAK


def elf(machine=183, interp='/lib/ld-linux-aarch64.so.1', versions=('GLIBC_2.17',),
        needed=('libc.so.6',), runpath=None, exec_stack=False):
    """Minimal synthetic ELF64 with PT_INTERP, dynamic section and verneed."""
    strings = bytearray(b'\0')

    def add(text):
        strings.extend(text.encode() + b'\0')
        return len(strings) - len(text) - 1
    needed_offsets = [add(n) for n in needed]
    version_offsets = [add(v) for v in versions]
    runpath_offset = add(runpath) if runpath else None
    interp_bytes = interp.encode() + b'\0'
    pos = 64 + 2 * 56
    interp_at, pos = pos, pos + len(interp_bytes)
    strings_at, pos = pos, pos + len(strings)
    dynamic = b''.join(struct.pack('<qQ', 1, o) for o in needed_offsets)
    if runpath_offset is not None:
        dynamic += struct.pack('<qQ', 29, runpath_offset)
    dynamic += struct.pack('<qQ', 0, 0)
    dynamic_at, pos = pos, pos + len(dynamic)
    verneed = struct.pack('<HHIII', 1, len(versions), needed_offsets[0] if needed else 0, 16, 0)
    for i, offset in enumerate(version_offsets):
        verneed += struct.pack('<IHHII', 0, 0, i + 2, offset, 16 if i + 1 < len(versions) else 0)
    verneed_at, pos = pos, pos + len(verneed)
    sections = [bytes(64),
                struct.pack('<IIQQQQIIQQ', 0, 3, 0, 0, strings_at, len(strings), 0, 0, 1, 0),
                struct.pack('<IIQQQQIIQQ', 0, 6, 0, 0, dynamic_at, len(dynamic), 1, 0, 8, 16),
                struct.pack('<IIQQQQIIQQ', 0, 0x6ffffffe, 0, 0, verneed_at, len(verneed), 1, 1, 4, 0)]
    header = (b'\x7fELF' + bytes([2, 1, 1, 0]) + bytes(8) +
              struct.pack('<HHIQQQIHHHHHH', 3, machine, 1, 0, 64, pos, 0, 64, 56, 2, 64, 4, 0))
    phdrs = (struct.pack('<IIQQQQQQ', 3, 4, interp_at, 0, 0, len(interp_bytes), len(interp_bytes), 1) +
             struct.pack('<IIQQQQQQ', 0x6474e551, 7 if exec_stack else 6, 0, 0, 0, 0, 0, 16))
    return header + phdrs + interp_bytes + bytes(strings) + dynamic + verneed + b''.join(sections)


def go_gates(engine_hash):
    gates = {name: {'state': 'GO', 'reviewer': 'Fixture Reviewer', 'date': '2026-10-29',
                    'evidence': 'synthetic'} for name in R.GATES}
    gates['h700_acceptance'].update({'level': 'verified-on-H700', 'device': 'RG35XX Pro',
                                     'firmware': 'fixture', 'engine_sha256': engine_hash,
                                     'results': {c: 'PASS' for c in R.H700_CHECKS}})
    return gates


class ReleaseArchiveTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.stage = self.root / 'stage'

    def make_stage(self, engine=None, gates=None, extra=None, roles=None, sums_fix=True):
        pak = self.stage / PAK
        files = {'launch.sh': b'#!/bin/sh\nexec "$(dirname "$0")/engine"\n',
                 'engine': engine if engine is not None else elf(),
                 'stdlib/fixture.rb': b'# synthetic\n',
                 'release/THIRD_PARTY_NOTICES.md': b'# Notices (fixture)\n',
                 'release/BUILDING.md': b'# Building (fixture)\n',
                 'release/LICENSES/FIXTURE.txt': b'synthetic license placeholder\n'}
        files.update(extra or {})
        for name, data in files.items():
            (pak / name).parent.mkdir(parents=True, exist_ok=True)
            (pak / name).write_bytes(data)
        sums = ''.join(f'{hashlib.sha256(d).hexdigest()}  {n}\n' for n, d in sorted(files.items()))
        (pak / 'SHA256SUMS').write_text(sums if sums_fix else sums[:-70])
        role = {'launch.sh': 'script', 'engine': 'binary', 'SHA256SUMS': 'data',
                'release/THIRD_PARTY_NOTICES.md': 'notice', 'release/BUILDING.md': 'doc',
                'release/LICENSES/FIXTURE.txt': 'license'}
        role.update(roles or {})
        entries = []
        for name in sorted(list(files) + ['SHA256SUMS']):
            entry = {'path': f'{PAK}/{name}', 'sha256': hashlib.sha256((pak / name).read_bytes()).hexdigest(),
                     'role': role.get(name, 'data'), 'license': 'FIXTURE'}
            if entry['role'] == 'binary':
                entry.update(license_file=f'{PAK}/release/LICENSES/FIXTURE.txt', source='fixture@0000000')
            entries.append(entry)
        engine_hash = hashlib.sha256((pak / 'engine').read_bytes()).hexdigest()
        manifest = {'schema': 1, 'version': '0.0.0-fixture',
                    'target': {'arch': 'aarch64', 'interpreter': '/lib/ld-linux-aarch64.so.1',
                               'glibc_max': '2.28', 'allowed_needed': ['libc.so.6', 'libm.so.6']},
                    'files': entries,
                    'gates': gates(engine_hash) if callable(gates) else gates or {}}
        (pak / 'release/manifest.json').write_text(json.dumps(manifest, indent=2))
        return manifest

    def raw_zip(self, members):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            for name, data, mode in members:
                info = zipfile.ZipInfo(name, R.EPOCH)
                info.create_system = 3
                info.external_attr = mode << 16
                archive.writestr(info, data)
        return buffer

    def stage_members(self):
        return [(p.relative_to(self.stage).as_posix(), p.read_bytes(), stat.S_IFREG | 0o644)
                for p in sorted(self.stage.rglob('*')) if p.is_file()]

    def rules(self, buffer):
        _, findings, _ = R.verify(buffer)
        return {rule for rule, _ in findings}

    def cli(self, *args):
        return subprocess.run(['python3', '-I', str(SCRIPT), *args], capture_output=True, text=True, timeout=60)

    def test_candidate_builds_and_verifies_but_gate_stays_blocked(self):
        self.make_stage()
        out = self.root / 'RMXP-fixture.zip'
        result = self.cli('build', '--stage', str(self.stage), '--out', str(out))
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn('STRUCTURE=PASS RELEASE_GATE=BLOCKED', result.stdout)
        for gate in R.GATES:
            self.assertIn(f'GATE_BLOCKED {gate}', result.stdout)
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        self.assertEqual(Path(str(out) + '.sha256').read_text(), f'{digest}  {out.name}\n')
        check = self.cli('--json', 'verify', str(out))
        self.assertEqual(check.returncode, 3)
        self.assertEqual(json.loads(check.stdout)['structure'], 'PASS')

    def test_build_is_deterministic_across_mtime_and_permissions(self):
        self.make_stage()
        first, second = self.root / 'a.zip', self.root / 'b.zip'
        R.build(self.stage, first)
        for path in self.stage.rglob('*'):
            if path.is_file():
                os.utime(path, (1_900_000_000, 1_900_000_000))
                path.chmod(0o600)
        R.build(self.stage, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            modes = {i.filename: (i.external_attr >> 16) & 0o777 for i in archive.infolist()}
        self.assertEqual(modes[f'{PAK}/engine'], 0o755)
        self.assertEqual(modes[f'{PAK}/stdlib/fixture.rb'], 0o644)

    def test_gate_requires_h700_evidence_bound_to_exact_engine(self):
        self.make_stage(gates=go_gates)
        count, findings, blocked, _ = R.build(self.stage, self.root / 'go.zip')
        self.assertEqual((findings, blocked), ([], []))
        for change in ('hash', 'level', 'check', 'reviewer', 'missing'):
            def gates(engine_hash, change=change):
                g = go_gates(engine_hash)
                if change == 'hash':
                    g['h700_acceptance']['engine_sha256'] = '0' * 64
                elif change == 'level':
                    g['h700_acceptance']['level'] = 'verified-on-host'
                elif change == 'check':
                    g['h700_acceptance']['results']['R7'] = 'NOT_TESTED'
                elif change == 'reviewer':
                    g['license_review']['reviewer'] = ' '
                else:
                    del g['relink']
                return g
            self.make_stage(gates=gates)
            _, findings, blocked = R.verify(self.raw_zip(self.stage_members()))
            self.assertEqual(findings, [])
            self.assertEqual(len(blocked), 1, change)

    def test_forbidden_paths_traversal_symlinks_and_collisions(self):
        self.make_stage()
        members = self.stage_members()
        bad = members + [('.userdata/h700/nextui-mkxp/x/save.rxdata', b'x', stat.S_IFREG | 0o644),
                         ('Roms/GBA/x.gba', b'x', stat.S_IFREG | 0o644),
                         (f'{PAK}/../../../escape', b'x', stat.S_IFREG | 0o644),
                         (f'{PAK}/link', b'/etc/passwd', stat.S_IFLNK | 0o777),
                         (f'{PAK}/STDLIB/fixture.rb', b'x', stat.S_IFREG | 0o644),
                         (f'{PAK}/Game.ini', b'x', stat.S_IFREG | 0o644)]
        found = self.rules(self.raw_zip(bad))
        self.assertTrue({'OUTSIDE_PAK_ROOT', 'FORBIDDEN_CONTENT', 'SPECIAL_FILE',
                         'DUPLICATE_OR_CASE_COLLISION', 'UNLISTED_FILE'} <= found)

    def test_checksum_sums_and_required_files(self):
        self.make_stage(sums_fix=False)
        (self.stage / PAK / 'stdlib/fixture.rb').write_bytes(b'# tampered\n')
        (self.stage / PAK / 'release/BUILDING.md').unlink()
        (self.stage / PAK / 'release/LICENSES/FIXTURE.txt').unlink()
        found = self.rules(self.raw_zip(self.stage_members()))
        self.assertTrue({'CHECKSUM_MISMATCH', 'PAK_SHA256SUMS_MISMATCH', 'REQUIRED_FILE_MISSING',
                         'LISTED_FILE_MISSING', 'LICENSES_MISSING',
                         'BINARY_SOURCE_OR_LICENSE_TEXT_MISSING'} <= found)

    def test_target_abi_rules(self):
        cases = [(elf(machine=62), 'ELF_NOT_AARCH64'),
                 (elf(interp='/lib/ld-linux-armhf.so.3'), 'ELF_INTERPRETER'),
                 (elf(versions=('GLIBC_2.17', 'GLIBC_2.34')), 'ELF_GLIBC_TOO_NEW'),
                 (elf(versions=('GLIBC_PRIVATE',)), 'ELF_GLIBC_PRIVATE'),
                 (elf(runpath='/job/sdl-prefix/lib:$ORIGIN'), 'ELF_ABSOLUTE_RPATH'),
                 (elf(exec_stack=True), 'ELF_EXECUTABLE_STACK'),
                 (elf(needed=('libc.so.6', 'libGL.so.1')), 'ELF_UNDECLARED_NEEDED'),
                 (b'#!/bin/sh\n', 'BINARY_NOT_ELF'),
                 (elf()[:80], 'ELF_MALFORMED')]
        for engine, rule in cases:
            self.make_stage(engine=engine)
            self.assertIn(rule, self.rules(self.raw_zip(self.stage_members())), rule)
        self.make_stage(engine=elf(runpath='$ORIGIN/lib', versions=('GLIBC_2.17', 'GLIBC_2.28')))
        self.assertEqual(self.rules(self.raw_zip(self.stage_members())), set())

    def test_undeclared_binary_and_shell_syntax(self):
        self.make_stage(extra={'release/notes.md': elf(), 'helper.sh': b'#!/bin/sh\nif then\n'},
                        roles={'release/notes.md': 'doc', 'helper.sh': 'script'})
        found = self.rules(self.raw_zip(self.stage_members()))
        self.assertTrue({'UNDECLARED_BINARY', 'SHELL_SYNTAX'} <= found)

    def test_failed_build_writes_nothing_and_never_overwrites(self):
        self.make_stage(engine=elf(machine=62))
        out = self.root / 'bad.zip'
        result = self.cli('build', '--stage', str(self.stage), '--out', str(out))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())
        self.make_stage()
        out.write_bytes(b'existing')
        result = self.cli('build', '--stage', str(self.stage), '--out', str(out))
        self.assertEqual(result.returncode, 2)
        self.assertIn('OUTPUT_EXISTS', result.stderr)
        self.assertEqual(out.read_bytes(), b'existing')

    def test_invalid_inputs(self):
        junk = self.root / 'junk.zip'
        junk.write_bytes(b'not a zip')
        result = self.cli('verify', str(junk))
        self.assertEqual(result.returncode, 1)
        self.assertIn('NOT_A_ZIP', result.stdout)
        self.make_stage()
        os.symlink('/etc/hostname', self.stage / PAK / 'link')
        result = self.cli('build', '--stage', str(self.stage), '--out', str(self.root / 'x.zip'))
        self.assertEqual(result.returncode, 2)
        self.assertIn('STAGE_SPECIAL_FILE', result.stderr)


if __name__ == '__main__':
    unittest.main()
