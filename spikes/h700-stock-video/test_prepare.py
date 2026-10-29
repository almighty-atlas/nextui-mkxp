# SPDX-License-Identifier: MIT
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('stock_prepare', HERE/'prepare.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def metadata():
    # Original text fixture only, never linked into or masquerading as a GPU DSO.
    text = '''[Requesting program interpreter: /lib/ld-linux-aarch64.so.1]
  (NEEDED) Shared library: [libSDL2-2.0.so.0]
  (NEEDED) Shared library: [libc.so.6]
  GNU_STACK 0x000000 0x000000 0x000000 0x000000 0x000000 RW 0x10
  OS: Linux, ABI: 4.9.0
Version needs section '.gnu.version_r' contains 1 entry:
  0x0010: Name: GLIBC_2.17 Flags: none Version: 2
Version definition section '.gnu.version_d' contains 1 entry:
  0x0000: Rev: 1 Flags: none Index: 2 Cnt: 1 Name: GLIBC_99.99
'''
    for i, name in enumerate(sorted(M.SDL_IMPORTS)):
        text += f' {i+1}: 0000000000000000 0 FUNC GLOBAL DEFAULT UND {name}\n'
    text += ' 22: 0000000000000000 0 FUNC GLOBAL DEFAULT UND printf@GLIBC_2.17 (2)\n'
    return text


HEADER = b'\x7fELF\x02\x01\x01'+bytes(9)+struct.pack('<HH', 2, 183)


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.prepared = Path(cls.temp.name)/'prepared'
        cls.preparation = M.prepare(cls.prepared)

    def test_exact_original_variant_launcher_license_guard(self):
        p = self.prepared
        self.assertEqual(M.sha((p/'triangle-original.c').read_bytes()), M.ORIGINAL)
        self.assertEqual(M.sha((p/'triangle-proc.c').read_bytes()), M.VARIANT)
        self.assertEqual(self.preparation['status'], 'SOURCE_PREPARED')
        for name in ('launch.sh', 'SOURCE_ONLY'):
            self.assertEqual((p/M.PAK/name).read_bytes(),
                             M.blob(M.PR23, 'spikes/h700-video/'+M.PAK+'/'+name))
        self.assertIn('MIT License', (p/'LICENSE').read_text())
        self.assertFalse((p/M.PAK/'bin').exists())

    def test_source_surface_and_timing_unchanged(self):
        source = (self.prepared/'triangle-proc.c').read_text()
        self.assertEqual(source.count('SDL_GL_GetProcAddress('), 26)
        self.assertIn('#define RUN_MS 5000u', source)
        self.assertIn('#define MAX_FRAMES 625u', source)
        self.assertIn('p_glDrawArrays(GL_TRIANGLES,0,3)', source)
        self.assertNotIn('eglGetCurrentDisplay', source)
        self.assertNotIn('eglQueryString', source)
        self.assertLess(source.index('SDL_GL_MakeCurrent('), source.index('SDL_GL_GetProcAddress('))

    def test_launcher_syntax_and_source_only_before_writes(self):
        launcher = self.prepared/M.PAK/'launch.sh'
        subprocess.run(['/bin/sh', '-n', str(launcher)], check=True)
        env = {'PATH': '/usr/bin:/bin', 'PLATFORM': 'h700', 'DEVICE': 'rg35xxpro',
               'SDCARD_PATH': '/mnt/SDCARD', 'USERDATA_PATH': '/mnt/SDCARD/.userdata/h700',
               'SYSTEM_PATH': '/mnt/SDCARD/.system/h700', 'SDL_VIDEODRIVER': 'mali'}
        result = subprocess.run(['/bin/sh', str(launcher)], env=env,
                                capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 90)
        self.assertEqual(result.stderr, 'RMXP_VIDEO launcher_code=90\n')
        self.assertEqual(result.stdout, '')

    def test_launcher_ssh_refusal(self):
        result = subprocess.run(['/bin/sh', str(self.prepared/M.PAK/'launch.sh')],
                                env={'SSH_CONNECTION': 'test'}, capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 81)

    def test_output_existing_or_inside_repository_is_refused(self):
        with self.assertRaises(FileExistsError):
            M.prepare(self.prepared)
        with self.assertRaisesRegex(ValueError, 'outside repository'):
            M.fresh(M.REPO/'must-not-create-stock-test')

    def test_prepare_never_fetches_and_copies_only_original_sources(self):
        self.assertEqual(set(self.preparation['files']), {
            'LICENSE', M.PAK+'/launch.sh', M.PAK+'/SOURCE_ONLY',
            'docs/build/issue-26-inputs.json',
            *('scripts/'+n for n in ('issue_26_proc_variant.py', 'issue_26_sandbox.py',
                                    'issue_26_sysroot.py', 'issue_26_sdl_proc.py')),
            'scripts/issue_26_tests/test_proc.py',
            *('scripts/issue_26_tests/fixtures/'+n for n in ('LICENSE', 'PROVENANCE.md',
              'triangle-original.c', 'mock_proc.c', 'include/GLES2/gl2.h', 'include/SDL2/SDL.h')),
        })

    def test_elf_metadata_accepts_only_reviewed_contract(self):
        facts = M.parse_elf(HEADER, metadata())
        self.assertEqual(facts['glibc_needs'], ['GLIBC_2.17'])
        self.assertEqual(len(facts['sdl_undefined']), 21)

    def test_wrong_abi_or_type_rejected(self):
        for header in (b'not-elf', HEADER[:16]+struct.pack('<HH', 2, 62),
                       HEADER[:16]+struct.pack('<HH', 3, 183)):
            with self.subTest(header=header):
                with self.assertRaises(ValueError):
                    M.parse_elf(header, metadata())

    def test_loader_kernel_glibc_and_stack_guards(self):
        for old, new in (('/lib/ld-linux-aarch64.so.1', '/lib/ld-musl-aarch64.so.1'),
                         ('ABI: 4.9.0', 'ABI: 4.19.0'),
                         ('Name: GLIBC_2.17', 'Name: GLIBC_2.28'),
                         ('Name: GLIBC_2.17', 'Name: GLIBC_PRIVATE'),
                         ('RW 0x10', 'RWE 0x10')):
            with self.subTest(new=new):
                with self.assertRaises(ValueError):
                    M.parse_elf(HEADER, metadata().replace(old, new))

    def test_needed_rpath_textrel_guards(self):
        for extra in ('(NEEDED) [libGLESv2.so.2]', '(NEEDED) [libEGL.so.1]',
                      '(RUNPATH) [/private]', '(RPATH) [/private]', '(TEXTREL) 0x0'):
            with self.subTest(extra=extra):
                with self.assertRaises(ValueError):
                    M.parse_elf(HEADER, metadata()+'\n'+extra)

    def test_missing_extra_or_versioned_import_rejected(self):
        for text in (metadata().replace('UND SDL_Init', 'UND SDL_Init@SDL_2.0'),
                     metadata().replace('UND SDL_Init', 'UND SDL_Unexpected'),
                     metadata()+'\n 23: 0 0 FUNC GLOBAL DEFAULT UND glDrawArrays',
                     metadata()+'\n 23: 0 0 FUNC GLOBAL DEFAULT UND glDrawArrays@GLIBC_2.17',
                     metadata()+'\n 23: 0 0 FUNC GLOBAL DEFAULT UND eglGetCurrentDisplay'):
            with self.subTest(text=text[-100:]):
                with self.assertRaises(ValueError):
                    M.parse_elf(HEADER, text)

    def test_readelf_child_clean_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/'fixture'
            file.write_bytes(HEADER+bytes(64))
            result = subprocess.CompletedProcess([], 0, metadata(), '')
            with patch.object(M.subprocess, 'run', return_value=result) as run:
                M.inspect(file, Path('/trusted/readelf'))
            self.assertEqual(run.call_args.kwargs['env'], M.ENV)
            self.assertNotIn('shell', run.call_args.kwargs)
            self.assertNotIn('LD_PRELOAD', run.call_args.kwargs['env'])

    def test_real_host_elf_is_not_an_aarch64_candidate(self):
        tool = Path(os.environ.get('STOCK_TEST_READELF', '/usr/bin/readelf'))
        with self.assertRaises(ValueError):
            M.inspect(Path('/bin/sh').resolve(), tool)

    def test_assemble_keeps_guard_and_excludes_all_runtime_libraries(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)/'build'
            build.mkdir()
            # Metadata-only assembly fixture, NOT an executable or a link input.
            payload = b'NOT_A_TARGET_ELF_TEST_ONLY'
            (build/'triangle-proc').write_bytes(payload)
            receipt = {'status': 'SDL_ONLY_HOST_LINKED', 'variant_sha256': M.VARIANT,
                       'original_sha256': M.ORIGINAL, 'variant': {'sha256': M.sha(payload)}}
            (build/'result.json').write_text(json.dumps(receipt))
            output = Path(tmp)/'output'
            with patch.object(M, 'inspect', return_value={'sha256': M.sha(payload)}):
                report = M.assemble(self.prepared, build, output, Path('/trusted/readelf'))
            self.assertTrue((output/M.PAK/'SOURCE_ONLY').is_file())
            self.assertEqual(report['h700_runtime'], 'NOT_TESTED')
            self.assertEqual(set(report['files']), {M.PAK+'/'+p for p in (
                'launch.sh', 'SOURCE_ONLY', 'LICENSE', 'source/triangle-proc.c', 'bin/triangle')})
            self.assertEqual(len(list(output.rglob('*'))), 11)

    def test_assemble_rejects_unverified_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)/'build'
            build.mkdir()
            (build/'result.json').write_text(json.dumps({'status': 'UNKNOWN'}))
            with self.assertRaises(ValueError):
                M.assemble(self.prepared, build, Path(tmp)/'output', Path('/trusted/readelf'))
            self.assertFalse((Path(tmp)/'output').exists())


if __name__ == '__main__':
    unittest.main()
