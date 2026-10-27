# Issue #22 — stock-SDL proc-triangle preparation

**Current result: BUILD_BLOCKED.** A pinned private source scaffold and host
verification/staging tools exist; **no new AArch64 executable or installable Pak
was built**. No target code or graphics ran. Do not deploy the scaffold or remove
`SOURCE_ONLY`. Refs [Issue #22](https://github.com/almighty-atlas/nextui-mkxp/issues/22).
Machine-readable facts: [evidence.json](evidence.json).

## Source and runtime decision

This separate PR starts at main `107db135b8e8ef72f6d61c78be14416330727b0d`.
It preserves all earlier branches; it does not merge PR #23/#27 or rewrite them.
Required project documents, actual source/build scripts, evidence and reviews in
those PRs, PR #21's ADR and PR #19's distribution STOP were read before implementation.

| Source | Immutable revision / identity |
| --- | --- |
| PR #23 original triangle/launcher/MIT notice | `60721c1a81a9f54e507650f313a479ecaa9b6d2a` |
| Original C SHA-256 | `8a08fe77d8675eb93368c15bd5fd3ddc1b00d9dd9229b8eda595e0a0e1432c42` |
| PR #27 generator, source-build drivers, native mocks | `1c04c578e3a35acc40b8669986228e3a2ae056c0` |
| Unchanged generated proc variant SHA-256 | `9b95b0bf6cddfebb6f2946b39896b69fea61614157b80ccc52d698d81e48f19d` |
| Source-built link-only SDL | fork `d4a7d7503524cc469fe775242f3f925d4dd56c88`, patch recipe `04faa348c112617fc6b99be62308099ee6d43581`; actual input hashes in exported PR #27 lock |

The [owner's new installed-SDL metadata](https://github.com/almighty-atlas/nextui-mkxp/issues/22#issuecomment-6450135998)
confirms SONAME `libSDL2-2.0.so.0`, SHA-256
`76de58c80f9a6d901fc5563711b9edc869a759c9446c5a6cd798f4c6774f7577`,
21/21 required SDL export names, SDL GLIBC needs through 2.17, libc's GLIBC_2.27
definition and Linux 4.9.170. These are **OWNER_REPORTED_METADATA**, not new
measurements by this agent or H700 runtime proof. The installed SDL additionally
needs `libsamplerate.so.0`; its exact closure is not verified here.

**Candidate strategy:** rebuild the existing original 26-proc variant, privately
link against the real source-built SDL from PR #27, and ship **only the original
program**, not that SDL. The executable must need precisely the SDL SONAME and
libc, import all 21 SDL names unversioned, require only GLIBC_2.17, and contain no
RPATH/RUNPATH. The normal NextUI library search environment should select the
installed SDL. This is a defensible candidate, **not proof of actual loader
selection, identical ABI signatures, relocations or vendor runtime operation**.
No installed SDL, proprietary library, dummy import DSO, ignored undefined symbol,
PowerVR/Mesa replacement or driver file is used as a build input or shipped.

The byte-identical proc variant resolves all 26 typed GL pointers only after
MakeCurrent, checks every result and the ES profile, preserves real shaders,
buffer/uniform animation, draws/swaps, partial cleanup, own TERM/INT and SDL_QUIT,
SSH/backend refusal, five-second cooperative deadline and frame cap. It omits
direct EGL metadata calls. A blocked driver/init/swap/cleanup call can still hang
beyond five seconds; there is **no hard watchdog guarantee** or automatic repair.

## Actual Alpine bootstrap attempt

The pinned 221.2-MiB compiler archive was fetched privately from the URL in
`evidence.json` and its SHA-256 checked **before extraction/execution**:

```text
d4ac4ef1968668f93f625f2b226c69d74739ae58ff640d2ce3aaae6b4d1b93d3
```

Only its regular host-GCC member was extracted for this probe. GNU readelf on
that host ELF reports:

```text
[Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]
```

The verified GCC file exists (SHA-256 `8be8cecfcf9f002099eef8bc97c83c8dbaa79bbad85c418ad85e1471cb05045f`),
but that interpreter does not exist here. Running **host** `gcc --version`
returns **127 / not found**. The target architecture was never executed. No
container engine or PR #27 private Linux-4.9 sysroot/SDL outputs are available.
Native Alpine GCC is not an equivalent glibc-target compiler.

This is the first concrete blocker, not a newly failed SDL/GLIBC/H700 compatibility
test. No loader shim, `gcompat`, host-wide glibc install, sudo, privileged container,
mount or ABI-note spoof was attempted. The original SDK sysroot is **not usable
unchanged**: its 4.19 minimum remains too high despite the new owner SDL evidence.

## Reproducible private process on a capable host

These are **commands for a later trusted x86_64 glibc Linux build host**, not a
claim that a clean environment/container has been built here. Use existing trusted
native tools listed in the exported `issue_26_sysroot.py` (Python 3.12+, GNU C/C++,
binutils, Bash, Perl, make and standard GNU build utilities), sufficient private
disk space and two build jobs. No root or handheld access is required. A rootless
glibc container is an alternative only after its image digest/tool inventory is
separately pinned and reviewed; no floating Docker image is prescribed here.

### 1. Prepare exact original source and guarded layout, offline

Ensure local git objects exist at the two full PR commits above. A fresh clone
may need explicit `git fetch origin` for their PR branches; preparation itself
never fetches or downloads. Set `P` to a **fresh path outside the repository**:

```sh
python3 -I -B spikes/h700-stock-video/prepare.py prepare --output "$P"
```

This exports only reviewed original project source/scripts/mock declarations,
the PR #27 input lock and the original MIT notice via local pinned git blobs.
It regenerates and checks both C hashes and writes `preparation.json` with every
exported file hash. The prepared layout includes:

```text
triangle-original.c
triangle-proc.c
scripts/issue_26_{sysroot,sdl_proc,sandbox,proc_variant}.py
docs/build/issue-26-inputs.json
Tools/h700/RMXP-Video-Test.pak/launch.sh     unchanged, executable
Tools/h700/RMXP-Video-Test.pak/SOURCE_ONLY  unchanged, never removed
LICENSE
```

It also exports the original native proc mock suite/fixtures from PR #27, keeping
their license and provenance. There is **no binary** in this scaffold.

### 2. Supply exact private build inputs; do not use stock firmware bundles

Separately fetch/review the compiler and six GNU/kernel archives at the exported
lock's immutable URLs, checking every SHA-256 before safe extraction. Keep the
compiler archive and verified extracted tree under `COMPILER_ARCHIVE` and
`COMPILER_PARENT`. Keep GNU archives under `ARCHIVES`. Use the real source
checkout of the SDL fork at its pinned full commit (`SDL_CHECKOUT`), the pinned
H700 patch (`H700_PATCH`) and the five real public Khronos headers at their locked
URLs/hashes under `API/{GLES2,EGL,KHR}`. Preserve their notices privately.
Never use the original mock headers as target build headers. Do not fetch SDL,
EGL/GLES or Mali binaries from the handheld or a firmware image.

Use the **unchanged existing build drivers**; they revalidate compiler-tree files,
source trees/archives/header hashes and actual include/link inputs. Native helper
sources include M4 1.4.21 and make 4.3, avoiding documented earlier bootstrap bugs:

```sh
python3 -I -B "$P/scripts/issue_26_sysroot.py" \
  --workspace "$PRIVATE_SYSROOT_BUILD" --archives "$ARCHIVES" \
  --compiler "$COMPILER_PARENT" --compiler-archive "$COMPILER_ARCHIVE"
```

Review `sysroot-provenance.json`, all stage logs and the resulting tree digest;
pass it as `REVIEWED_SYSROOT_DIGEST`, not the earlier experiment's digest. This is
a complete glibc 2.28 build/install with Linux 4.9.170 UAPI headers and minimum
kernel 4.9.0, not a patched ELF note or transplanted crt object.

```sh
python3 -I -B "$P/scripts/issue_26_sdl_proc.py" \
  --workspace "$PRIVATE_SDL_BUILD" \
  --compiler "$COMPILER_PARENT" --compiler-archive "$COMPILER_ARCHIVE" \
  --records "$PRIVATE_SYSROOT_BUILD/host-tools.json" \
  --sysroot "$PRIVATE_SYSROOT_BUILD/sysroot" \
  --sysroot-tree-sha256 "$REVIEWED_SYSROOT_DIGEST" \
  --sdl "$SDL_CHECKOUT" --patch "$H700_PATCH" \
  --api "$API" --triangle "$P/triangle-original.c"
```

This source-builds a **private link-only SDL** with audio disabled, genuinely
compiles/links the proc triangle and repeats the link. It retains strict undefined
symbol checks, compiler isolation flags, link maps and source/dependency receipts.
It never runs ARM, downloads or packages libraries. Private SDL differs from the
installed SDL and is **not** a replacement candidate. The existing driver's
successful `result.json` is mandatory for the next step.

### 3. Inspect actual ELF and stage a still-disabled private Pak

```sh
python3 -I -B spikes/h700-stock-video/prepare.py assemble \
  --prepared "$P" --build "$PRIVATE_SDL_BUILD" \
  --output "$FRESH_PRIVATE_STAGE" --readelf /usr/bin/readelf
```

Assembly rechecks variant/source/ELF receipt hashes and uses only host GNU readelf
(`-h -l -d --version-info --notes --dyn-syms`). It requires ELF64 LE AArch64 ET_EXEC,
`/lib/ld-linux-aarch64.so.1`, GNU Linux ABI 4.9.0, non-executable stack, precisely
`libSDL2-2.0.so.0` + `libc.so.6`, GLIBC_2.17 version needs, all 21 expected unversioned
SDL undefined names, no direct GL/EGL imports, RPATH/RUNPATH, TEXTREL or unreviewed
imports. Conservative metadata mismatch refuses assembly; no target `ldd` or
loader execution. It re-reads the launch/guard/license from pinned original git
objects and copies **only**:

```text
Tools/h700/RMXP-Video-Test.pak/launch.sh
Tools/h700/RMXP-Video-Test.pak/SOURCE_ONLY
Tools/h700/RMXP-Video-Test.pak/LICENSE
Tools/h700/RMXP-Video-Test.pak/source/triangle-proc.c
Tools/h700/RMXP-Video-Test.pak/bin/triangle
manifest.json                              outside the Pak
```

No `lib/` directory or source-built/stock dependency enters staging. The manifest
contains ELF facts, imports, file checksums and continuing runtime/legal stops.
Even `HOST_VERIFIED` means **static private artifact verification**, not H700
compatibility. This assembly path is tested with metadata mocks only in this
session, not a real AArch64 artifact. Inspect outputs and original build maps/logs
independently; a JSON build receipt alone is not compiler-execution attestation.
Host tools, private working directories and local git objects are trusted, not
sandboxed against hostile concurrent mutation. Do not upload the private stage.

## Host tests and actual evidence

```sh
python3 -I -B -m unittest discover -s spikes/h700-stock-video -p test_prepare.py -v
python3 -I -B -m unittest discover -s "$P/scripts/issue_26_tests" -p test_proc.py -v
sh -n "$P/Tools/h700/RMXP-Video-Test.pak/launch.sh"
git diff --check origin/main...HEAD
```

Tests only compile/run **native original mocks**, never target code or real SDL/GL.
This Alpine session installed native GCC/musl headers/make into the existing
private user-cache package root, non-root with scripts disabled; no host-wide
package changes. Existing private Python 3.14.10/readelf 2.45.1 were reused.
The local `cc` wrapper supplies only that native sysroot/tool paths; it does not
cross-compile or substitute for H700 proof. Exact local invocations/tool paths
are in the PR. All temporary fixtures are deleted; private source preparation and
the verified compiler archive remain outside tracked paths for review.

| Gate | Evidence level | Actual outcome |
| --- | --- | --- |
| Source generator/original/launcher/guard identity, native proc behavior | verified-on-host | PASS, byte-identical generated variant; 5 proc tests |
| New parser/assembly/guard tests | verified-on-host | PASS, 15 tests, metadata-only acceptance/assembly fixtures; actual host ELF rejection |
| All 26 null GL lookups, changing triangle uniforms/draw/swap, simulated 5000 ms, clock/cleanup failures | verified-on-host | PASS in original native mock suite; not real time/GPU |
| Pinned compiler archive and host ELF | verified-on-host | SHA-256 matches; host start BLOCKED (exit 127, absent glibc loader) |
| New actual AArch64 ELF/link map/repeat link | HOST | BUILD_BLOCKED; no new artifact, no facts fabricated |
| Prior AArch64 ELF/link proof | PR #27 reported HOST | Preserved, not attributed to this build |
| Automatic CI | CI | BLOCKED by existing workflow-write credential limitation; not activated/retried |
| Installed SDL/libc export/version observations | OWNER_REPORTED_METADATA | New issue comment/user report, not independently repeated |
| Actual relocation/libsamplerate/vendor closure, Mali context/presentation/orientation/NextUI return | H700 | NOT_TESTED |
| Distribution | SOURCE | BLOCKED; no rights clearance |

## Later explicitly authorized NextUI Tools test (proposal only)

**Keine Aktion jetzt:** Zuerst den echten privaten Build auf einem geeigneten
glibc-Host erzeugen und ELF/Manifest/Maps unabhängig prüfen. SOURCE_ONLY bleibt
bis zu einer gesonderten Freigabe erhalten. Das ist der nächste konkrete Schritt,
nicht ein weiterer Geräte-Metadatentest oder ein Start über SSH.

After a real build, resolve PR #19's combined-work/source/notice and relinking
obligations and obtain explicit named approval of the exact candidate hash,
limited display ownership and a separately reviewed SOURCE_ONLY transition.
This PR has **no guard-removal flag or deployment/activation command**.

Only then propose one owner-run sequence:

1. Review allowlisted files/checksums and source/notices on the owner's host. No
   SDL/vendor/glibc libraries are supplied. Stop if a Pak of this name already
   exists; do not overwrite existing Paks, saves or `.system`.
2. Under separate transfer authorization, place only the reviewed new Pak in
   `Tools/h700` via the owner's existing file-transfer method. Transfer is not
   graphical execution. No firmware scripts, services or permission changes.
3. Physically select **NextUI → Tools → RMXP-Video-Test**, never launch graphics
   from SSH. Observe a moving multicolored shader triangle, correct orientation
   and hardware renderer identity; black/clear-only/offscreen output is not PASS.
4. Let it self-exit after the cooperative 5000-ms loop, verify responsive NextUI
   video/navigation and no remaining test process. The original foreground exec,
   no-SSH/context checks, fb0/ION metadata checks, no-core/log limit and owned
   bounded `.userdata/h700/RMXP-Video-Test/latest.log` behavior are unchanged.
5. On first failure/hang, stop testing and record the first stage. No global kill,
   reboot, privileged repair, kernel/zram/driver change or automatic fallback.
   Share only reviewed `RMXP_VIDEO` lines, candidate hash, exact firmware/model
   and physical observation. Code 0 or a successful void SDL swap is not display
   proof. Audio/input mapping, mkxp-z, games and performance remain NOT_TESTED.

Rollback after normal return: under owner control remove only this newly added
Pak and optionally its owned log directory after evidence collection. No cleanup
script or modification of existing user data is included.

## Rights and scope

`prepare.py`/tests are original MIT-marked project code; the reused original
triangle, launcher and mock declarations retain their MIT notice and provenance.
No third-party runtime/header is vendored. SDL source fork/root zlib terms do not
clear GPL-noticed Mali backend code/patch context. Relying on the installed SDL
is not a legal exception by itself. glibc startup/LGPL corresponding-source or
relinking requirements, GCC runtime exception, Khronos notices, and vendor/source
combination rights still need review. No binaries are committed, uploaded or
redistributed, and private building does not authorize release or deployment.
