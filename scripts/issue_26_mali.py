#!/usr/bin/env python3
"""Offline H700 development-interface gate; no build, loading or target execution.

Facts must come from native readelf of hash-reviewed inputs. An approval map is
separately reviewed evidence, never inferred from filenames or generic symbols.
"""
import re


# Candidate names from source/harvest metadata, not installed ELF attestation.
SONAMES = {'SDL2': 'libSDL2-2.0.so.0', 'EGL': 'libEGL.so.1', 'GLESv2': 'libGLESv2.so.2'}


def interface_errors(facts, approvals, symbols, allowed_needed):
    errors = []
    for role in SONAMES:
        item = facts.get(role)
        approved = approvals.get(role)
        if not item:
            errors.append('missing development input: ' + role)
            continue
        if (not approved or not re.fullmatch('[0-9a-f]{64}', str(approved.get('sha256'))) or
                item.get('sha256') != approved['sha256'] or
                not approved.get('source_id') or not approved.get('license_review') or
                approved.get('platform') != 'H700_MALI_FBDEV'):
            errors.append('unreviewed input provenance: ' + role)
        if item.get('machine') != 183 or item.get('type') != 3:
            errors.append('not AArch64 shared ELF: ' + role)
        soname = approved.get('soname') if approved else None
        if (not isinstance(soname, str) or not re.fullmatch(r'lib[A-Za-z0-9_.+-]+\.so(?:\.[0-9]+)*', soname)
                or item.get('soname') != soname):
            errors.append('SONAME mismatch: ' + role)
        if item.get('rpaths'):
            errors.append('unapproved RPATH/RUNPATH: ' + role)
        if not isinstance(item.get('exports'), list) or set(symbols[role]) - set(item['exports']):
            errors.append('missing exports: ' + role)
        if (role not in allowed_needed or not isinstance(item.get('needed'), list) or
                set(item['needed']) != set(allowed_needed[role])):
            errors.append('unreviewed NEEDED closure: ' + role)
        versions = item.get('required_versions')
        if (not isinstance(versions, list) or any(
                not isinstance(v, str) or not re.fullmatch(r'GLIBC_2\.(?:[0-9]|1[0-9]|2[0-8])', v)
                for v in versions)):
            errors.append('unapproved GLIBC/private/version requirement: ' + role)
    if set(facts) - set(SONAMES):
        errors.append('unknown library role')
    return errors


def link_outcome(returncode, input_errors):
    if input_errors:
        if returncode == 0:
            raise ValueError('unexpected successful link with unreviewed inputs')
        return 'LINK_BLOCKED'
    if returncode != 0:
        return 'LINK_BLOCKED'
    return 'TRIANGLE_HOST_LINKED_RUNTIME_AND_DISTRIBUTION_BLOCKED'
