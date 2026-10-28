# mkxp-z source and dependency lock for the minimal H700 profile

2026-10-28 · Refs #5 · Stacked on the #6 runtime branch (PR #32); no merge.

## Result

| Result | Level | Check |
| --- | --- | --- |
| PASS | verified-on-host | mkxp-z `37a04d14413454551a7b6aadbb4e93e67168accb` fetched by exact commit; `git rev-parse HEAD` matches. Upstream `HEAD` equalled this commit on 2026-10-28 |
| PASS | verified-on-host | All 56 Meson wraps classified: 22 selected, 34 explicitly excluded ([profile](../build/h700-engine/mkxp-z-profile.json)) |
| PASS | verified-on-host | [Lock](../build/h700-engine/mkxp-z-lock.json) `LOCK_COMPLETE`: 21 HTTPS archives with wrap SHA-256, 1 git wrap at an immutable commit plus 17 recursive submodule commits, every patch file and patch-directory digest |
| PASS | verified-on-host | Offline cross `meson setup` for aarch64, see [below](#offline-configure-meson-setup-pass-verified-on-host) |
| PASS | verified-on-host | All 21 archives (plus 1 WrapDB overlay) downloaded into a private Meson packagecache (outside Git), verified while streaming and re-verified afterwards. 409 MiB used, 30 GiB still free (26-GiB stop guard respected) |
| NOT_PERFORMED | — | License/grant review of the selected closure (#3); embedded-asset review |
| NOT_ATTEMPTED | — | Compile, link, device execution |

Private `git archive` of the commit: SHA-256
`93fbab8c9683ec79e01909de91fc33d23938c2aa7372213ffcd80301cca55ff2`
(git 2.47.3, prefix `mkxp-z-37a04d14/`). That digest depends on the git
version and is only a local fingerprint. The commit ID is the identity.

## Findings that change the earlier plan

1. **The engine needs mkxp-z's patched Ruby, not the stock Ruby tested
   earlier.** `subprojects/packagefiles/ruby-3.1-mkxp-z-patches.patch`
   changes how the interpreter behaves: private/protected method visibility
   checks are skipped (`vm_eval.c`, `vm_insnhelper.c`), "superclass mismatch"
   is ignored (`class.c`, `vm_insnhelper.c`), and the sprintf
   "too many arguments" check is removed. RGSS/Essentials-style scripts
   depend on this behaviour. The wrap also builds Ruby **statically**, with
   statically linked extensions (`--disable-shared --with-static-linked-ext`).
   The profile therefore uses `ruby_system=disabled`. This supersedes the
   `ruby_system=enabled` proposal in [H700_RUNTIME_PIPELINE.md](H700_RUNTIME_PIPELINE.md).
   The earlier [Ruby batch PASS](H700_RUBY_BATCH.md) still holds as evidence
   for the toolchain, glibc/loader, encodings and libffi on the device. It
   is not evidence that the engine's Ruby works.
2. **SDL:** `sdl_system=enabled` uses the existing private Mali-fbdev SDL
   2.28.5 build (`SDL_VIDEO_DRIVER_MALI`, no X11/Wayland/KMSDRM, no SDL audio).
   This avoids the vendored SDL 2.28.1 branch, which would pull in X11,
   Wayland, libdecor, udev, D-Bus, IBus, DRM and optionally ANGLE/SPIR-V/Vulkan.
   Missing SDL audio is fine because mkxp-z plays audio through OpenAL Soft.
   That SDL's `sdl2.pc` declares `-Wl,-rpath,/usr/lib`, which must be
   overridden or audited at link time.
3. **mesa is headers only** at this commit (`packagefiles/mesa/meson.build`
   declares include directories). No Mesa library is built or shipped.
4. **SDL_image** `release-2.6.3` is a mutable tag, resolved to
   `d3c6d5963dbe438bcae0e2b6f3d7cfea23d02829`, with `clone-recursive`.
   AVIF, TIFF and WebP are off by default and mkxp-z doesn't enable them,
   so the dav1d/libavif/libtiff/libwebp submodules are fetched but
   presumably not built. JXL is enabled: libjxl with Brotli, Highway,
   skcms and possibly lcms/sjpeg. This is the largest native closure and
   has upstream patches (`sdl2_image-libjxl-*`, `sdl2_image-highway-*`).
5. **Audio:** OpenAL Soft 1.24.3 with vendored alsa-lib 1.2.15.3. Whether
   its configuration path and plugins match NextUI's ALSA setup is untested.
   FluidSynth uses the embedded OSAL profile; glib is not required.
6. `-static-libstdc++` on non-Windows remains open (see
   [H700_CXX_ABI.md](H700_CXX_ABI.md)).

## Profile

Meson options (recorded in the profile, not yet applied):
`default_system=disabled`, `sdl_system=enabled`, `ruby_system=disabled`,
`gfx_backend=gles`, `angle/openssl/extra_shaders=disabled` (extra shaders would
require GPLv3), `use_miniffi=false`, no CJK font, JACK/PulseAudio/PipeWire/OSS
disabled.

Selected wraps: alsa-lib, fluidsynth, fmt, freetype, gcem, libffi,
libiconv, libyaml, mesa (headers), ogg, openal-soft, physfs, pixman, ruby-3.1,
sdl2_image, sdl2_sound, sdl2_ttf, theora, theoraplay, uchardet, vorbis, zlib.

## Reproduction

```sh
python3 scripts/mkxp_z_source_lock.py --source "$MKXP_Z_CHECKOUT" \
  --profile build/h700-engine/mkxp-z-profile.json            # lock only
python3 scripts/mkxp_z_source_lock.py --source "$MKXP_Z_CHECKOUT" \
  --profile build/h700-engine/mkxp-z-profile.json --fetch "$PRIVATE_PACKAGECACHE"
```

The lock rejects unclassified, stale or duplicate wraps, missing or
non-HTTPS archive hashes, mutable git revisions, unrecorded submodules and
missing patch files. The fetch is HTTPS-only, size-capped (256 MiB), verifies
before an atomic rename and re-verifies cached files. It never extracts,
configures or runs anything. Downloaded sources are third-party code; they
stay in the private cache and are not tracked here.

Local check: `python3 -m unittest discover -s tests` (verified-on-host, not CI).

## Offline configure: `meson setup` PASS (verified-on-host)

`scripts/mkxp_z_configure.py` re-derives the lock and requires it to equal
the committed one. It re-hashes every cached archive, the private SDL
library (`25dba080…`, as in its build receipt) and the pinned native Ruby,
compiler archive and sysroot tree. It then stages everything in a fresh
private job and runs only `meson setup --wrap-mode=nodownload` in the tools
image: no network, read-only rootfs, unprivileged UID, 2 CPUs / 4 GiB,
`build_alias=x86_64-pc-linux-gnu` for every nested autoconf, a 26-GiB
free-space stop guard and a 3-GiB job budget. Afterwards it scans every
configure log for target-execution attempts.

| Attempt | Result | Cause / fix |
| --- | --- | --- |
| 1 | BLOCKED at OpenAL Soft | **Lock gap:** the OpenAL Soft wrap also downloads a WrapDB overlay (`patch_url`/`patch_hash`) that the lock did not record. The lock now records overlays with HTTPS and hash requirements and rejects any unknown wrap key. The overlay (`6642f3f3…`) was fetched and verified |
| 2 | BLOCKED at SDL_image | Meson does not apply `diff_files` to a pre-provided git checkout, so mkxp-z's SDL_image patches were missing. The driver now applies the locked patches in wrap order with `patch -p1 --forward`, after a hash check |
| 3 | **MESON_SETUP_PASS** in 63 s | All 22 subprojects configured, including the patched Ruby; exit 0; **no target-execution attempts** in any configure log |

The configuration mkxp-z reports: version 2.4.2, ALSA on; ANGLE, OpenSSL,
JACK, PulseAudio, PipeWire, OSS and the GPLv3 extra shaders off;
`License: GPL-2.0-or-later`. Non-blocking warnings: pixman OpenMP header
missing, FluidSynth `gnu90` c_std ignored, SDL_image `extract_all_objects`.

Private receipt `configure-result.json` SHA-256
`51e7cd531cab6f560067ee819e9f5ca1fc7f6cf372a47a516c55e7852ec44893`; it binds
lock `4d9d9a97…`, profile `a05d93ad…` and driver `1a1c00c1…`. The job is
about 1.0 GB. Logs of the two failed attempts were kept privately; their
job trees were deleted to stay above the disk guard.

## Disk reserve decision

After configuring, tiny02 had about 28.1 GiB free, only ~2.1 GiB above the
previous 26-GiB stop guard (25-GiB hard reserve). **On 2026-10-28 the owner
lowered the hard reserve to 5 GiB** for these builds. The driver takes it
as `--reserve-gib` (default still 25; values below 5 are rejected),
stops 1 GiB above it and refuses to start a fresh setup with less than
reserve + 2 GiB free. No Docker prune or deletion of other data is
implied.

## Compile

`--phase compile --job <configured job>` reuses a `MESON_SETUP_PASS` job.
It requires identical lock, profile and pinned inputs, runs `meson compile
-j 2` in the same container profile, scans all logs for target-execution
attempts and records the hashes of AArch64 ELF executables in the build
root. ABI and device execution remain separate steps.

### First successful compile (verified-on-host)

Final private job `engine-build-20261028T172043Z`: setup PASS, then **684/684**
compile/link steps PASS in **463 seconds**. Candidate `mkxp-z.aarch64`:
34,914,232 bytes, SHA-256
`245e5cb379f305660c12afe41cc9047da5ceec3bff67dd156f92ae100770558c`.
Receipt SHA-256 `ef2d2bff731e64f25f3c174badf6726f19590631427aa79bc50f22c642b7db9c`.
No target-execution attempts found in logs. See
[machine-readable evidence](../build/h700-engine/engine-build-evidence.json).

Failures fixed before success:

- Meson's `sys_root` property prefixed the private SDL include paths with the
  sysroot; removed that property while preserving explicit compiler `--sysroot`.
- OpenAL Soft 1.24.3 exposed GCC 8 limitations: 12 runtime enum helpers could
  not be `constexpr`, `std::reduce` was unavailable, and `std::filesystem`
  required `libstdc++fs`. The local, hash-pinned
  `patches/h700/openal-soft-1.24.3-gcc8.patch` is appended to the staged wrap.
  It uses `inline` helpers, sequential `std::accumulate` and a filesystem link
  dependency. Runtime behavior remains untested; reduction order may differ.

Remaining: initial readelf inspection found build RPATH
`/job/sdl-prefix/lib:$ORIGIN`. Upstream's private DESTDIR install step removes
the build path and leaves `$ORIGIN` as configured by `install_rpath`.
This is expected Meson build/install behavior, not a required source patch.
The full provider ABI audit is still pending. No engine device run is claimed.
Follow [Knight Blade progress](KNIGHT_BLADE_ROADMAP.md) for the next milestone.
