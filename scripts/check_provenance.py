#!/usr/bin/env python3
"""Offline structural checks for the M0 snapshot; not a license validator."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'docs/audit/source-inventory.json').read_text())
assert data['schema_version'] == 1
for pin in ('mkxp-z', 'r36s'):
    assert re.fullmatch(r'[0-9a-f]{40}', data['pins'][pin]), pin
for group, key, count in [('dependencies', 'component', 56), ('r36s_files', 'path', 24)]:
    rows = data[group]
    assert len(rows) == count, (group, len(rows))
    assert len({r[key] for r in rows}) == len(rows), group
    for row in rows:
        for field in (key, 'evidence_url', 'spdx', 'obligations', 'status'):
            assert row[field], (row[key], field)
        assert '/blob/' in row['evidence_url'] and row['evidence_url'].startswith('https://github.com/')
        assert data['pins']['mkxp-z' if group == 'dependencies' else 'r36s'] in row['evidence_url']
        if group == 'dependencies':
            assert row['source_url'].startswith('https://'), row[key]
            assert row['status'] == 'BLOCKED_FOR_RELEASE'
            assert row['revision']
            assert row['source_sha256'] == 'UNKNOWN' or re.fullmatch(r'[0-9a-f]{64}', row['source_sha256'])
            for patch in row['patches']:
                assert re.fullmatch(r'[0-9a-f]{64}', patch['sha256'])
        else:
            assert re.fullmatch(r'[0-9a-f]{64}', row['sha256'])
            assert row['status'] == 'REFERENCE_ONLY_NO_IMPORT'
assert sum(len(r['patches']) for r in data['dependencies']) == 138
# Check relative Markdown file destinations without accessing the network.
for doc in [ROOT/'docs/SOURCES.md', ROOT/'docs/DISTRIBUTION_GATE.md', ROOT/'docs/audit/ISSUE-003-EVIDENCE.md']:
    for link in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
        if '://' not in link and not link.startswith('#'):
            assert (doc.parent / link.split('#')[0]).exists(), (doc, link)
# License text evidence hashes are content fingerprints, not legal conclusions.
evidence = json.loads((ROOT/'docs/audit/license-evidence.json').read_text())
for row in evidence:
    assert row['url'].startswith('https://raw.githubusercontent.com/')
    assert re.fullmatch(r'[0-9a-f]{64}', row['sha256'])
print('PASS: 56 dependency wraps, 138 patch references, 24 R36S file records; pins, hashes, blocked states and local links valid')
