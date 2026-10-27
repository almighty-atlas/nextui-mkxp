"""Host-only metadata gate for the single owner-fingerprinted H700 libc.

Never executes a target ELF. No network, device access, downloads or file writes.
Linux host with trusted GNU readelf required. See docs/H700_HOST_LIBC.md.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess


EXPECTED_SHA256 = "dd80538bfc685542511168f4cde5dcce476c22d310e727578f17cf23eebb6822"
MAX_SIZE = 32 * 1024 * 1024
ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"}
VERSION = re.compile(r"GLIBC_[0-9]+(?:\.[0-9]+)+\Z")


class Blocked(Exception):
    """A deliberately path-free diagnostic safe for shared reports."""


def provider_versions(text):
    """Read VERDEF names only, never VERNEED, VERSYM or parent labels."""
    definitions = False
    versions = set()
    for line in text.splitlines():
        if line.startswith("Version "):
            definitions = line.startswith("Version definition section ")
        if definitions:
            match = re.search(r"\bRev:.*\bName: (\S+)\s*$", line)
            if match and VERSION.fullmatch(match[1]):
                versions.add(match[1])
    return sorted(versions, key=lambda v: tuple(map(int, v[6:].split("."))))


def readelf(fd, tool, option):
    # Fixed descriptor path avoids path replacement between hashing and inspection.
    # The child inherits only this explicitly passed target descriptor.
    try:
        result = subprocess.run(
            [str(tool), "--wide", option, f"/proc/self/fd/{fd}"],
            env=ENV, pass_fds=(fd,), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Blocked("READELF_UNAVAILABLE_OR_TIMEOUT") from None
    if result.returncode or result.stderr or len(result.stdout) > 8 * 1024 * 1024:
        raise Blocked("READELF_FAILED_OR_WARNED")
    return result.stdout.decode("ascii", errors="replace")


def digest(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    data = bytearray()
    while chunk := os.read(fd, 65536):
        data.extend(chunk)
        if len(data) > MAX_SIZE:
            raise Blocked("FILE_TOO_LARGE")
    return hashlib.sha256(data).hexdigest(), bytes(data[:20])


def inspect(path, tool, expected=EXPECTED_SHA256):
    if not tool.is_absolute() or not tool.is_file():
        raise Blocked("ABSOLUTE_TRUSTED_READELF_REQUIRED")
    try:
        initial = path.lstat()
        if stat.S_ISLNK(initial.st_mode):
            raise Blocked("INPUT_UNAVAILABLE_OR_SYMLINK")
        if not stat.S_ISREG(initial.st_mode) or not 64 <= initial.st_size <= MAX_SIZE:
            raise Blocked("REGULAR_BOUNDED_ELF_REQUIRED")
        # Preflight avoids opening known devices/FIFOs; fstat rechecks the opened fd.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise Blocked("INPUT_UNAVAILABLE_OR_SYMLINK") from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 64 <= info.st_size <= MAX_SIZE:
            raise Blocked("REGULAR_BOUNDED_ELF_REQUIRED")
        sha, header = digest(fd)
        if sha != expected:
            raise Blocked("SHA256_MISMATCH")
        if (header[:7] != b"\x7fELF\x02\x01\x01"
                or struct.unpack_from("<HH", header, 16) != (3, 183)):
            raise Blocked("AARCH64_ELF64_LE_ET_DYN_REQUIRED")
        dynamic = readelf(fd, tool, "--dynamic")
        sonames = re.findall(r"\(SONAME\).*\[([^\]]+)\]", dynamic)
        if sonames != ["libc.so.6"]:
            raise Blocked("LIBC_SONAME_REQUIRED")
        versions = provider_versions(readelf(fd, tool, "--version-info"))
        if not versions:
            raise Blocked("NO_PUBLIC_GLIBC_DEFINITIONS")
        # Detect ordinary concurrent modification; this is not a hostile-writer jail.
        if digest(fd)[0] != sha:
            raise Blocked("INPUT_CHANGED")
        return {
            "status": "HOST_METADATA_ONLY",
            "sha256": sha,
            "elf": "ELF64_LE_AARCH64_ET_DYN",
            "soname": "libc.so.6",
            "glibc_provider_definitions": versions,
            "defines_GLIBC_2_17": "GLIBC_2.17" in versions,
            "defines_GLIBC_2_27": "GLIBC_2.27" in versions,
            "full_symbol_and_dependency_compatibility": "NOT_TESTED",
            "h700_runtime": "NOT_TESTED",
            "distribution": "BLOCKED",
        }
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("libc", type=Path, help="already authorized local regular file")
    parser.add_argument("--readelf", type=Path, default=Path("/usr/bin/readelf"))
    args = parser.parse_args()
    try:
        report = inspect(args.libc, args.readelf)
    except (Blocked, OSError) as error:
        reason = str(error) if isinstance(error, Blocked) else "HOST_IO_ERROR"
        print(json.dumps({"status": "BLOCKED", "reason": reason,
                          "h700_runtime": "NOT_TESTED"}, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
