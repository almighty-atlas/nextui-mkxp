# Issue #4 — C++14 calibration: source prepared, cross build blocked

2026-10-28; continuation of Draft PR #31 from `7a928cd`.
**No new native C++ or AArch64 ELF was produced in this session.**
No mkxp-z build/import, target execution/QEMU, download, Docker socket, remote
connection, container configuration change or handheld action occurred.
PR #19's license/distribution STOP and the engine's #1/#2/#3 gates stay intact.
The current task permits this narrow original host-only calibration conditionally
on real input review; it does not authorize an engine or binary release.

## Evidence assignment — do not confuse two hosts

Read AGENTS, required project docs, the [PR #30 engine plan][PLAN], the
[preflight report](H700_ENGINE_PREFLIGHT.md), Issue #4 and current PR #31.
Inspected original build helpers from PR #27 at
`1c04c578e3a35acc40b8669986228e3a2ae056c0`: sandbox, sysroot recipe, crosscheck,
ELF gate and SDL/proc driver; and PR #30's `prepare.py` at `91b5a27`.
No existing helper or PR #19/#27/#30 was changed.

| Fact | Evidence level / scope |
| --- | --- |
| tiny02, Debian `nextui-mkxp-builder`, network disabled, two CPUs, 5 GiB RAM | Owner-verified host facts supplied in this task; not a local container observation |
| GCC/G++ 8.3.0, target `aarch64-nextui-linux-gnu`, private glibc 2.28/Linux-4.9.170 sysroot | Owner-verified host facts, consistent with PR #27's source recipe |
| Compiler input lock matches sysroot receipt; SDL receipt confirms earlier AArch64 graphics build | **Owner-verified relationship**; no longer “unknown” as an owner fact. Raw receipt paths, bytes and digests were not supplied to this session; no independent file comparison claimed |
| `libstdc++.so.6.0.25`, AArch64 | Owner-verified SHA-256 `678f07e10eecaced61f0686af119680fc6d0a23487b057cc3be5718204716fa4`; needs GLIBC_2.17 and GLIBC_2.18 |
| `libgcc_s.so.1`, AArch64 | Owner-verified SHA-256 `3e250c02603da82479e64559d926bae3964e6ea6128f1c74dc8339bfb97fe476`; needs GLIBC_2.17 |
| GLIBCXX/CXXABI/GCC definitions and exact versioned-symbol providers | Not supplied; file names/GLIBC floors do not establish every C++ symbol provider |
| Current author's host | Linux x86_64 authoring environment, **not tiny02**; no `c++`, `g++` or `clang++` in PATH. No C++ compiler installed/downloaded |

Machine-readable record: [cxx-provider-evidence.json](../build/h700-engine/cxx-provider-evidence.json).
It preserves owner evidence, explicit null/absent raw receipt facts and local
`local_provider_bytes_checked: false`; no receipt hashes or ELF results invented.
The compiler archive pin is the existing PR #27 lock, **not** a sysroot/output
digest. Do not use an older experiment's tree digest as tiny02's current receipt.

## Original test and native runner

`spikes/h700-cxx-abi/probe.cpp`, original MIT source (notice alongside it), uses
C++14 `make_unique`, heap strings/arrays, a forced non-small string, exception
throw/catch and RAII destructors during unwinding and normal scope exit. Checks
require exactly two destructor calls, no live guard and a matching exception
message; failures return nonzero. No assets, SDL, Ruby or game engine.
Source SHA-256:
`30fd3a0216496f30950322bbeb4e2cb7b075022826742bead66095b7c28dd2e4`.

On an **existing trusted Linux x86_64 shell with native C++ compiler**, offline:

```sh
python3 -I -B scripts/h700_cxx_abi.py native --workspace "$FRESH_PRIVATE_DIRECTORY"
# Optional: --compiler /absolute/path/to/trusted/native/g++
```

No Docker/SSH command is supplied. The caller must already be in an approved
host shell; this does not enter/start/change `nextui-mkxp-builder`. Workspace
must be fresh, outside the repository and under an existing private parent.
The runner requires **at least 20 GiB free**, compiles with `-std=c++14 -O0
-Wall -Wextra -Werror`, and validates native x86_64 ELF before executing its
own probe once. AArch64 compiler/probe headers and script wrappers are refused.
Child environment excludes inherited loader/include/config variables; only
trusted native OS tool/headers/runtime are used. Native compiler/helper libraries
remain a trusted host boundary, not a fully fingerprinted sandbox. Private
compiler logs and a result/hash receipt stay outside Git. Failed workspaces are
retained for review, never recursively deleted by the runner.

**Native C++ behavior is NOT_TESTED here**: actual CLI returned
`HOST_BUILD_BLOCKED / NATIVE_CXX_COMPILER_UNAVAILABLE`, exit 2, before writing a
workspace or invoking a compiler. A policy test of the source text is not proof
that it compiles or that its destructors actually ran.

## Prepared cross-build boundary (not an operational cross-link driver)

`scripts/h700_cxx_abi.py` provides reusable offline gates and an explicit blocked
status. [cxx-cross-plan.example.json](../build/h700-engine/cxx-cross-plan.example.json)
is an **incomplete private input-map template**, not a real receipt or approval.
Only the original probe and supplied compiler/provider hashes are filled.
Unknown local paths/digests are null; no source/archive acquisition needed.

```sh
python3 -I -B scripts/h700_cxx_abi.py cross-status
python3 -I -B scripts/h700_cxx_abi.py cross-audit --plan "$REVIEWED_PRIVATE_INPUT_MAP"
```

`cross-status` exits 2 / CROSS_BUILD_BLOCKED for this session. `cross-audit`
only reads supplied local snapshots: verify lock/receipt hashes, PR #27
source-lock/sysroot/SDL linkage, current compiler/sysroot tree digests and exact
provider hashes/AArch64 headers; reject unknown/mismatching inputs and insufficient
disk space. Its input-map digest must be derived from the **already archive-verified**
compiler, not blessed by merely hashing an arbitrary tree. The compiler archive
hash alone does not compare extracted compiler files to archive members.
Use PR #27's existing `verify_archive_tree` for that binding; do not replace it.
If actual tiny02 receipt field names differ from the inspected PR #27 recipe,
stop and review the adapter; never rewrite original receipts to fit this schema.

`search_audit` checks **observed**, nonempty include/library/startup paths:
resolve symlinks, allow only selected C++/GCC header roots and the new sysroot,
separate GCC support-library and C++-provider roots, refuse old SDK or host roots,
and require the non-PIE startup set `crt1.o`, `crti.o`, `crtbegin.o`, `crtend.o`,
`crtn.o`. All five files need matching hashes/AArch64 ET_REL headers. A supplied
search snapshot is not compiler-execution attestation or a complete file closure.
**CROSS_INPUT_AUDIT_ONLY is not build success, an execution grant or a cross link.**

Before any actual link on tiny02, the next adapter must, in a fresh private
directory and the already restricted builder, perform this exact ordering:

1. Check current free space >=20 GiB; revalidate existing input lock/compiler
   archive/extracted compiler, raw sysroot receipt/current tree and the two exact
   providers. Keep source/receipt/tool hashes and explicit local paths privately.
   This calibration intends shared libstdc++/libgcc_s (exception unwinding), not
   the C triangle driver's `-static-libgcc` shortcut; do not copy its flags blindly.
2. Verify trusted **host** G++/cc1plus/collect2/as/ld/readelf and their actual
   source/archive provenance. Record default `-print-sysroot` as **old SDK**, not
   as the selected build root. Apply explicit `--sysroot=<verified-new-root>`.
3. Use `-nostdinc -nostdinc++` plus exact reviewed C++ version/target/backward,
   GCC builtin/include-fixed and new sysroot headers. Use `-fno-pie -no-pie` for
   this calibration's explicit startup contract. Obtain `-E -v -H` search/header
   traces and dependencies using the real probe. Compare every resolved include,
   not just the top-level `-I` arguments. No inherited CPATH/COMPILER_PATH/etc.
4. Obtain the actual G++ `-###`/search-directory/file-selection dry-run with the
   **same flags/source** and check every `-L`, startup, collect2/plugin/support
   path and provider before link. Explicit startup `-B`/library flags must select
   the rebuilt glibc; `--sysroot` alone does not redirect all configured C++ paths.
   If reviewed C++ providers live inside the denied old SDK, stop and review a
   small private provider stage; do not broaden the old-libc search allowance.
5. Inventory/hash exact `crt*`, libstdc++, libgcc_s, GCC support archives,
   **new** libc/libm/loader/libc_nonshared/linker scripts and all script GROUP /
   INPUT members. Do not publish a guessed `-nostdlib` library order before that
   actual closure is available. No unresolved-symbol bypass, stubs or static
   libstdc++ shortcut. The new script intentionally has **no cross-link action**
   while these concrete paths/recipes are unavailable for review.
6. Only then privately compile/link once, capture trace and map, audit all actual
   LOAD/archived/script inputs and repeat link in the same workspace. Audit must
   fail on old SDK libc/startup even if a successful link was produced. Our
   `audit_link_map` helper only verifies fingerprinted LOAD files/no old root;
   archive-member and versioned-symbol closure still require inspection.

**Current blocker:** raw local compiler/sysroot/provider paths/receipts, current
compiler/stdlib search transcripts and exact link closure are unavailable to this
agent; no approved execution transport to tiny02 was provided/used. This is not
“tiny02 absent”, not a new libc/provider failure, and not an engine-license waiver.
No safe cross-link recipe is claimed complete from synthetic metadata tests.

## Host readelf and ELF policy — ready for a real future artifact

```sh
python3 -I -B scripts/h700_cxx_abi.py inspect \
  --elf "$PRIVATE_REAL_ELF" --readelf "$TRUSTED_HOST_READELF" \
  --readelf-sha256 "$REVIEWED_HOST_READELF_SHA256"
```

Requires an actual bounded regular AArch64 ELF and hash-checked native x86_64
readelf; invokes only readelf, never target `ldd`/loader/ARM/QEMU. It records
interpreter, GNU kernel note, NEEDED, GLIBC/GLIBCXX/CXXABI/GCC VERNEED **by provider**,
VERDEF separately, RPATH/RUNPATH, stack/TEXTREL and ELF hash.
`ELF_FACTS_ONLY` explicitly leaves policy and link provenance unevaluated.
`elf_policy` separately requires interpreter `/lib/ld-linux-aarch64.so.1`, ABI
4.9.0, no RPATH/TEXTREL/executable stack, expected C++/GCC/libc dependency surface,
GLIBC <=2.28 and required versions contained in **actual supplied provider**
definitions (including GCC unwind versions). Numeric provider GLIBC floors do
not establish all C++ version namespaces or exact symbol/loader closure.
There is **no actual C++ AArch64 ELF, readelf result or linker map here**.

## Execution evidence and next smallest action

Actual commands and results are recorded below; policy fixtures never establish
C++ runtime, cross-build, engine or H700 success. Existing engine preflight stays
BLOCKED; inactive CI template now discovers both offline suites, still not active
because of the existing workflow-write permission blocker. No CI PASS claimed.

```sh
LD_LIBRARY_PATH=/home/opencode/.cache/nextui-host-tools/usr/lib /home/opencode/.cache/nextui-host-tools/usr/bin/python3 -I -B -m unittest discover -s tests -p 'test_h700*.py' -v
```

```text
Ran 54 tests in 1.087s
OK
```

**verified-on-host:** 32 existing input-preflight tests + 22 new C++ policy/
metadata/CLI tests. Includes positive **synthetic** search/receipt/ELF fixtures,
negative SDK/host paths/symlink escapes/startup sets, receipt/hash mismatches,
20-GiB floor, loader/kernel/version/provider checks, VERNEED vs VERDEF,
map LOAD fingerprints and refusal to execute a non-native compiler/probe.
No mocked successful native build is claimed; no test compiles the C++ source.

Actually attempted, with the same private Python prefix as above:

```sh
python3 -I -B scripts/h700_cxx_abi.py native --workspace /tmp/opencode/nextui-cxx14-native
python3 -I -B scripts/h700_cxx_abi.py cross-status
df -Pk /workspace/nextui-mkxp
sha256sum spikes/h700-cxx-abi/probe.cpp
git diff --check
```

Native CLI: exit 2, `HOST_BUILD_BLOCKED`,
`reason=NATIVE_CXX_COMPILER_UNAVAILABLE`. Cross CLI: exit 2,
`CROSS_BUILD_BLOCKED`, reasons
`TINY02_LOCAL_INPUT_PATHS_AND_RAW_RECEIPTS_UNAVAILABLE` and
`PRELINK_SEARCH_TRANSCRIPTS_AND_LINK_INPUT_INVENTORY_UNAVAILABLE`.
`type c++ g++ clang++ python3` likewise found none in PATH; the existing private
Python 3.14.10 was reused, no installation. `df` reported **35,759,548 KiB**
available locally (>20 GiB), not a tiny02 measurement. Source hash matched the
value above. Whitespace check exited 0 without output. No host/target ELF or
map exists from this attempt, so no actual readelf run is reported.

Next action is to finish **this C++ calibration**, not start mkxp-z: on the existing
approved tiny02 shell, run the native test, provide/bind the raw receipt/path map
and capture the prelink search evidence above. Then implement/review the smallest
actual cross-link adapter using those exact paths and inspect its real ELF/map.
Only a successful calibrated C++/versioned-symbol/provider audit supports the
next engine dependency-lock slice (native Ruby helpers and mandatory libraries);
it still does not authorize engine code import or distribution.

[PLAN]: https://github.com/almighty-atlas/nextui-mkxp/blob/91b5a27378150bb479fc8546f2bddb6c6e5b1da7/docs/H700_MINIMAL_ENGINE_PLAN.md

---

## Owner-observed follow-up on tiny02 and stock H700 (2026-10-28)

**Evidence boundary:** This section reports subsequent commands and outputs
supplied by the device/host owner. It is **not** the original author's
environment, CI evidence, an independent reproduction, or an authorization
to execute the C++ probe on the handheld. The statements above about
`CROSS_BUILD_BLOCKED` and no ELF refer to the **original PR authoring
session**, and do not negate the later private tiny02 observations.

The owner reported:

| Stage | Owner-observed result | Scope |
| --- | --- | --- |
| Native host C++14 compile + run | `NATIVE_HOST_PASS`; 2 destructors | Linux x86_64 on tiny02 only |
| AArch64 C++14 compile | ET_REL SHA-256 `142242a4ccce66e7aa47ae1e9929332b71625dfe9c247f03303eae182212cb8d` | Private cross object |
| AArch64 cross-link | ET_EXEC SHA-256 `748974b7412b321ac81001e2516584d33015a1a880b87eb3d905eef68c9d1b73` | Private linked probe; never executed on H700 |
| Actual link-map path audit | `LINK_MAP_PATH_AUDIT_PASS`; 16 LOAD records | Verified probe object, GCC support, staged C++ providers, rebuilt glibc 2.28; no old SDK libc LOAD |
| ELF policy against build-time providers | `ELF_VERSION_POLICY_PASS` | AArch64, interpreter `/lib/ld-linux-aarch64.so.1`, Linux ABI 4.9.0, no RPATH/RUNPATH or TEXTREL, nonexecutable stack |
| Stock H700 C++ versions | `H700_STOCK_CXX_SYMBOLS_PASS` | Original device libstdc++ and libgcc_s contain all requested versions |
| Stock transitive symbol-version needs | `STOCK_CXX_TRANSITIVE_VERSION_PASS` | Test ELF + five stock AArch64 DSOs; matching VERNEED vs VERDEF and NEEDED names |
| Stock interpreter identity | `H700_INTERPRETER_IDENTITY_PASS` | Device `/lib/ld-linux-aarch64.so.1` resolves to the fingerprinted device loader |
| Stock private glibc symbol names | `GLIBC_PRIVATE_SYMBOL_MATCH_PASS` | 20 undefined private symbol imports: 16 in libc resolved to loader; 4 in libm resolved to libc |
| Target run | `H700_CXX_RUNTIME_NOT_TESTED` | No H700 C++ probe execution approved or performed |
| Distribution | `DISTRIBUTION_BLOCKED` | No binary or game assets committed/released |

Required versioned symbols from the linked probe:
`GLIBC_2.17` (libc), `GCC_3.0` (libgcc_s),
`CXXABI_1.3`, `CXXABI_1.3.9`, `GLIBCXX_3.4`,
`GLIBCXX_3.4.21` (libstdc++). The stock libstdc++ also
needs libc symbols through `GLIBC_2.34`; stock libgcc_s needs
libc through `GLIBC_2.35`. Device glibc/loader/libm provide
version definitions through `GLIBC_2.35`. The glibc 2.28 **build
sysroot** must not be confused with the stock device runtime.

Original device AArch64 library SHA-256 identities, checked again after
copying to private tiny02 scratch:

- `libstdc++.so.6` — `c4834bd79254443665af96b6d5e71d124b7f92f2eea121e61f9fff5204fc594d`
- `libgcc_s.so.1` — `acfe23cf0f5f4ac35b4c314415bb31d6f52a9bd39df8be04dfb2818a571533fd`
- `libc.so.6` — `dd80538bfc685542511168f4cde5dcce476c22d310e727578f17cf23eebb6822`
- `libm.so.6` — `b24316bc659ab74096d8679a9e423c1673082649bf148b513579b5acb4e9294a`
- `ld-linux-aarch64.so.1` — `68a35077a50da30312b60706db5ba027c892c3be4cf42f3fd167ac241e8c01a9`

**Measurement correction:** An early ad-hoc script falsely printed
`MISSING` for all stock C++ symbol versions by splitting on
`Version definition section:` (which does not match actual GNU readelf
headings). Re-check using this PR's `parse_readelf` function returned
all required versions as present. This was a parsing error, not a
device-library change.

**Residual STOP gates:** Versioned and private *symbol-name* matches do
not prove full unversioned symbol resolution, dynamic relocation, actual
runtime loader search, exception unwinding, or C++ object behavior on the
device. The exact on-device loader path and hash were validated; the probe
was **not run**. Before a hardware trial, review loader search paths and
strong undefined symbols/relocations with the same private artifacts.
Any handheld C++ execution requires separate explicit owner permission.
The private official `KNight-Blade – Howling of Kerberos` RPG Maker XP
sample is reserved for a **later engine-level** compatibility test, not
this C++ ABI calibration. No demo assets or restricted third-party library
binaries may be added to the repository.

Related owner evidence: [PR #31 evidence entry 1](https://github.com/almighty-atlas/nextui-mkxp/pull/31#issuecomment-6463223748)
and [PR #31 evidence entry 2](https://github.com/almighty-atlas/nextui-mkxp/pull/31#issuecomment-6463496889).
