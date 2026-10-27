import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inspector", ROOT / "tools/inspect_h700_libc.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
TOOL = Path(os.environ.get("H700_TEST_READELF", "/usr/bin/readelf"))
DEFS = """Version symbols section '.gnu.version' contains 2 entries:
  000: GLIBC_9.99
Version definition section '.gnu.version_d' contains 3 entries:
  0x0000: Rev: 1 Flags: BASE Index: 1 Cnt: 1 Name: libc.so.6
  0x001c: Rev: 1 Flags: none Index: 2 Cnt: 1 Name: GLIBC_2.17
  0x0038: Rev: 1 Flags: none Index: 3 Cnt: 2 Name: GLIBC_2.27
  0x0054: Parent 1: GLIBC_9.98
Version needs section '.gnu.version_r' contains 1 entry:
  0x0010: Name: GLIBC_9.97 Flags: none Version: 4
"""


def elf_fixture():
    """Original synthetic metadata, not a runnable library or a link stub."""
    names = b"\0.shstrtab\0.dynstr\0.gnu.version_d\0.dynamic\0"
    strings = b"\0libc.so.6\0GLIBC_2.17\0GLIBC_2.27\0"
    defs = b"".join(
        struct.pack("<HHHHIII", 1, 0, i + 1, 1, 0, 20, 28 if i < 2 else 0)
        + struct.pack("<II", strings.index(name), 0)
        for i, name in enumerate((b"libc.so.6", b"GLIBC_2.17", b"GLIBC_2.27"))
    )
    strings_offset = 176 + len(names)
    dynamic = struct.pack("<qQqQqQqQ", 5, strings_offset, 10, len(strings), 14, 1, 0, 0)
    payloads = (names, strings, defs, dynamic)
    data = bytearray(176)
    sections = [bytes(64)]
    for name, kind, payload, link, count, entsize in zip(
        (b".shstrtab", b".dynstr", b".gnu.version_d", b".dynamic"),
        (3, 3, 0x6ffffffd, 6), payloads, (0, 0, 2, 2), (0, 0, 3, 0), (0, 0, 0, 16),
    ):
        sections.append(struct.pack("<IIQQQQIIQQ", names.index(name), kind, 0, 0,
                                    len(data), len(payload), link, count, 1, entsize))
        data.extend(payload)
    offset = len(data)
    data.extend(b"".join(sections))
    data[:64] = struct.pack("<16sHHIQQQIHHHHHH", b"\x7fELF\x02\x01\x01" + bytes(9),
                            3, 183, 1, 0, 64, offset, 0, 64, 56, 2, 64, 5, 1)
    data[64:120] = struct.pack("<IIQQQQQQ", 1, 4, 0, 0, 0, len(data), len(data), 1)
    dynamic_offset = 176 + len(names) + len(strings) + len(defs)
    data[120:176] = struct.pack("<IIQQQQQQ", 2, 4, dynamic_offset, dynamic_offset,
                                dynamic_offset, len(dynamic), len(dynamic), 1)
    return bytes(data)


class LibcInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "private path libc"
        self.file.write_bytes(elf_fixture())
        self.sha = hashlib.sha256(self.file.read_bytes()).hexdigest()

    def inspect(self):
        return M.inspect(self.file, TOOL, self.sha)

    def test_definitions_not_needs_symbols_or_parents(self):
        self.assertEqual(M.provider_versions(DEFS), ["GLIBC_2.17", "GLIBC_2.27"])

    def test_numeric_order_and_no_private_or_injected_text(self):
        text = DEFS.replace("GLIBC_2.17", "GLIBC_2.9").replace("GLIBC_2.27", "GLIBC_2.10")
        self.assertEqual(M.provider_versions(text), ["GLIBC_2.9", "GLIBC_2.10"])
        for bad in ("GLIBC_PRIVATE", "GLIBC_2.27/private", "GLIBC_2.27 injected"):
            self.assertNotIn(bad, M.provider_versions(DEFS.replace("GLIBC_2.27", bad)))

    def test_needs_only_is_not_a_provider(self):
        self.assertEqual(M.provider_versions(DEFS.split("Version needs")[1]), [])

    def test_exact_hash_before_readelf(self):
        with patch.object(M, "readelf") as reader:
            with self.assertRaisesRegex(M.Blocked, "SHA256_MISMATCH"):
                M.inspect(self.file, TOOL)
            reader.assert_not_called()

    def test_wrong_abi_rejected(self):
        data = bytearray(self.file.read_bytes())
        data[18:20] = struct.pack("<H", 62)
        self.file.write_bytes(data)
        self.sha = hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(M.Blocked, "AARCH64"):
            self.inspect()

    def test_symlink_rejected(self):
        link = self.file.with_name("alias")
        link.symlink_to(self.file)
        with self.assertRaisesRegex(M.Blocked, "SYMLINK"):
            M.inspect(link, TOOL, self.sha)

    def test_fifo_rejected_without_wait(self):
        fifo = self.file.with_name("fifo")
        os.mkfifo(fifo)
        with self.assertRaisesRegex(M.Blocked, "REGULAR"):
            M.inspect(fifo, TOOL, self.sha)

    def test_missing_and_relative_tool(self):
        for tool in (Path("readelf"), Path("/nonexistent/readelf")):
            with self.assertRaisesRegex(M.Blocked, "TRUSTED_READELF"):
                M.inspect(self.file, tool, self.sha)

    def test_real_readelf_on_synthetic_metadata(self):
        report = self.inspect()
        self.assertEqual(report["glibc_provider_definitions"], ["GLIBC_2.17", "GLIBC_2.27"])
        self.assertTrue(report["defines_GLIBC_2_27"])
        self.assertEqual(report["h700_runtime"], "NOT_TESTED")
        self.assertNotIn(str(self.file), json.dumps(report))
        self.assertEqual(hashlib.sha256(self.file.read_bytes()).hexdigest(), self.sha)

    def test_no_definitions_is_blocked(self):
        with patch.object(M, "readelf", side_effect=["(SONAME) [libc.so.6]", ""]):
            with self.assertRaisesRegex(M.Blocked, "NO_PUBLIC"):
                self.inspect()

    def test_wrong_soname_is_blocked(self):
        with patch.object(M, "readelf", return_value="(SONAME) [libSDL2.so]"):
            with self.assertRaisesRegex(M.Blocked, "SONAME"):
                self.inspect()

    def test_concurrent_mutation_is_blocked(self):
        with patch.object(M, "digest", side_effect=[(self.sha, self.file.read_bytes()[:20]),
                                                   ("0" * 64, b"")]):
            with self.assertRaisesRegex(M.Blocked, "INPUT_CHANGED"):
                self.inspect()

    def test_newer_version_does_not_imply_older_definition(self):
        with patch.object(M, "readelf", side_effect=["(SONAME) [libc.so.6]",
                                                   DEFS.replace("GLIBC_2.27", "GLIBC_2.28")]):
            self.assertFalse(self.inspect()["defines_GLIBC_2_27"])

    def test_bounded_file_and_missing_input(self):
        self.file.write_bytes(b"short")
        with self.assertRaisesRegex(M.Blocked, "REGULAR_BOUNDED"):
            self.inspect()
        with self.file.open("wb") as stream:
            stream.truncate(M.MAX_SIZE + 1)
        with self.assertRaisesRegex(M.Blocked, "REGULAR_BOUNDED"):
            self.inspect()
        self.file.unlink()
        with self.assertRaisesRegex(M.Blocked, "INPUT_UNAVAILABLE"):
            self.inspect()

    def test_actual_readelf_under_hostile_parent_environment(self):
        with patch.dict(os.environ, {"PATH": "/nonexistent", "LD_PRELOAD": "/nonexistent.so",
                                     "LD_LIBRARY_PATH": "/nonexistent", "LD_AUDIT": "/nonexistent.so",
                                     "LC_ALL": "invalid_locale", "PKG_CONFIG_PATH": "/nonexistent"}):
            self.assertTrue(self.inspect()["defines_GLIBC_2_27"])

    def test_child_env_and_descriptor_not_input_path(self):
        result = subprocess.CompletedProcess([], 0, b"safe", b"")
        with patch.object(M.subprocess, "run", return_value=result) as run:
            self.assertEqual(M.readelf(42, TOOL, "--dynamic"), "safe")
        args, kwargs = run.call_args
        self.assertEqual(args[0][-1], "/proc/self/fd/42")
        self.assertEqual(kwargs["pass_fds"], (42,))
        self.assertEqual(kwargs["env"], M.ENV)
        self.assertNotIn("LD_PRELOAD", kwargs["env"])
        self.assertNotIn("shell", kwargs)

    def test_tool_failure_warning_and_timeout_are_sanitized(self):
        for result in (subprocess.CompletedProcess([], 1, b"", b"/private"),
                       subprocess.CompletedProcess([], 0, b"", b"warning /private")):
            with patch.object(M.subprocess, "run", return_value=result):
                with self.assertRaisesRegex(M.Blocked, "READELF_FAILED_OR_WARNED"):
                    M.readelf(42, TOOL, "--dynamic")
        with patch.object(M.subprocess, "run", side_effect=subprocess.TimeoutExpired("private", 15)):
            with self.assertRaisesRegex(M.Blocked, "READELF_UNAVAILABLE_OR_TIMEOUT"):
                M.readelf(42, TOOL, "--dynamic")

    def test_cli_fails_closed_without_private_path(self):
        result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "tools/inspect_h700_libc.py"),
                                 str(self.file), "--readelf", str(TOOL)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reason"], "SHA256_MISMATCH")
        self.assertNotIn(str(self.file), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
