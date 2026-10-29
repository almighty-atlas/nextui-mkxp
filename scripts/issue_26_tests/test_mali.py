import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from issue_26_mali import SONAMES, interface_errors, link_outcome


class MaliInterfaceTests(unittest.TestCase):
    def setUp(self):
        # Metadata fixtures only: no ELF/stub library is created or linked.
        self.facts = {role: {'machine': 183, 'type': 3, 'soname': soname,
                            'sha256': 'a' * 64, 'rpaths': [], 'exports': ['fixture_symbol'],
                            'needed': ['libc.so.6'], 'required_versions': ['GLIBC_2.17']}
                      for role, soname in SONAMES.items()}
        self.approvals = {role: {'sha256': 'a' * 64, 'source_id': 'synthetic fixture only',
                                'license_review': 'synthetic fixture only',
                                'platform': 'H700_MALI_FBDEV', 'soname': soname}
                          for role, soname in SONAMES.items()}
        self.symbols = {role: ['fixture_symbol'] for role in SONAMES}
        self.needed = {role: ['libc.so.6'] for role in SONAMES}

    def errors(self, facts=None, approvals=None):
        return interface_errors(self.facts if facts is None else facts,
                                self.approvals if approvals is None else approvals,
                                self.symbols, self.needed)

    def test_missing_library_inputs(self):
        self.assertEqual(len(self.errors(facts={})), 3)
        for role in SONAMES:
            facts = dict(self.facts); del facts[role]
            self.assertIn('missing development input: ' + role, self.errors(facts))

    def test_host_or_bogus_elf(self):
        for machine, kind in ((62, 3), (40, 3), (183, 1), (None, None)):
            facts = copy.deepcopy(self.facts)
            facts['EGL'].update(machine=machine, type=kind)
            self.assertIn('not AArch64 shared ELF: EGL', self.errors(facts))

    def test_soname_and_dll_mismatch(self):
        for value in ('EGL.dll', 'libGL.so.1', 'libEGL.so.2', None):
            facts = copy.deepcopy(self.facts); facts['EGL']['soname'] = value
            self.assertIn('SONAME mismatch: EGL', self.errors(facts))

    def test_unknown_provenance_and_changed_bytes(self):
        self.assertTrue(self.errors(approvals={}))
        facts = copy.deepcopy(self.facts); facts['SDL2']['sha256'] = 'b' * 64
        self.assertIn('unreviewed input provenance: SDL2', self.errors(facts))
        approval = copy.deepcopy(self.approvals); approval['EGL']['platform'] = 'TRIMUI_POWERVR'
        self.assertTrue(self.errors(approvals=approval))

    def test_exports_and_dependency_closure(self):
        for key, value in (('exports', []), ('needed', ['libIMGegl.so']),
                           ('rpaths', ['/usr/lib']), ('required_versions', ['GLIBC_PRIVATE']),
                           ('required_versions', ['GLIBC_2.29'])):
            facts = copy.deepcopy(self.facts); facts['GLESv2'][key] = value
            self.assertTrue(self.errors(facts))

    def test_unexpected_success_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unexpected successful link'):
            link_outcome(0, self.errors(approvals={}))
        self.assertEqual(link_outcome(1, self.errors(approvals={})), 'LINK_BLOCKED')

    def test_static_metadata_match_is_not_runtime_or_release(self):
        self.assertEqual(self.errors(), [])
        self.assertEqual(link_outcome(0, []),
                         'TRIANGLE_HOST_LINKED_RUNTIME_AND_DISTRIBUTION_BLOCKED')
