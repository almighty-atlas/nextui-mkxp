# Issue 26: Linux 4.9 libc retarget and independent H700 link gate

2026-10-26. Refs [#26](https://github.com/almighty-atlas/nextui-mkxp/issues/26).
**Blocked host experiment; no usable H700 executable.** A real isolated glibc
build produced AArch64 startup objects and a preliminary libc with Linux 4.9.0
notes. The complete build did not finish. No original-triangle object or link,
target execution, installation, device access or binary publication occurred.

The first reproduced build blocker is GNU Make 4.4.1 repeatedly restarting in
glibc 2.28 `stdio-common/others`: **103 restarts in a bounded 3-second run**.
The initial full build was terminated after **281.33 seconds**, exit `-15`.
Separately, authentic, provenance-reviewed H700 Mali EGL/GLES link inputs are
unavailable in this workspace. **LINK_BLOCKED**, independent of libc progress.

## Scope, prerequisites and evidence

Read main's AGENTS, README, ROADMAP, ARCHITECTURE, TEST_PLAN, SOURCES and workflow;
issues #1–#4/#18/#22/#24/#26; PRs #19/#20/#21/#23/#25 and #25's review and
follow-up comments. Fresh branch from current main
`201dd309a6fd311f3e53acba330bc9d58a364f4f`; those branches remain unchanged.
The original #23 source at `60721c1a81a9f54e507650f313a479ecaa9b6d2a`
was independently read and hashed to
`8a08fe77d8675eb93368c15bd5fd3ddc1b00d9dd9229b8eda595e0a0e1432c42`.
Its source-only launcher was read, never installed or invoked.

Inputs and per-file fingerprints: [issue-26-inputs.json](issue-26-inputs.json).
Actual commands, timings, tool hashes, metadata and private-log fingerprints:
[issue-26-evidence.json](issue-26-evidence.json). `<PRIVATE>` substitutes the
ephemeral research directory; no ELF/archive/library bytes are tracked.

The environment-status connector and `/etc/codex/network-policy.json` were
unavailable. Network reads used the supported approved executor; no proxy,
credential, CA, network-policy or system configuration was changed. No Docker
image, SDK overlay, host package installation or privileged build was used.

## Root cause and candidate order

At [GCC configuration pin d37268f](https://github.com/LoveRetro/gcc-arm-8.3-aarch64-tg5040/tree/d37268f5160ec6cd4da541524c8111797e060c36),
both host variants select Linux headers 4.19, glibc 2.28,
`CT_GLIBC_KERNEL_VERSION_AS_HEADERS=y` and `CT_GLIBC_MIN_KERNEL="4.19"`.
The freshly downloaded compiler archive independently matches
`d4ac4ef1968668f93f625f2b226c69d74739ae58ff640d2ce3aaae6b4d1b93d3`
(231900984 bytes). Native `readelf -n` on its actual `crt1.o` reports 4.19.0.
Switching compiler host architecture would retain the target assumption.

[crosstool-NG 1.25.0](https://github.com/crosstool-ng/crosstool-ng/blob/8fa98eeeff9bc53478d97ef722f366fea151ae64/scripts/build/libc/glibc.sh)
translates the selected header version into `--enable-kernel`. The annotated
tag resolves to commit `8fa98eeeff9bc53478d97ef722f366fea151ae64` (the tag
object itself is not the source commit). Its specific-kernel choice also permits
an explicit minimum; changing only a generated config/ELF note is insufficient.

[glibc 2.28 AArch64 configure](https://github.com/bminor/glibc/blob/3c03baca37fdcb52c3881e653ca392bba7a99c2b/sysdeps/unix/sysv/linux/aarch64/configure.ac)
sets an architectural minimum of 3.7.0. Generic Linux configure checks the
headers against the requested minimum and generates `__LINUX_KERNEL_VERSION`
and `__ABI_TAG_VERSION`; `csu/abi-note.S` emits the note, and `csu/Makefile`
combines it with startup objects. Thus 4.9.0 is source-supported here; a real
rebuild must also change compiled syscall assumptions, not just the note.
For example `kernel-features.h` assumes statx only from 4.11; the 4.9 build
retains its ENOSYS fallback in `statx.c`. This example is not an exhaustive
syscall or vendor-kernel audit. Installed H700 libc and driver symbols remain
unknown; a low note or low direct GLIBC requirement cannot establish that closure.

Candidates were evaluated in the requested order:

1. **Attempted:** pristine upstream glibc 2.28 commit
   `3c03baca37fdcb52c3881e653ca392bba7a99c2b`, Linux 4.9 UAPI headers and the
   verified GCC 8.3 compiler. Same libc version, explicit new startup/library
   build; no unrelated CRT substitution or symbol suppression. This is a direct
   glibc experiment, not a completed crosstool-NG rebuild. Its three glibc-2.28
   patches were inventoried: caddr typedef guard, x86 CET, GCC-10 long double;
   none was applied to this pristine GCC-8/AArch64 experiment.
2. **Not selected:** no second prebuilt toolchain was substituted after the
   reproducible blocker. Host-architecture variants retain 4.19, and the
   TrimUI PowerVR SDK does not establish the target graphics ABI.
3. **Current outcome:** incomplete sysroot, precisely reproduced host-tool
   blocker. Stop before speculative source patches or an engine build.

The cloned GCC-config, H700-toolchain and SDL default heads matched #25's pins
on inspection. crosstool-NG's observed default head was
`deacc28df92242014699eac9220e1d18fac3eeb6`; only the resolved 1.25.0 commit
above was inspected for the baseline. No moving head is a build input.

## Real private build and bounded failure reproduction

The kernel archive is **93192404 bytes**, SHA-256
`029098dcffab74875e086ae970e3828456838da6e0ba22ce3f64ef764f3d7f1a`.
This independent hash matches kernel.org's `v4.x/sha256sums.asc`; its PGP
signature was not verified. Both archives were hashed before parsing, then
preflighted/extracted privately using #25's pinned `h700_build_gate.py` pattern.
No SDK was downloaded. The compiler preflight selected 4323 members, Linux
60064; special files, traversal and escaping archive links were rejected by
that existing helper. No archive input was piped to execution or installed.

With `W` a private directory, sources and compiler laid out as in the evidence,
the actual stage commands were:

```sh
# All subprocesses receive the minimal environment described below.
# cwd: $W/kernel/linux-4.9
$W/host-bin/make ARCH=arm64 INSTALL_HDR_PATH=$W/headers headers_install
# cwd: $W/glibc-build (separate from the source tree)
$W/glibc/configure --build=x86_64-pc-linux-gnu \
  --host=aarch64-nextui-linux-gnu --prefix=/usr --enable-kernel=4.9.0 \
  --with-headers=$W/headers/include --disable-werror --disable-selinux \
  --disable-nscd CC=$W/compiler/x86_64-aarch64-nextui-linux-gnu/bin/aarch64-nextui-linux-gnu-gcc \
  CXX=$W/compiler/x86_64-aarch64-nextui-linux-gnu/bin/aarch64-nextui-linux-gnu-g++
$W/host-bin/make -j4
```

Header installation passed in 2.43 s; `LINUX_VERSION_CODE=264448` (4.9.0).
Initial configure failed because the explicit tool allowlist omitted `ls`;
adding the canonical, fingerprinted host `ls` resolved that setup error.
Configure then passed in 0.82 s. `config.h` contains
`__LINUX_KERNEL_VERSION=(4*65536+9*256+0)` and `__ABI_TAG_VERSION=4,9,0`.
Source remained unmodified; no CRT bytes or ABI notes were edited.

The build reached `stdio-common/others`, then stopped advancing its log.
The child was measured at 98.8% CPU. Only the three identified own make
processes were terminated. A separate diagnostic invocation, from `$W/glibc`,
was limited to three seconds and its own process group terminated:

```sh
$W/host-bin/make --debug=m objdir=$W/glibc-build \
  subdir=stdio-common -C stdio-common ..=../ others
```

It restarted 103 times and exited `-15` on the deliberate timeout. This is
direct host evidence for the restart loop. The
[upstream libc-help report](https://sourceware.org/pipermail/libc-help/2023-September/006488.html)
describes the matching older-glibc/Make-4.4.1 failure and suggests an older
Make or newer glibc. That explains the likely compatibility cause; the local
test does not independently prove a particular upstream fix.

Smallest next **non-device** experiment: review and pin a private GNU Make
4.3 build and its sources/checksum, replace only this build-tool input, then
repeat a fresh glibc build. It was not performed here. Do not skip failed
targets, install a partial sysroot, change glibc/kernel versions silently or
use the preliminary libc as a distribution candidate.

| Private material | Native readelf observation | Meaning |
| --- | --- | --- |
| Original compiler crt1.o | ELF64 LE AArch64 relocatable; ABI 4.19.0 | Independently confirms baseline |
| Newly built crt1.o | ELF64 LE AArch64 relocatable; ABI 4.9.0 | Partial HOST build only |
| Preliminary libc.so | ELF64 LE AArch64 shared object; ABI 4.9.0 | Full make/install/check not completed |
| Compiler libgcc_s.so.1 | Requires GLIBC_2.17, no GNU kernel note | Not rebuilt; compiler-runtime consistency remains unaudited |

Exact hashes, sizes, interpreter/NEEDED/version facts for those files are in
the evidence JSON. No original-triangle link map, PT_INTERP, required-symbol
floor or repeat-build hashes exist for this retargeting attempt. No same-root
or cross-root reproducibility claim; no foreign `ldd`, QEMU or target tests.

## Independent H700 SDL/EGL/GLES link contract

The pinned SDL fork's `include/SDL_version.h` and `configure.ac` really declare
**2.28.5**. Its libtool recipe predicts `libSDL2-2.0.so.0.2800.5` with SONAME
`libSDL2-2.0.so.0`; that is source intent, not inspection of installed bytes.
Every SDL function called by the original triangle was found in this fork's
`src/dynapi/SDL_dynapi_procs.h` (SDL_VERSION is a header macro). This confirms
API declarations, not symbol versions/export presence in an actual H700 DSO.

H700-toolchain `support/build-sdl2.sh` pins the fork, applies the fingerprinted
H700 input patch, enables Mali/GLES/shared SDL and disables KMSDRM/X11/Wayland.
NextUI `workspace/h700/makefile` stages that prebaked SDL; its external image
selection is `latest`, so it does not attest the owner's installed bytes.
The recipe overlays a TrimUI SDK, whose PowerVR implementation was used in
#25; its successful link cannot supply the required H700 Mali evidence.

The triangle needs real SDL2 **and direct EGL/GLES symbols**, including
`eglGetCurrentDisplay`, `eglQueryString`, shader/buffer/draw operations.
The fork has Khronos API headers, but headers do not provide link inputs.
SDL's EGL loader separately loads EGL/GLES libraries and resolves symbols;
its Mali backend also needs framebuffer/ION and vendor pixmap support.
Direct DT_NEEDED, `-rpath-link` closure, SDL's dlopen resolution, and the
vendor driver's additional closure must ultimately agree.

No provenance-approved H700 libEGL/libGLESv2/link sysroot was supplied. The
pinned NextUI source tree metadata contains recipes rather than those H700
runtime libraries. No stock/vendor libraries were copied or repackaged; no
dummy shim, PowerVR substitute, unresolved-symbol suppression, x86_64 link
or stub compile was used to imply success. **LINK_BLOCKED** remains separate
even if a later Make change completes the libc build.

## Environment boundary and offline safeguards

The real stages used a new environment dictionary: PATH points only to a
private `host-bin`; HOME/TMPDIR are private; LC_ALL/LANG=C, TZ=UTC and fixed
SOURCE_DATE_EPOCH. No inherited environment values, proxies, network-fetchers,
LD_PRELOAD/LD_LIBRARY_PATH/LD_AUDIT/LD_DEBUG, PYTHONPATH, compiler/include/library
overrides, PKG_CONFIG_*, CONFIG_SITE, BASH_ENV, ENV or MAKEFLAGS were passed.
Acquisition occurred separately, retaining the executor's networking setup.

The exact observed tool allowlist and canonical executable hashes are in the
evidence. It comprises shell/make, compiler/binutils, awk/bison, text and file
utilities, Perl/Python and the authenticated archive's cross-tool executables.
`egrep`/`fgrep` were explicitly present compatibility scripts, fingerprinted
with the host tools; configure actually selected `grep -E`. The stricter new
`verify_tools` helper rejects script wrappers for scanner tools. It is not
claimed to have retroactively authenticated every tool in the earlier build.

glibc compile commands show `-nostdinc`, pinned GCC internal include paths,
the 4.9 UAPI directory and glibc source/build directories. Logs are retained
privately. No triangle `-H` trace or reviewed full link map was produced.
The added helpers support reviewed search-root and file-digest checks for a
future completed build. This is environment isolation, **not** a filesystem
or network jail; absolute paths, host executables' own dynamic dependencies,
and the unpinned host OS remain reproducibility limits. A trusted parent
interpreter/loader is required: cleaning child environments cannot undo
LD_PRELOAD or PYTHONPATH injection that occurred before Python started.

Offline checks (no downloads, target builds or external artifact uploads):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -I -m unittest discover -s scripts/issue_26_tests -v
git diff --check
```

The workflow has read-only repository permissions and no upload/install steps.
Actual local results: **12 tests PASS**, `git diff --check` PASS, JSON parsing,
local documentation links and Python syntax PASS. GitHub CI was not the host
cross-build environment; any later workflow success only validates offline tests.
Tests cover hostile parent environment and actual clean child, unknown file/tool
digests, wrapper rejection, traversal/symlink ancestors, escaped include/library
roots, missing/multiple/excessive kernel notes, GLIBC floor/named ABI versions,
foreign ELF, interpreter/NEEDED/RPATH mismatches and malformed inputs/policies.
Synthetic PASS means only an experimental policy match. The CLI scanner always
reports H700 as OWNER_NOT_TESTED and distribution as BLOCKED.

## Comparison and rights gates

| Gate | Status | Evidence level |
| --- | --- | --- |
| Original toolchain kernel baseline | KNOWN: 4.19 | SOURCE + HOST crt1.o |
| Retargeted glibc/sysroot | BLOCKED: full make restart loop; partial 4.9 objects | HOST |
| Original AArch64 triangle object | NOT_TESTED after earlier build blocker | HOST |
| Compatible H700 SDL/EGL/GLES link | LINK_BLOCKED: authentic link inputs absent | SOURCE/workspace inventory |
| Original triangle ELF/PT_INTERP/NEEDED/GLIBC/note | BLOCKED: no linked triangle | HOST |
| Installed H700 hashes, /dev/ion, visible video/return | OWNER_NOT_TESTED | No new H700 evidence |
| Distribution/rights | BLOCKED | Existing #19 gate remains |

MIT covers only #23's original source. The SDL fork includes GPL-noticed
`mali.h`; root SDL Zlib licensing does not resolve that file or combined-work
terms. Human review must map actual SDL bytes/patches to notices, select any
applicable GPL version, and resolve exact proprietary EGL/GLES linking rights
or an applicable system-library/explicit linking exception. Omitting vendor
DSOs does not itself provide that exception. glibc startup/nonshared LGPL
material, corresponding source/relinking requirements, and GCC runtime
exception eligibility remain separate. No combined license was elected and
no exception, redistributable SDK, game asset or binary approval is inferred.
See [PR #19's pinned distribution gate](https://github.com/almighty-atlas/nextui-mkxp/blob/9d482dc981401166b40155678ad00e29daad9163/docs/DISTRIBUTION_GATE.md).

No runtime behavior or supported-game claim changed. This standalone limitation
report avoids overlapping #19–#25's shared COMPATIBILITY edits; integration
there remains deferred until those PRs are resolved. No owner device command
is requested. #22/#24/#26 remain open, this PR stays unmerged.
