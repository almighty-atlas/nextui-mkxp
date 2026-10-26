# Issue #26 — Linux 4.9 libc and independent H700 Mali gate

Refs [#26](https://github.com/almighty-atlas/nextui-mkxp/issues/26).
Private host build, 2026-10-26. Evidence levels: **SOURCE**, **HOST**, **H700**.
This is also the issue-specific limitations addendum to `docs/COMPATIBILITY.md`;
shared files and unmerged PRs #19–#25 are deliberately untouched.

## Result

A complete glibc 2.28 was rebuilt with Linux 4.9.170 headers and
`--enable-kernel=4.9.0`, using the pinned GCC 8.3 compiler from PR #25.
The rebuilt `crt1.o` and libc encode Linux **4.9.0**, without editing ELF notes
or transplanting startup objects. A small libc calibration program links
against that matched libc/startup/loader set. It is **not the triangle**.
The original PR #23 triangle is separately compiled to an AArch64 object.
The real H700 graphics link remains **LINK_BLOCKED**: authentic matching
SDL2/EGL/GLES link libraries were not supplied. No substitute library was made.

| Gate | Result | Evidence / boundary |
| --- | --- | --- |
| TOOLCHAIN kernel baseline | **KNOWN** | SOURCE + HOST: original compiler sysroot 4.19; both host configs agree |
| RETARGETED glibc/sysroot | **BUILT** | HOST: full make + staged install, glibc 2.28 / Linux headers 4.9.170 / minimum 4.9.0 |
| AArch64 original triangle object | **PASS** | HOST: unchanged pinned source + real SDL/Khronos headers; ET_REL, machine 183 |
| AArch64 H700 SDL/EGL/GLES link | **LINK_BLOCKED** | HOST: genuine link attempt fails; no H700 library input bundle |
| Libc calibration ELF/PT_INTERP/NEEDED/GLIBC/note | **PASS_STATIC** | HOST: AArch64 ET_EXEC, `/lib/ld-linux-aarch64.so.1`, libc.so.6, GLIBC_2.17, Linux 4.9.0, no RPATH |
| Triangle final ELF / full graphics closure | **BLOCKED** | No linked triangle exists; calibration facts must not be attributed to it |
| Installed H700 hashes, ION, actual video | **OWNER_NOT_TESTED** | H700: none; filename/version reports do not attest installed bytes |
| Distribution/rights | **BLOCKED** | PR #19 gate remains in force |

Only text, original build scripts and offline tests are published. Every ELF,
archive, copied header and system library stays in private scratch space.
Nothing was installed, executed or modified on the handheld. No target ELF,
target `ldd`, target test suite, emulator, or target `ldconfig` was run.

## Mali-link follow-up from d678597

The follow-up continues this same PR after fetching and fast-forwarding to
`d678597ab6c9522594c1669a1f4eb3196fd63911`. The complete earlier libc build,
calibration ELF and original-object evidence above are preserved. They were
not reclassified as failures because their private build directory is absent
on this host. The pinned SDL tree and all five Khronos headers were independently
rehashed; the original triangle hash still matches the lock.

| Requested gate | Current follow-up result | Evidence |
| --- | --- | --- |
| LIBC49_BUILT | Preserved | Prior HOST build at d678597; not installed-device attestation |
| SDL_SOURCE_BUILT / SDL_BUILD_BLOCKED | **SDL_BUILD_BLOCKED** locally | Complete prior sysroot unavailable here; dependency preparation failed in native M4 before SDL configure/make |
| EGL_GLES_LINK_INPUTS_VERIFIED / LINK_BLOCKED | **LINK_BLOCKED** | No approved development implementation found in inspected NextUI/toolchain/BaseOS sources and manifests |
| TRIANGLE_HOST_LINKED / NOT_LINKED | **NOT_LINKED** | No new target link attempted without eligible inputs |
| ELF_POLICY_HOST_ONLY | Retained | Previous libc/object metadata and offline gates; no new SDL/graphics ELF exists |
| H700_RUNTIME_NOT_TESTED | Unchanged | No device operation |
| LICENSE_DISTRIBUTION_BLOCKED | Unchanged | No new permission for Mali/vendor/combined-work distribution |

### Exact source symbol contract

The evidence JSON's `mali_followup.source_symbol_matrix` records each symbol,
its original C call lines and declaration lines. These are source declarations,
not installed DSO exports or a freshly measured object undefined-symbol table.
The source is [unchanged PR #23 triangle.c](https://github.com/almighty-atlas/nextui-mkxp/blob/60721c1a81a9f54e507650f313a479ecaa9b6d2a/spikes/h700-video/triangle.c).

| Provider / phase | Exact source calls | Required evidence still missing |
| --- | --- | --- |
| SDL2, direct link: init/events/metadata | `SDL_Init`, `SDL_Quit`, `SDL_getenv`, `SDL_GetVersion`, `SDL_GetCurrentVideoDriver`, `SDL_GetTicks`, `SDL_Delay`, `SDL_PollEvent`, `SDL_GetError`, `SDL_ClearError` | Matching AArch64 SDL DSO, actual SONAME, these exports and version/dependency requirements |
| SDL2, direct link: window/context/swap | `SDL_CreateWindow`, `SDL_DestroyWindow`, `SDL_GL_SetAttribute`, `SDL_GL_CreateContext`, `SDL_GL_DeleteContext`, `SDL_GL_MakeCurrent`, `SDL_GL_GetDrawableSize`, `SDL_GL_SetSwapInterval`, `SDL_GL_SwapWindow` | Same SDL input; a swap call is through SDL, not a direct original-triangle `eglSwapBuffers` reference |
| EGL, direct link (2) | `eglGetCurrentDisplay`, `eglQueryString` | Authentic EGL development DSO/import interface, source/build/rights identity, exports/SONAME/closure |
| GLES2, direct link: shader/program | `glCreateShader`, `glShaderSource`, `glCompileShader`, `glGetShaderiv`, `glDeleteShader`, `glCreateProgram`, `glAttachShader`, `glBindAttribLocation`, `glLinkProgram`, `glGetProgramiv`, `glGetUniformLocation`, `glUseProgram`, `glDeleteProgram` | Authentic GLES2 development interface with all these exports |
| GLES2, direct link: buffers/draw/identity | `glGenBuffers`, `glBindBuffer`, `glBufferData`, `glDeleteBuffers`, `glVertexAttribPointer`, `glEnableVertexAttribArray`, `glUniform1f`, `glViewport`, `glClearColor`, `glClear`, `glDrawArrays`, `glGetError`, `glGetString` | Same GLES2 input; these 13 plus the 13 shader/program calls total 26 |
| C/POSIX source calls | `memset`, `printf`, `setvbuf`, `strcmp`, `strncmp`, `sigemptyset`, `sigaction` | Rebuilt libc/startup gate already established; a future real link must inspect compiler-selected symbols and support objects again |
| Header macro | `SDL_VERSION` | No ELF symbol; do not request a fabricated export |

All 19 SDL functions occur in the pinned fork's
[dynapi declarations](https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/dynapi/SDL_dynapi_procs.h).
The direct EGL/GLES functions are declared in the exact Khronos headers already
locked in `issue-26-inputs.json`, not definitions of a Mali implementation.
The SDL 2.28.5 libtool source convention predicts `libSDL2-2.0.so.0`; the
BaseOS harvest lists filenames `libEGL.so.1`, `libGLESv2.so.2` and
`libmali.so.0`. Actual SONAMEs and the resulting application's DT_NEEDED remain
UNKNOWN until authentic bytes are inspected. EGL/GLES may resolve through
vendor shims/aliases; no monolithic-vs-shim layout is assumed from the names.

There is a second, runtime-only contract beyond these direct calls:

- [Mali window creation](https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_malivideo.c#L452-L464)
  resolves `egl_create_pixmap_ID_mapping` and `egl_destroy_pixmap_ID_mapping`.
  Public EGL/GLES2 symbols alone do not establish that vendor pixmap ABI.
- [The blitter loader](https://github.com/JohnnyonFlame/SDL-malifbdev-rot/blob/d4a7d7503524cc469fe775242f3f925d4dd56c88/src/video/mali-fbdev/SDL_maliblitter.c#L404-L430)
  loads `libEGL.so` and `libGLESv2.so`, then resolves both function tables through
  `eglGetProcAddress` and its EGL-object symbol fallback. The tables additionally
  require image/fence/pixmap functions (`eglCreateImageKHR`, `eglCreateSyncKHR`,
  `eglClientWaitSyncKHR`, `eglCreatePixmapSurface`) and GLES extensions such as
  `glEGLImageTargetTexture2DOES` and `glGenVertexArraysOES`. These are distinct
  from the original triangle's 26 direct GLES2 calls.
- The backend opens `/dev/fb0` and `/dev/ion` and uses the bundled `mali_pixmap`,
  `fbdev_window_s` and ION ioctl definitions. No proprietary header requirement
  was identified in this source inspection. Layout compatibility, kernel access,
  vendor extension support and successful context/presentation remain untested.
  The H700 source patch changes input behavior; it was reviewed and fingerprinted
  but not applied in this follow-up because the build dependency failed earlier.

### Published BaseOS input investigation and stop

The newly inspected BaseOS v1.4.0 annotated tag resolves to source commit
[`5866358eb4ad7cf1e6c0b09228e6cfa11f2cf3d5`](https://github.com/pvaibhav/BaseOS/tree/5866358eb4ad7cf1e6c0b09228e6cfa11f2cf3d5).
Only recipe/manifest text and Git tree metadata were fetched. Its
[harvest allowlist](https://github.com/pvaibhav/BaseOS/blob/5866358eb4ad7cf1e6c0b09228e6cfa11f2cf3d5/manifest/harvest.list#L1-L29)
explicitly calls the GPU set stock Mali plus GLES/EGL shims, with symlink paths
dereferenced during harvesting. It does not build that vendor implementation.
The [RG35XX Pro manifest](https://github.com/pvaibhav/BaseOS/blob/5866358eb4ad7cf1e6c0b09228e6cfa11f2cf3d5/manifest/prepared/rg35xxpro.json)
declares `stockmod-image` provenance and
`RG35XXPRO-V1.0.5-BASE-20260522-mod-v3.9.9.img`. Its aggregate harvest hash
identifies a runtime collection, not per-library symbols, source identity or a
vendor development/linking grant. Those manifests do not attest this owner's
installed bytes. No prepared bundle, disk image or stock/vendor DSO was fetched.

The pinned H700 toolchain still
[overlays the TrimUI SDK](https://github.com/LoveRetro/h700-toolchain/blob/04faa348c112617fc6b99be62308099ee6d43581/Dockerfile#L45-L51).
Neither that recipe nor the inspected BaseOS manifests provide the missing
rights-reviewed H700 development interface. Public release availability does
not establish permission to use harvested vendor DSOs as development inputs.

| Missing specific input | Source/SONAME identity | Why the route stops |
| --- | --- | --- |
| Patched H700 SDL2 shared library | Source fork and patch pinned; source SONAME convention above; actual DSO absent | Cannot inspect actual exports/NEEDED/GLIBC; local source build prerequisite failed |
| EGL development interface | 2 direct symbols above plus SDL loader/vendor/extension requirements; actual shim/vendor source and SONAME UNKNOWN | No reviewed development grant, implementation identity or matching link input in inspected sources |
| GLES2 development interface | 26 direct symbols above plus blitter extension table; actual source/SONAME UNKNOWN | Khronos headers give declarations only; no matching approved library |
| Driver and load closure | Harvest filename `libmali.so.0`; version/build/source/NEEDED UNKNOWN | Aggregate stock harvest is neither corresponding source nor library-specific clearance |

**LINK_BLOCKED.** No fabricated import/stub DSO, PowerVR/Mesa/glvnd substitute,
ignored undefined reference or arbitrary vendor runtime was used. No fresh
triangle link/map was produced. The smallest remaining graphics input is a
maintainer-provided, reviewable development manifest or source-build route for
the actual H700 fbdev EGL/GLES provider: exact source/build identity, permissible
private-link terms/notices, candidate hashes, SONAMEs, exports and dependency
closure. No contact with maintainers or additional device inventory was performed.

### Local SDL build dependency and verification limits

To supply only SDL's missing build dependency, the existing pinned
`issue_26_sysroot.py` was invoked with a fresh private workspace, the same
source lock and revalidated compiler. It stopped before glibc/SDL:
M4 1.4.20 configure returned 0 in **22.447 s**, but native M4 make returned
**2 in 0.214 s**. The first errors are declarations of `bsearch`/`memchr` in
gnulib-generated headers: `expected identifier or '(' before '_Generic'`.
Native GCC identifies as 16.2.1 and reports default `__STDC_VERSION__=202311L`;
a C23/host-header interaction is the hypothesis, not a proved fix. This is a
host-specific bootstrap failure, not a newly observed Mali/vendor-header failure
and not a reversal of the earlier successful libc build on its different host.
No source/compiler-standard patch or broader bootstrap investigation was made.
Exact normalized stage arguments, fresh environments, tool hashes and log hashes
are appended under `mali_followup` in the existing JSON files.

Offline checks now pass **32 boundary tests plus 22 scanner/CI/Mali tests**.
The added Mali tests use metadata fixtures only, never constructed or linked
DSOs, and cover missing inputs, bogus/host ABI, SONAME/DLL mismatch, changed or
unreviewed provenance, exports/closure/private-version errors and rejection of
an unexpected successful link with unreviewed inputs. A static metadata match
does not authorize linking without genuine input review or any runtime claim.

The existing offline workflow now includes `docs/build/issue-26-*` triggers,
fetches checkout history explicitly, and uses PR base SHA or the default remote
branch on push to find the merge point. `issue_26_ci.py` checks the entire
base-to-head branch diff. Its regression constructs multiple commits and proves
that a whitespace error in the earlier commit fails even when `HEAD^..HEAD`
passes. CI remains offline after checkout: no toolchain build, dependency fetch,
target execution or binary artifact upload.

## Earlier Issue #26 report

This advances existing PR #27 rather than opening another PR. Its earlier
[blocked experiment at 87ca744](https://github.com/almighty-atlas/nextui-mkxp/blob/87ca74459a760cc80e52290d1f79ebbd79ec0dac/docs/build/issue-26-linux49-mali.md),
[input fingerprints](https://github.com/almighty-atlas/nextui-mkxp/blob/87ca74459a760cc80e52290d1f79ebbd79ec0dac/docs/build/issue-26-inputs.json)
and [evidence](https://github.com/almighty-atlas/nextui-mkxp/blob/87ca74459a760cc80e52290d1f79ebbd79ec0dac/docs/build/issue-26-evidence.json)
remain available in the preserved Git history. That separate experiment used
Linux 4.9.0 headers and reported 103 Make restarts in a three-second diagnostic;
it did not complete glibc or compile the triangle. The new experiment uses
Linux 4.9.170 headers, independently pinned GNU sources and a completed Make
4.3 rebuild. Its metadata supersedes the blocked status without treating the
two experiments as identical. The prior scanner and its regression suite are
retained (13 tests after the native-tool regression); its child environment now omits HOME and scanner tools must be native
x86_64 ELF. No earlier PR branch was overwritten or rebased.

## Inputs and mandatory review

[Input lock](issue-26-inputs.json), [host evidence](issue-26-evidence.json),
and [tool fingerprints](issue-26-host-tools.json) record exact hashes and commands.
The compiler archive hash was already published upstream; GNU/kernel/API source
hashes were independently observed over HTTPS. Detached signature validation
was **not** performed. Hashes identify reviewed bytes; they are not license or
publisher authentication certificates.

Reviewed: repository instructions/roadmap/sources/architecture/test plan; issues
#18, #1–#4, #22, #24, #26; open PRs #19–#25, including #21's ADR, #23's source-only
launcher and original source, and #25's gate/crosscheck/tests and [review thread](https://github.com/almighty-atlas/nextui-mkxp/pull/25#issuecomment-6414817887).
The #25 review requirements are reflected in the complete libc rebuild,
separate PowerVR/Mali gates, fresh child environment, scoped repeatability claim,
and retained licensing/device stops.

Upstream default-head API checks on 2026-10-26 still resolved to:

| Repository | Pinned commit, also observed default head |
| --- | --- |
| LoveRetro/gcc-arm-8.3-aarch64-tg5040 | `d37268f5160ec6cd4da541524c8111797e060c36` |
| LoveRetro/h700-toolchain | `04faa348c112617fc6b99be62308099ee6d43581` |
| LoveRetro/NextUI | `5291344b3aceae5fa197437a70824afb41e2d338` |
| JohnnyonFlame/SDL-malifbdev-rot | `d4a7d7503524cc469fe775242f3f925d4dd56c88` |

Original triangle: PR #23 head `60721c1a81a9f54e507650f313a479ecaa9b6d2a`,
`spikes/h700-video/triangle.c`, SHA256
`8a08fe77d8675eb93368c15bd5fd3ddc1b00d9dd9229b8eda595e0a0e1432c42`.
The source is neither duplicated nor modified here. The compiler cache was
independently checked against the archive: **3,890 regular/hardlink contents**,
symlink targets, and complete file inventory, before using its host tools.

## Why 4.19 appeared, and what changed

At the pinned GCC recipe, both `x86_64-aarch64.config` and `aarch64.config`
contain `CT_LINUX_VERSION="4.19"`, `CT_GLIBC_VERSION="2.28"`,
`CT_GLIBC_MIN_KERNEL="4.19"`. The original sysroot's Linux version code is
267008 (4.19.0), and native readelf reports a 4.19.0 GNU ABI note in its
`crt1.o`. Changing the compiler **host** architecture would retain this policy.
This was a static gate; no H700 execution failure was observed.

Pinned crosstool-NG 1.25 commit
[`8fa98eeeff9bc53478d97ef722f366fea151ae64`](https://github.com/crosstool-ng/crosstool-ng/blob/8fa98eeeff9bc53478d97ef722f366fea151ae64/scripts/build/libc/glibc.sh)
computes and passes `--enable-kernel`; it does not universally require 4.19.
glibc 2.28's AArch64 configure fragment at
[`3c03baca37fdcb52c3881e653ca392bba7a99c2b`](https://github.com/bminor/glibc/blob/3c03baca37fdcb52c3881e653ca392bba7a99c2b/sysdeps/unix/sysv/linux/aarch64/configure)
sets `arch_minimum_kernel=3.7.0`. Linux 4.9 is above that architecture minimum.
This build uses the hashed GNU release archive, not an unpinned mirror checkout.

The replacement is a complete matched glibc build/install: libc headers,
startup objects, libc/nonshared archives, loader and shared objects, plus
sanitized Linux 4.9.170 UAPI headers. The generated config records
`__LINUX_KERNEL_VERSION (4 * 65536 + 9 * 256 + 0)` and `cross-compiling = yes`.
The upstream install rules skip target ldconfig when cross compiling.
No old crt object was copied into the replacement and no note was patched.

Lowering the note alone would be insufficient. The kernel configuration also
changes glibc's `__ASSUME_*` syscall policy. For example, `__ASSUME_STATX` is
only defined from 4.11; the pinned `statx.c` retains its ENOSYS/generic fallback
at 4.9. Linux 4.9.170 UAPI headers omit the later syscall definition as well.
This source/config check supports the intended minimum; it does not test every
syscall, device kernel option, driver, or firmware-specific behavior.

The replacement libc's required loader versions are internal to the matching
rebuilt libc/loader pair, including `GLIBC_PRIVATE`; they are not an excuse to
allow arbitrary private versions in applications. The calibration executable
requires only GLIBC_2.17. A future graphics closure requires a separate version
and dependency audit of every authentic DSO. No alternate toolchain candidate
was needed after candidate (a), the known compiler plus rebuilt libc, succeeded.

## Compiler search paths matter

`--sysroot` alone did **not** isolate this compiler. Inspection found its default
`aarch64-nextui-linux-gnu/include` resolving into the **old** libc tree, and its
`libgcc_s.so` alias resolving there too. The crosscheck rejected those inputs.
The final compile/link flags therefore include:

```text
--sysroot=$SYSROOT -B$SYSROOT/usr/lib64/ -static-libgcc -nostdinc
-isystem $GCCROOT/lib/gcc/aarch64-nextui-linux-gnu/8.3.0/include
-isystem $GCCROOT/lib/gcc/aarch64-nextui-linux-gnu/8.3.0/include-fixed
-isystem $SYSROOT/usr/include
-L$SYSROOT/lib64 -L$SYSROOT/usr/lib64
-Wl,-rpath-link,$SYSROOT/lib64
```

This keeps only the same verified GCC's internal headers, crtbegin/crtend and
static support archive. It excludes all old libc headers/CRT/DSOs. glibc's own
build uses `-nostdinc` and the configured fresh UAPI headers too.
The calibration link map, preprocessor verbose search list, and triangle `.d`
dependencies are checked by resolved paths, including symlinks. Runtime RPATH
is never used. `-rpath-link` affects host linking only. No compiler support DSO
is required by this calibration ELF; this says nothing about future engine C++
requirements. The compiler and libstdc++ were not rebuilt or qualified for mkxp-z.

## SDL Mali evidence and first remaining blocker

The pinned H700 recipe enables Mali fbdev/GLES and shared ALSA, disables
X11/Wayland/KMS, and applies `support/sdl2-h700.patch` (hash in lock).
The fork's `SDL_version.h` is 2.28.5. Source-confirmed behavior includes
opening `/dev/fb0` and `/dev/ion`, the Mali native-pixmap ABI and
`eglCreatePixmapSurface`, and dynamically loading `libEGL.so`/`libGLESv2.so`.
These requirements cannot be inferred from generic EGL symbol names alone.
NextUI's pinned H700 startup selects `SDL_VIDEODRIVER=mali`.

For the object-only check, upstream configure generates a real Mali SDL config;
all public SDL headers are private copies of the pinned source and only
`SDL_config.h` is replaced with that generated file. Khronos EGL/GLES2/KHR
headers are pinned genuine API definitions with their notices. This is a
**header/configuration experiment**: audio, joystick, haptic and renderer are
disabled, no SDL library is built, and the recipe's input patch is reviewed but
not applied. It does not reproduce the shipped H700 SDL binary or attest its
SONAME. The libtool recipe expects the SDL2 ABI (`libSDL2-2.0.so.0` convention);
installed SONAMEs, exports, dependency closure and hashes remain UNKNOWN.

The original triangle's SDL calls, direct `gl*` calls and direct
`eglGetCurrentDisplay`/`eglQueryString` calls type-check with these authentic
headers. A real compiler link using `-lSDL2 -lGLESv2 -lEGL`, without ignored
unresolved symbols, fails because those matching target link libraries are
absent. No shims, empty DSOs, dummy successes, host libraries, Mesa/glvnd,
PowerVR or copied stock vendor libraries are used. PR #25's SDL 2.26.1/PowerVR
link is retained solely as historical host evidence, never H700 evidence.

Owner metadata in issue #1 reports RG35XX Pro, BaseOS 1.4.0,
NextUI-20261013-0/build39a06de, Linux 4.9.170 AArch64, and an SDL 2.28.5 filename.
It provides no attestation of the exact installed SDL/loader/libc/GPU bytes,
ION ABI/permissions, or successful display. Those remain OWNER_NOT_TESTED.
The smallest next **non-device** step is a license-reviewed, source-identifiable
H700 SDL/EGL/GLES development interface from the relevant maintainers: exact
source/recipe, notices, target SONAMEs/exports/ELF requirements, and authorized
link inputs (or an authorized host-only build route). Until then, stop at
LINK_BLOCKED. No owner command to run on the handheld is requested.

## Environment boundary and offline verification

Build children receive a fresh dictionary, never `os.environ.copy()`:

```text
PATH=<owned tool-symlink directory only>
LC_ALL=C LANG=C TMPDIR=<owned workspace>/tmp CONFIG_SITE=/dev/null
PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 SOURCE_DATE_EPOCH=1533081600
CC=<verified cross gcc> BUILD_CC=/usr/bin/gcc
PKG_CONFIG_LIBDIR=<empty owned directory> PKG_CONFIG_SYSROOT_DIR=<new sysroot>
```

The last two variables are needed only for the SDL crosscheck. HOME is omitted,
never reassigned. Loader variables (`LD_PRELOAD`, `LD_LIBRARY_PATH`, `LD_AUDIT`,
`LD_DEBUG`), PYTHONPATH, BASH_ENV/ENV, GCC_EXEC_PREFIX/COMPILER_PATH, CPATH,
C_INCLUDE_PATH/CPLUS_INCLUDE_PATH/LIBRARY_PATH, arbitrary PKG_CONFIG_* variables,
proxy/secrets, locale and parent PATH/TMPDIR/build flags are not inherited.
Only named tool overrides are accepted, each resolving to a recorded tool.
Unknown PATH entries, changed symlinks/hashes, and unreviewed wrappers fail closed.
The pinned CT-ng `ld` shell selector was explicitly reviewed: an absent
`CTNG_LD_IS` selects its verified sibling `ld.bfd`; that variable is also dropped.
Source configure flags are explicit recorded arguments, not inherited CFLAGS.

`issue_26_sysroot.py` enumerates the OS bootstrap allowlist; helper m4, bison,
gawk and make come from the six hashed archives in the lock. The final
crosscheck drops GCC debugger/populate/ldd/gcov wrappers from its selected set.
No network fetcher appears in the tool farm. Source fetching is a separate
trusted preparation step; the checked build commands never fetch.
The observed first build's broader explicit 106-entry manifest is preserved
for audit; the consolidated recipe narrows it to **90 named tools**. Fingerprints, arguments, exit
codes and fresh environments are logged before publishing a sanitized record.

This is a **process environment/input boundary**, not a container security jail
or a complete compiler-execution trace. Trusted OS tools may invoke their
native interpreters/shared libraries, and pinned build scripts can name
absolute executables. Native GCC bootstrap search resources are trusted host
inputs. There is no syscall/network enforcement inside these Python helpers.
Start from a trusted native `/usr/bin/python3 -I`; cleaning child variables
cannot undo hostile preload code already loaded into the bootstrap process.
Hashes and an allowlist do not make unreviewed executable inputs trustworthy.

Run offline tests (also run automatically by the read-only CI workflow):

```sh
python3 -I -B scripts/issue_26_test.py
python3 -I -B -m unittest discover -s scripts/issue_26_tests -v
```

They cover hostile environment/preload/PATH, wrappers and target execution
format rejection, unknown/mutated file/link provenance, host include and
symlink escapes, malformed ELF/archive input, unsafe links, mismatched kernel
note, GLIBC floor/private/C++ versions, RPATH, NEEDED and interpreter, and ELF
version definitions versus requirements. CI performs no cross-build, download,
target run or external artifact upload. The test status in the PR refers to
these offline gates, not to H700 runtime validation.

## Rights gate

PR #19's provenance/notice gate is unchanged. The triangle is original MIT;
that does not authorize a combined work. The SDL fork's root notice is zlib,
but `src/video/mali-fbdev/mali.h` carries a GPL notice. The H700 input patch and
NextUI licensing context also need an exact provenance/combination review.
A permissive root notice is not a blanket exception for those files.

Before distribution, obtain a recorded compatibility determination or exact
permission/exception for the Mali code and patch; identify authentic vendor
EGL/GLES development/runtime redistribution terms; preserve Khronos/SDL notices;
and satisfy the rebuilt glibc LGPL 2.1-or-later corresponding-source/relinking
requirements, startup-file exceptions where applicable, and GCC runtime
exception conditions. No such clearance is asserted here. Omitting a vendor
library as a “system library” does not automatically settle the combined-work
question. Even the libc-only private build is not a distribution approval.

## Host-only reproduction

Use a private native x86_64 Linux workspace (not a NextUI directory), two build
jobs and sufficient disk space. This session had a two-CPU quota, 8 GiB memory,
and about 27 GiB free initially. The scripts do not download dependencies or
change host packages. Fetch the six source archives and compiler archive from
`issue-26-inputs.json` separately, retain their notices, and verify every SHA
before use. Privately unpack the compiler under `$COMPILER_PARENT`; the scripts
revalidate every extracted file/link against the hashed archive, including
rejecting extra files. Obtain clean detached source checkouts at the SDL and
PR #23 commits above, and the five raw Khronos headers at their locked URLs,
under `$API/{EGL,GLES2,KHR}`. Nothing from these checkouts enters the PR.

All variables below are task-local absolute paths; use paths without whitespace
for the GNU configure recipe. No HOME variable is changed. Review trusted OS
bootstrap tools and scripts first. A fingerprint of a hostile bootstrap does
not sanitize it.

```sh
/usr/bin/python3 -I scripts/issue_26_sysroot.py \
  --workspace "$PRIVATE_BUILD" --archives "$ARCHIVES" \
  --compiler "$COMPILER_PARENT" --compiler-archive "$COMPILER_ARCHIVE"
```

The command requires a **fresh** build directory. Its stages are source hash
checking/safe extraction; private m4 1.4.20, bison 3.8.2, gawk 5.3.2 and make 4.3
builds (`configure --disable-nls`, `make -j2`, private install); Linux UAPI
`headers_install`; and:

```text
sh <glibc-2.28>/configure
  --build=x86_64-pc-linux-gnu --host=aarch64-nextui-linux-gnu --prefix=/usr
  --with-headers=<private>/kernel-headers/include
  --enable-kernel=4.9.0 --disable-werror --disable-nscd
<private make 4.3> -j2
<private make 4.3> install_root=<private>/sysroot install
```

The script checks `cross-compiling = yes` before make/install, copies sanitized
UAPI headers into the installed sysroot, and writes local provenance with the
resulting tree digest. Each stage records argv, environment, native executable
hash, exit status and elapsed time. It never runs `make check` or a target tool.
Review the resulting provenance, then pass its digest explicitly:

```sh
/usr/bin/python3 -I scripts/issue_26_crosscheck.py \
  --workspace "$PRIVATE_CHECK" \
  --compiler "$COMPILER_PARENT" --compiler-archive "$COMPILER_ARCHIVE" \
  --records "$PRIVATE_BUILD/host-tools.json" \
  --sysroot "$PRIVATE_BUILD/sysroot" \
  --sysroot-tree-sha256 "$REVIEWED_SYSROOT_DIGEST" \
  --sdl "$SDL_CHECKOUT" \
  --triangle "$PR23_CHECKOUT/spikes/h700-video/triangle.c" --api "$API"
```

The fresh crosscheck directory receives only private outputs. A successful
crosscheck exit means the libc static gate and original-object gate passed
**and the expected missing-library blocker was recorded**. It never means the
triangle linked or ran. An unexpected successful graphics link also fails the
script pending input provenance review. Review `result.json`, all log JSON,
link maps and dependency files together; do not upload the private directory.

## Measured failures and repeatability limits

The initial full glibc build used host GNU Make 4.4.1. After building libc and
startup objects it spent several minutes in `stdio-common/others`, consuming a
CPU while repeatedly reading dependency files. That attempt was deliberately
terminated at **565.212 seconds**, parent exit 2. This is an observed host-build
failure, not a diagnosed general upstream Make bug. A private GNU Make 4.3
build resumed the unchanged glibc tree and completed make in **38.335 seconds**;
staged install returned 0. The consolidated recipe then completed a second
full build and install from a fresh directory, using Make 4.3 from the start;
its full glibc make took **274.374 seconds**, exit 0. All 16 source-build stages
returned 0. This is an additional rebuild on the same host and compiler, not
a clean-room rebuild. The initial and consolidated sysroot tree digests differ;
raw byte identity across build roots is not an acceptance claim. Both
crosschecks passed the same static libc properties; the original triangle
object hashes match across these two roots, while the raw libc probe hashes
differ. Each root's duplicate probe link is byte-identical.

Development crosschecks also deliberately failed at deleted temporary link-map
inputs, old `libgcc_s` provenance, and the old default include search path.
The final recipe keeps the probe object, uses static GCC support and explicit
system includes, then revalidates actual paths. These checks must not be weakened
merely to obtain a successful link.

Each libc probe is linked twice in the same crosscheck directory and its bytes
compared. This is a scoped same-workspace repeat, **not** a clean-room or
cross-host reproducibility claim. The original compiler is a verified release
binary, not rebuilt here; native OS/compiler/interpreter/shared-library versions
are part of the trusted host. Embedded build paths, locale-independent but
host-generated files, and native helper build differences can change raw
sysroot hashes. Source dates are preserved during extraction to avoid silently
regenerating release files with unpinned autotools. A fixed SOURCE_DATE_EPOCH
alone does not prove reproducibility.
