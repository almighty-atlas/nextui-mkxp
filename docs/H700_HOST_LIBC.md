# H700 runtime follow-up: host-only libc definition gate

Refs [Issue #1](https://github.com/almighty-atlas/nextui-mkxp/issues/1).
Assessment date: **2026-10-27**. Independent source-only follow-up from
`main` `107db135b8e8ef72f6d61c78be14416330727b0d`.
**No device action or library transfer is authorized.**

## Inventory and next technical step

Reviewed AGENTS, README, roadmap, architecture, test plan, Issues #1/#22/#26
and PRs #27/#28 including reviews and owner observations. Relevant inputs:

| Input | Immutable revision / evidence | What it establishes |
| --- | --- | --- |
| PR #27 | [`1c04c578e3a35acc40b8669986228e3a2ae056c0`](https://github.com/almighty-atlas/nextui-mkxp/tree/1c04c578e3a35acc40b8669986228e3a2ae056c0) | Reported private Linux-4.9 sysroot and SDL-only AArch64 link; not rerun here |
| PR #28 | [`69cddf33056ab5c2840540c49393ea934584f9c5`](https://github.com/almighty-atlas/nextui-mkxp/tree/69cddf33056ab5c2840540c49393ea934584f9c5) | Metadata probe, host fixtures, selected owner-supplied hashes |
| Owner observation | [Issue #1 comment, 2026-10-26](https://github.com/almighty-atlas/nextui-mkxp/issues/1#issuecomment-6429137189) | Linux 4.9.170, sampled AArch64 libraries, session-specific node metadata; no `readelf` |

The highest-value next step is **inspect the already-fingerprinted libc on the
owner's trusted Linux development host**, only if a local copy is separately
authorized. Do not repeat the already successful M4/sysroot/SDL build to guess
the installed libc version. No authorized stock libc is available in this session;
the real-file assessment is **BLOCKED**, not a failed GLIBC compatibility test.

### Keep the four gates separate

1. **Kernel:** PR #27 reports glibc 2.28 built with Linux 4.9.170 headers and
   `--enable-kernel=4.9.0`, and an application ABI note 4.9.0. This addresses the
   earlier toolchain's 4.19 baseline on the host only. It is not an execution
   test or an installed libc identification. Do not strip/spoof ABI notes.
2. **GLIBC:** the application directly needs GLIBC_2.17; private SDL additionally
   needs GLIBC_2.27 and libc/libm/libdl/libpthread. Installed libc definitions
   remain UNKNOWN. A version label is a necessary namespace check, **not exact
   symbol/version/provider resolution** or full closure. Loader pairing and the
   other glibc DSOs remain separate gates.
3. **SDL2:** private audio-disabled SDL is not installed SDL. PR #28 declined to
   read installed SDL symlink targets outside its roots. This is not missing-SDL
   evidence. Classify their path metadata under separate explicit authorization;
   do not broaden roots or shadow system libraries here.
4. **Mali/GLES2:** proc-address loading removes direct EGL/GLES link inputs,
   not vendor runtime dependencies. Reported `/dev/ion`, `/dev/fb0`, `/dev/mali0`
   access in SSH is not normal Pak access or graphics functionality. Vendor
   closure, pixmap/extension ABI, EGL context, physical presentation, orientation
   and responsive NextUI return are **NOT_TESTED**. Mock draw/swap and a void
   SDL swap return cannot prove visible output.

## Implemented host gate

`tools/inspect_h700_libc.py` accepts one local file and a trusted absolute host
GNU `readelf` path. Its CLI has **no hash-override option**. It:

- Rejects final-component symlinks, non-regular/too small/over-32-MiB inputs.
- Requires the owner's reported SHA-256
  `dd80538bfc685542511168f4cde5dcce476c22d310e727578f17cf23eebb6822`
  **before invoking readelf**. Another firmware libc requires a reviewed new
  fingerprint, not a bypass flag.
- Checks ELF64 little-endian AArch64 ET_DYN and SONAME `libc.so.6`.
- Invokes only trusted host readelf, with fixed options, clean child environment,
  no shell, 15-second deadlines and a passed descriptor at `/proc/self/fd/N`.
  No `ldd`, input loader execution or input `dlopen`.
- Reads public numeric **VERDEF** names only, never VERNEED, VERSYM, parent labels
  or GLIBC_PRIVATE. Reports exact GLIBC_2.17/2.27 membership, not a guessed maximum
  or broad compatibility PASS. Warned/failed/empty results fail closed.
- Rehashes afterward to detect ordinary concurrent changes. Filtered JSON omits
  private input paths, arbitrary symbols, raw tool errors and binary contents.
  Exit 0 means **HOST_METADATA_ONLY**, exit 2 means **BLOCKED**.

This is not a malicious-host sandbox or hostile-writer snapshot: it trusts Python,
explicitly selected readelf (including any reviewed wrapper), host libraries and
`/proc`. Child cleanup cannot undo injection into the parent Python process.
Ancestor symlinks are not a directory-containment policy. lstat preflight and fstat
are not an atomic snapshot: only supply approved regular files. Captured output is
checked after capture (8 MiB), not a hard subprocess-memory limit. Hashes identify
bytes, not provenance or transfer rights. No stock libraries/headers are vendored.

## Reproduction — development host only

Synthetic offline suite (no stock binaries, compiler, network or H700 needed):

```sh
python3 -I -B -m unittest discover -s tests -p test_h700_host_libc.py -v
git diff --check origin/main...HEAD
```

**Only after separate authorization of an already local libc copy**, on the
owner's Linux development host, not the handheld:

```sh
python3 -I -B tools/inspect_h700_libc.py /approved/local/libc.so.6 --readelf /usr/bin/readelf
```

No transfer/download/device command is provided or performed. Do not upload libc,
SDL, vendor libraries, firmware or raw readelf dumps. Review filtered JSON locally
before sharing. Missing GLIBC_2.27 would block the namespace requirement for the
private SDL path; presence only permits later exact symbol/provider/closure review.

## Actual verification in this change

| Check | Evidence level | Result |
| --- | --- | --- |
| 18 offline tests, including actual GNU readelf on original synthetic AArch64 metadata | verified-on-host | PASS |
| Hash before tool invocation; ABI/SONAME; symlink/FIFO/size/missing-file rejection | verified-on-host | PASS |
| VERDEF vs needs/symbols/parents; no inference from newer version; path/error filtering | verified-on-host | PASS |
| Real readelf under hostile PATH/LD/locale/pkg-config; descriptor/clean child environment | verified-on-host | PASS |
| Missing tool, nonzero exit/warnings/timeout, empty definitions, concurrent mutation | verified-on-host | PASS |
| Fingerprinted installed libc provider definitions | HOST | BLOCKED: no separately authorized file |
| New sysroot/SDL cross-build | HOST | NOT_TESTED here; preserve PR #27 evidence |
| SDL/EGL/Mali loading, rendering, input/audio, NextUI return | H700 | NOT_TESTED |
| Combined licensing/distribution | SOURCE | BLOCKED; PR #19 unchanged |

This session initially had neither Python nor readelf. Alpine packages were
installed **non-root into a private user-cache root only**, with package scripts
disabled; no host-wide change. Host tools: Python 3.14.10, GNU readelf 2.45.1.
`/tmp/opencode` was not writable; private tools use the user cache instead. These
tools are not target build inputs or a reproducible cross-toolchain provenance claim.
Initial tests exposed the missing tool selection and incomplete synthetic ELF
program headers; both were corrected before the final run.

Exact final host command, using a temporary trusted readelf wrapper:

```sh
LD_LIBRARY_PATH=/home/opencode/.cache/nextui-host-tools/usr/lib H700_TEST_READELF=/workspace/nextui-mkxp/.git/readelf-host /home/opencode/.cache/nextui-host-tools/usr/bin/python3 -I -B -m unittest discover -s tests -p test_h700_host_libc.py -v
```

Final output: `Ran 18 tests` / `OK`. The untracked local wrapper's only command:

```sh
exec /lib/ld-musl-x86_64.so.1 --library-path /home/opencode/.cache/nextui-host-tools/usr/lib /home/opencode/.cache/nextui-host-tools/usr/bin/readelf "$@"
```

The proposed [CI definition](ci/issue-1-host-libc.yml.proposed) runs the same synthetic suite with Ubuntu's installed Python/readelf after a
pinned checkout, read-only token and no persisted credentials. It checks the
complete event base-to-head diff including docs, uploads nothing and never reads
real firmware or executes ARM code. **CI activation is BLOCKED**: the current
GitHub token cannot create workflows (push rejected for missing `workflow` scope),
and SSH authentication is unavailable. The definition is intentionally stored
outside `.github/workflows`, not active or verified-in-CI. A maintainer can review
and place it at `.github/workflows/issue-1-host-libc.yml` with an appropriately
authorized account. No credential/permission change was attempted. Local tests
above really ran; no successful CI run is claimed.

## Next step and safety boundary

Smallest follow-up: a separate owner decision about local inspection of **this one
fingerprinted LGPL libc**, then filtered metadata review. No device action is
requested now. Afterward review exact transitive symbol/provider requirements and
SDL identities before proposing a separately approved NextUI-Tools visual test
for Issue #22. GPL-noticed Mali code, patches, vendor, glibc and GCC runtime rights
remain independent gates.

No firmware/service/Pak/library changes, vendor downloads, proprietary publication,
device connections, GPU opens, target executions, merges or issue closures.
PRs #27/#28 and earlier branches stay untouched. Rollback is dropping this
unmerged source-only branch; there is no device state to restore.
