# H700 runtime follow-up: host-only glibc definition gate

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
   other glibc DSOs remain separate gates. The extended host tool can now inspect
   each of the four fingerprinted DSOs individually; none has been acquired or
   inspected here.
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
GNU `readelf` path. The positional argument and `--readelf` interface are unchanged.
Its CLI has **no hash/target/SONAME override option**. It:

- Rejects final-component symlinks, non-regular/too small/over-32-MiB inputs.
- Selects exactly one entry of the fixed target table by SHA-256 **before invoking
  readelf**, never by the input filename. An unknown or ambiguous digest fails
  closed without printing an expected filename. Another firmware DSO requires a
  reviewed new fingerprint, not a bypass flag.
- Checks ELF64 little-endian AArch64 ET_DYN and the selected entry's exact SONAME.
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

### Extended targets

All four fingerprints are copied verbatim from
[PR #28's pinned metadata report](https://github.com/almighty-atlas/nextui-mkxp/blob/69cddf33056ab5c2840540c49393ea934584f9c5/docs/H700_RUNTIME_METADATA.md).
The table is source-pinned; tests pin all four values and their uniqueness.

| Required SONAME | Owner-reported SHA-256 | Actual-file assessment |
| --- | --- | --- |
| `libc.so.6` | `dd80538bfc685542511168f4cde5dcce476c22d310e727578f17cf23eebb6822` | BLOCKED |
| `libm.so.6` | `b24316bc659ab74096d8679a9e423c1673082649bf148b513579b5acb4e9294a` | BLOCKED |
| `libdl.so.2` | `7f0db218d2126ed6d8df831a24abb0e1b6e96e3952813944a914051ea712440b` | BLOCKED |
| `libpthread.so.0` | `cc12f9592e8d130630b7e95a390aa238dfad6d4092615a65c516e3cf93d30aa3` | BLOCKED |

Each remains **BLOCKED until the owner separately authorizes a local copy of that
specific file**. One invocation inspects one approved file, not a directory or a
dependency closure. The table does not authorize transfer or inspection. SDL,
EGL, GLES, Mali and the dynamic loader are deliberately not added as targets.
Namespace membership in these files still cannot prove exact symbol resolution,
loader pairing or H700 compatibility.

### Prepared owner authorization request (text only, not consent)

**Deutsch:** Erlaubst du ausdrücklich die rein lesende Metadatenprüfung der vier
oben per SHA-256 identifizierten GLIBC-Dateien `libc.so.6`, `libm.so.6`,
`libdl.so.2` und `libpthread.so.0` auf deinem vertrauenswürdigen Linux-Host?
Bitte gib jede Datei einzeln frei; die Freigabe einer Datei gilt nicht für die
anderen. Einen gegebenenfalls erforderlichen Übertragungsweg wählst du selbst;
dieser Auftrag führt keine Übertragung und keinerlei Geräteaktion aus. Die
Dateien bleiben auf deinem Host und werden weder ins Repository noch als Anhang
hochgeladen. Nur das lokal geprüfte, gefilterte JSON wird geteilt; keine
Binärdateien oder rohen Symboltabellen. SDL-/GPU-Dateien und ein Grafiktest sind
ausgeschlossen. Ohne deine ausdrückliche Freigabe bleibt die jeweilige Prüfung
BLOCKED.

**English:** Do you explicitly authorize read-only metadata inspection of the four
GLIBC files identified above by SHA-256 (`libc.so.6`, `libm.so.6`, `libdl.so.2`,
`libpthread.so.0`) on your trusted Linux host? Please approve each file separately;
approval of one does not cover the others. You choose any required transfer
method; this task performs no transfer and no device action. Files stay on your
host, with no repository or attachment uploads. Only locally reviewed, filtered
JSON is shared, never binaries or raw symbol tables. SDL/GPU files and graphics
testing are excluded. Each inspection remains BLOCKED without explicit approval.

## Reproduction — development host only

Synthetic offline suite (no stock binaries, compiler, network or H700 needed):

```sh
python3 -I -B -m unittest discover -s tests -p test_h700_host_libc.py -v
git diff --check origin/main...HEAD
```

**Only after separate authorization of an already local glibc DSO copy**, on the
owner's Linux development host, not the handheld:

```sh
python3 -I -B tools/inspect_h700_libc.py /approved/local/libc.so.6 --readelf /usr/bin/readelf
```

No transfer/download/device command is provided or performed. Do not upload libc,
SDL, vendor libraries, firmware or raw readelf dumps. Review filtered JSON locally
before sharing. Missing GLIBC_2.27 in the specific DSO required to provide it would
block that namespace requirement; it is not required in all four DSOs merely
because private SDL needs it somewhere. Presence only permits later exact
symbol/provider/closure review.

## Initial verification (commit `1a7fb1d`)

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

Initial output: `Ran 18 tests` / `OK`. The untracked local wrapper's only command:

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

## Extension verification (2026-10-27)

Continuation on the same PR #29 branch, without rewriting `1a7fb1d` or touching
PRs #27/#28. Only the inspector, its tests and this document change in this
follow-up. `docs/COMPATIBILITY.md` and the proposed workflow remain unchanged.

The parser already handled `Hash:` fields and separate parent lines; explicit
regressions now verify those cases, BASE SONAME exclusion and
`GLIBC_ABI_DT_RELR` exclusion. Four original, synthetic, metadata-only ELF fixtures
exercise actual host GNU readelf for target-specific SONAME acceptance/rejection.
Their digest is **mocked** to select each production policy; this is not evidence
that any fixture matches a real firmware hash or that a real DSO was inspected.
Additional tests pin all four hashes, reject ambiguous hashes and filename-based
bypasses, and verify CLI rejection of policy-override flags.

Using the exact private-tool command above, the final suite reports:

```text
Ran 28 tests in 0.524s

OK
```

| Extension check | Evidence level | Result |
| --- | --- | --- |
| Full suite including all 18 original tests and 10 added tests | verified-on-host | PASS, 28 tests |
| Four code/documentation hashes vs pinned PR #28 report | STATIC | PASS |
| Full branch diff whitespace and changed-file review | STATIC | PASS |
| Active CI | CI | BLOCKED; proposed file unchanged, no activation attempted |
| Actual four owner-fingerprinted DSOs | HOST | BLOCKED; no authorized copies read |
| SDL/Mali/GLES2/ION, presentation and NextUI return | H700 | NOT_TESTED |

Exact final diff-check/stat commands and outputs are recorded in the updated PR:

```sh
git diff --check origin/main...HEAD
git diff origin/main...HEAD --stat
```

The first command emits nothing and exits 0. The complete PR includes the original
commit's proposed workflow and compatibility note; this follow-up changes neither.

## Next step and safety boundary

Smallest follow-up: a separate owner decision about local inspection of **each
fingerprinted glibc DSO**, starting with libc, then filtered metadata review. No device action is
requested now. Afterward review exact transitive symbol/provider requirements and
SDL identities before proposing a separately approved NextUI-Tools visual test
for Issue #22. GPL-noticed Mali code, patches, vendor, glibc and GCC runtime rights
remain independent gates.

No firmware/service/Pak/library changes, vendor downloads, proprietary publication,
device connections, GPU opens, target executions, merges or issue closures.
PRs #27/#28 and earlier branches stay untouched. Rollback is dropping this
unmerged source-only branch; there is no device state to restore.
