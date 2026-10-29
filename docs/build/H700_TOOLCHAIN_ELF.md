# Issue #24: actual AArch64 build, unresolved H700 ABI gate

**A real cross-compile and link succeeded for the unchanged original triangle
from PR #23. The result was never executed or uploaded. It is an SDK ABI
experiment, not an approved H700 executable.** Refs [#24](https://github.com/almighty-atlas/nextui-mkxp/issues/24),
[#22](https://github.com/almighty-atlas/nextui-mkxp/issues/22), [PR #23](https://github.com/almighty-atlas/nextui-mkxp/pull/23).

The important new blocker is concrete: the compiler's glibc sysroot is configured
for **minimum Linux 4.19**, and the linked executable carries GNU Linux ABI note
**4.19.0**. The owner's observed kernel is **4.9.170**. A direct GLIBC_2.17 symbol
requirement alone cannot clear this discrepancy. Do not delete the note or ignore
shared-library errors to manufacture compatibility.

| Gate | Result | Smallest next step |
| --- | --- | --- |
| GREEN | Compiler bytes match published digest; selected SDK bytes hashed and inspected; original C compiles against real SDK headers; complete local SDK link succeeds | Review reproducible scripts and evidence |
| GREEN | AArch64 ELF facts, actual includes/link inputs, link map and repeated same-root build hashes captured | Inspect the committed text/JSON evidence |
| YELLOW | TrimUI SDL 2.26.1/API inputs and PowerVR link libraries differ from installed H700 SDL 2.28.5/Mali assumptions | Resolve an auditable H700-compatible link interface and installed runtime identity |
| RED | Toolchain minimum kernel 4.19 versus observed 4.9.170; libc/loader versions/hashes not confirmed | Select/rebuild a reviewed test sysroot with a compatible kernel baseline; reassess exact ELF requirements |
| RED | Linked-work distribution rights/source obligations unresolved | Human review under PR #19; no target artifact publication |
| RED | EGL/ION/presentation/return not tested | No device action now; later independent review and #22 owner test remain necessary |

## Independent branch and scope

Base main: `bcb666b` (full revision in [lockfile](h700-inputs.lock.json)). PRs
#19/#20/#21/#23 remain open/unmerged and untouched. No shared document or source
from those PRs is edited or copied here. A detached checkout of PR #23 head
`60721c1a81a9f54e507650f313a479ecaa9b6d2a` was used only under the temporary research
workspace; its original `triangle.c` SHA-256 is
`8a08fe77d8675eb93368c15bd5fd3ddc1b00d9dd9229b8eda595e0a0e1432c42`.
No issues #4/#5/#6/#7 engine work, games, device access, graphical execution,
container execution, system package installation or global changes occurred.

Files delivered:

- [Input lock](h700-inputs.lock.json), [actual build/ELF evidence](h700-build-evidence.json)
  and [sanitized full link map](h700-triangle.link-map.txt).
- [Archive/ELF gate](../../scripts/h700_build_gate.py): digest-before-parse, safe
  selective extraction, readelf-only scan and fail-closed policy checks.
- [Reproduction driver](../../scripts/h700_triangle_crosscheck.py): isolated,
  local-input cross-build; never executes or publishes the target.
- [Offline tests](../../scripts/tests/test_h700_build_gate.py) and a dedicated
  [workflow](../../.github/workflows/h700-abi.yml); CI downloads no SDK and builds
  no graphical executable.

## Download and extraction evidence

| Input | Actual independently verified bytes / SHA-256 |
| --- | --- |
| Compiler x86_64-host archive | 231900984 bytes; `d4ac4ef1968668f93f625f2b226c69d74739ae58ff640d2ce3aaae6b4d1b93d3` |
| TrimUI SDK_usr_tg5040_a133p.tgz | 185049621 bytes; `b6b615d03204e9d9bb1a91c31de0c3402434f6b8fc780743fa88a5f1da6f3c79` |

Exact release URLs and actual retrieval UTC timestamps are in the lockfile.
Compiler release metadata/checksum matches the independently hashed bytes. The
SDK release metadata has **no published digest**: its hash is this audit's
observation, not upstream attestation or proof of license/build provenance.
The SDK is offered as a development package; there is no established aggregate
redistribution license in the inspected repository/release. No SDK/runtime bytes
are committed or distributed here.

The compiler archive has 4323 non-root members and 113 links; validation preceded
extraction to a fresh workspace, with no /opt installation. The full SDK archive
contains three absolute build-machine symlinks under `usr/bin`. Full validation
refused the first (`usr/bin/gpg-error-config`) before extraction. Their target
usernames/paths are omitted as irrelevant; no link was followed. Instead, an
explicit allowlist extracted **103** relevant SDL2/EGL/GLES2/KHR header/library
members, excluding all SDK utilities, unrelated data and external links. The
allowlist and archive digest are locked. This is selective extraction, not a
silent rewrite of the vendor archive.

The helper rejects traversal/absolute member names, unsafe links, non-directory
ancestors, hardlinks to nonregular/missing targets, duplicates and special files;
preflights before writes, creates regular files first and links last, strips
privileged/group/world-write modes, and requires a new destination. Limits are
200000 members / 4 GiB declared regular data. It does not call extractall, preserve
owners or execute archive contents. An explicitly selected subtree excludes
unrelated links; unsafe selected links still fail. Use only a private workspace
without concurrent modification by another process. Failure may leave partial
files in that new workspace after an I/O error; do not resume into it.

## Compiler, headers, sysroot and first failed stage

Pinned [H700 recipe](https://github.com/LoveRetro/h700-toolchain/blob/04faa348c112617fc6b99be62308099ee6d43581/Dockerfile)
is research context, not an attested H700 rootfs. No floating container image was
used. The compiler release traces to source commit
`d37268f5160ec6cd4da541524c8111797e060c36`:

```text
aarch64-nextui-linux-gnu-gcc (crosstool-NG 1.25.0) 8.3.0
-dumpmachine: aarch64-nextui-linux-gnu
```

Its bundled libc headers report **glibc 2.28**. The
[pinned x86_64-aarch64.config](https://github.com/LoveRetro/gcc-arm-8.3-aarch64-tg5040/blob/d37268f5160ec6cd4da541524c8111797e060c36/x86_64-aarch64.config#L359-L395)
sets `CT_GLIBC_MIN_KERNEL="4.19"`; readelf also finds Linux ABI 4.19.0 in its libc.
The compiler recipe's documentation/version claims must not replace these facts.
A canonical digest over 2265 sysroot file/link records is in the lockfile. This
experiment uses that compiler-bundled libc plus **only the selected SDK graphics
inputs**, not a full TrimUI /usr overlay or host headers. It does not adopt the
H700 Dockerfile's unverified claim about the owner's installed glibc version.

The SDK genuinely contains SDL2, GLES2, EGL and Khronos headers; selected SDL
headers identify **2.26.1** and define `SDL_VIDEO_DRIVER_MALI`. This does not
identify the installed patched H700 2.28.5 backend, build flags or symbols.
The SDK header notices name SDL's Zlib-style terms and Khronos permissive terms;
they are not a license for every vendor binary in the SDK.

**Actual first build:** C compilation completed with exit 0 and no mock headers.
The first link exited 1: `libIMGegl.so`, `libsrv_um.so`, `libusc.so` and
`libglslcompiler.so`, required by the SDK PowerVR libraries, were absent from the
initial extraction. Representative unresolved symbols included
`PVRSRVSyncPrimGetFirmwareAddr` and `IMGeglGetDisplay`. The precise fix was to
extract exactly these four existing SDK members and provide their directory via
**link-time-only** `-rpath-link`. The next link exited 0, without permissive
unresolved-symbol flags, driver loading, installation or runtime replacement.
These PowerVR files are private local link inputs, not H700 driver candidates.

Compile flags: `--sysroot=<compiler libc> -std=c99 -O2 -Wall -Wextra -Werror`,
selected SDK include directory, `-v -H`, compile-only `-c` first. Link: the target
object, selected SDK `-L`, matching `-Wl,-rpath-link`, `-Wl,-t`, link map, and
`-lSDL2 -lGLESv2 -lEGL`. Full literal argument lists with normalized workspace
prefixes and exit codes are in the evidence JSON. GCC defaults include Cortex-A53,
little-endian LP64; no CPU-specific claim about device behavior follows.
The driver removes host include/compiler search overrides, uses a private TMPDIR,
and rejects traced include/link inputs outside the isolated output workspace.
No foreign `ldd`, emulator or target program was run.

## Actual ELF evidence (not a device approval)

Primary scripted build: **24744 bytes**, SHA-256
`507c5800d1e98055117f56d1f04b4564fcd9f51be3aa358755c6f8c63745b37e`.

| Field | Host readelf/file observation |
| --- | --- |
| Class / endian / machine / type | ELF64 / little / AArch64 (183) / ET_EXEC (2) |
| PT_INTERP | `/lib/ld-linux-aarch64.so.1` |
| DT_NEEDED | `libSDL2-2.0.so.0`, `libGLESv2.so.2`, `libEGL.so.1`, `libc.so.6` |
| RPATH / RUNPATH | None in this executable |
| Direct required symbol versions | `GLIBC_2.17`; no GLIBCXX/CXXABI requirement observed |
| GNU Linux ABI note | **4.19.0**; above observed device kernel 4.9.170 |
| Source/object identity | Original source hash locked; object `b6c55e65b5dba4742f16a6ee576a65bdf58520b20b268b73fb54053743ba7f62` |
| Repeat result | Two full compile+link runs in the same extraction root produced identical objects and ELFs |

Cross-root limitation: the initial manual ELF hash was
`a1f6ccd476089ee96272304670b1eede8ed73985325f448312bb11847f4d0c42`.
The object bytes match the scripted build, but unstripped CRT file-symbol strings
contain absolute extraction paths, so raw ELF hashes differ across extraction
roots. No cross-root bit-for-bit reproducibility claim is made. The map and JSON
normalize only research paths (`<RESEARCH>`) and trailing map whitespace for
review; the raw map hash is recorded separately. No ELF, object, SDK, archive or
.so is attached to this PR or workflow.

The executable's requirements are **not** the whole runtime closure. SDK SDL has
additional libc/math/dl/pthread/libgcc dependencies; SDK GLES/EGL pull PowerVR
components and contain vendor build RPATHs (redacted usernames in JSON). Those
are a reason to keep SDK binaries off H700, not to copy them to satisfy a link.
The installed Mali backend additionally loads/uses EGL/GLES vendor interfaces,
ION/pixmap and framebuffer resources; SDL audio/backends can add dlopen inputs
beyond NEEDED, though this app requests only video/timer. A direct EGL dependency
must resolve consistently with SDL's EGL instance. Exact H700 versions, hashes,
loader resolution, backend symbols and driver closure remain UNKNOWN.

The GNU ABI note/configuration mismatch is a **static rejection/retargeting gate**,
not a claim that a specific syscall or loader failure was observed. Installed
H700 libc can differ from the compiler's libc; neither executing this artifact
nor transplanting the compiler/SDK libc is an approved way to resolve it.

## Reproduce privately; no target execution

After reviewing scripts and rights, download the **two exact lockfile URLs** as
ordinary files into a private temporary directory. Retain proxy/CA settings;
verify the compiler's published digest and this audit's recorded SDK digest
before parsing. Downloading bytes does not authorize redistribution. No container,
sudo or system package installation is required. Create a detached checkout of
PR #23's **full pinned commit** outside the current issue branch, then run:

```sh
python3 scripts/h700_triangle_crosscheck.py \
  --compiler-archive "$INPUTS/gcc-8.3.0-aarch64-nextui-linux-gnu-x86_64-host.tar.xz" \
  --sdk-archive "$INPUTS/SDK_usr_tg5040_a133p.tgz" \
  --source-checkout "$PR23_CHECKOUT" --output "$NEW_PRIVATE_BUILD_DIR" \
  --lock docs/build/h700-inputs.lock.json --policy docs/build/h700-target-policy.json
```

The output directory must not exist. The driver verifies original source/commit
and input digests, preflights and selectively extracts, records compiler identity,
performs two compile/link runs, writes local logs/maps/results, and uses native
readelf. It does **not** execute the target. **Exit 2 is expected even after a
successful build:** the H700 policy is deliberately incomplete and the kernel
note mismatches. Check `build_status`, per-stage exit codes and `elf_gate` rather
than interpreting this as compiler failure. The reproducible driver uses the
already identified complete link subset; the exploratory missing-library failure
is recorded separately, not repeated artificially.

Standalone inspection (also expected exit 2 with the current policy):

```sh
python3 scripts/h700_build_gate.py elf "$NEW_PRIVATE_BUILD_DIR/triangle-1" \
  --policy docs/build/h700-target-policy.json
```

The scanner checks ELF header/notes, interpreter, NEEDED, RPATH and version needs;
GLIBC definitions are not confused with requirements. Unknown target policy,
foreign ABI, unreviewed dependencies/paths/versions or excess GNU kernel/glibc
requirements fail closed. `STATIC_POLICY_MATCH_ONLY` for a complete synthetic
policy still does not certify driver closure, rights or hardware functionality.

## Narrow distribution/source-notice decision

**Distribution remains STOP/BLOCKED** under [PR #19's gate](https://github.com/almighty-atlas/nextui-mkxp/blob/9d482dc981401166b40155678ad00e29daad9163/docs/DISTRIBUTION_GATE.md).
This task does not select a combined-work license or claim legal clearance.

| Material in a future distribution | Required review/delivery |
| --- | --- |
| Original PR #23 C/shaders/launcher | Retain the scoped MIT copyright/license; include exact source, flags and patch history. MIT is GPL-compatible but does not clear linked libraries |
| Installed H700 SDL fork | Map actual library bytes to source/patch/config and notices. Root SDL Zlib terms and SDK headers do not resolve the fork's [GPL-noticed mali.h](https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/mali.h#L1-L14). Human review must decide applicable file/combined-work terms and GPL version |
| Possible GPL combined work | If applicable, distribute under compatible GPL terms, retain notices/change dates and deliver complete corresponding source/build/install scripts, including the app and required non-system linked components. Dynamic linking to an existing installation is not an automatic exemption |
| EGL/GLES vendor implementations | Do not ship SDK PowerVR or H700 GPU blobs. Review whether any GPL system-library exception/link permission applies to the actual arrangement. Do not assume that omitting vendor binaries alone resolves combination rights |
| libc/startup/runtime objects | Link map includes crt objects and libc_nonshared material; review relevant glibc LGPL/notices and source/relink requirements even though libc is dynamically NEEDED. Distinguish searched libgcc archives from selected code; examine GCC Runtime Library Exception eligibility for any included runtime material |
| SDK/compiler packages | Tool use and private analysis are distinct from redistribution. Compiler archive contains component licenses (including GCC COPYING.RUNTIME and glibc COPYING.LIB/LICENSES); SDK aggregate/vendor terms and complete corresponding build sources remain unresolved |

Necessary human decisions: actual SDL source/license mapping, proprietary-system
library/link-exception analysis, combined license election/source-delivery plan,
startup/runtime obligations and final artifact approval. Include full applicable
license texts/NOTICE/copyrights and source availability with the exact artifact.
No GPL exception or proprietary redistribution permission is invented here.

## One consolidated future metadata handoff — NOT authorized now

Current owner action is **source-code review only**. No additional device command
is requested by this PR. First address the already demonstrated kernel/sysroot
mismatch using build inputs, without changing the handheld.

If a separately reviewed inventory is later approved, collect the following once
through the existing SSH/file workflow; do not enable SSH/services or run graphics:

1. Record only `/dev/ion` character-device status and current read/write access
   using shell metadata tests (`-c`, `-r`, `-w`), **never opening the node**.
2. For each approved fixed regular file below, record canonical system path,
   size, SHA-256 and ELF class/machine. Missing utility/file/access is UNKNOWN;
   do not install a utility or scan arbitrary paths:

   - `/mnt/SDCARD/.system/h700/lib/libSDL2-2.0.so.0.2800.5`
   - `/lib/libEGL.so.1`
   - `/lib/libGLESv2.so.2`
   - `/lib/aarch64-linux-gnu/libc.so.6`
   - `/lib/ld-linux-aarch64.so.1`

3. In the same approved batch, privately transfer only those reviewed library
   copies to a trusted host if on-device ELF tools are absent. Resolve symlinks
   within known system/runtime directories; unexpected destinations remain
   UNKNOWN. Hash again on the host, then inspect **without execution** using
   `file` and `readelf --wide -h -l -d --version-info --notes`. Record symbol
   definitions/requirements separately, SONAME/NEEDED/RPATH and GNU ABI notes;
   map permitted source/build versions to the hashes. Do not run foreign ldd.
4. Share a sanitized metadata table/report, not library bytes, absolute private
   paths, env dumps, Wi-Fi/IP/MAC identifiers, passwords, games or general logs.
   Resolve any discovered dependency outside this fixed list through a later
   review, not automatic recursive transfer or a guessed policy allowlist.

This batch can identify the remaining ABI facts but cannot establish visual
rendering, ION operation or clean return. Any eventual graphical test still goes
through the separately reviewed NextUI Tools plan in #22; never launch the app
from SSH while NextUI is running.

## Verification and evidence levels

Executed: release metadata reads, pinned downloads with independent streaming
SHA-256, archive inventory/preflight, safe private extraction, GCC identity,
original-source real compile/link, include traces/link maps, file/readelf/notes,
repeat builds and source-only tests. Full build argument arrays and first failure
are in the JSON; no target execution, binary upload, merge or device action occurred.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts/tests -v
git diff --check
```

**12 tests PASS locally:** hashes/pins, traversal/absolute/external link/device/
duplicate/ancestor rejection, explicit safe subset, extraction modes, correct
failure handling before compiler execution, ELF parser fixture and real host-ELF
rejection, unknown/malformed policy, NEEDED/RPATH/GLIBC/C++ and kernel-note gates.
CI runs only these offline/static tests, never downloads or builds against SDKs.

| Evidence class | Result |
| --- | --- |
| SOURCE_CONFIRMED | Pinned recipe/source settings, API notices and minimum-kernel configuration |
| HOST_VERIFIED | Download hashes, actual target compile/link, ELF facts, same-root repeat and offline tests |
| OWNER_OBSERVED_H700 | Existing #1 inventory only: AArch64 shell, kernel 4.9.170, selected files present |
| H700_RUNTIME_NOT_TESTED | EGL/ION/SDL startup, renderer/presentation/rotation, return, audio/input and games |
| BLOCKED | Kernel/sysroot mismatch, actual installed ABI/driver identity and rights/source-delivery approval |

Smallest next action: review this PR's source/evidence, then resolve the **test
sysroot's minimum-kernel configuration** and vendor-neutral/approved graphics
link inputs. The future single metadata batch can then close installed ABI facts
before any candidate package or hardware test. No changes to existing PRs or
full engine environment are required by this delivery.
