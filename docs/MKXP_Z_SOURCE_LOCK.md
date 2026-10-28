# mkxp-z source and dependency lock for the minimal H700 profile

2026-10-28 · Refs #5 · Stacked on the #6 runtime branch (PR #32); no merge.

## Result

| Result | Level | Check |
| --- | --- | --- |
| PASS | verified-on-host | mkxp-z `37a04d14413454551a7b6aadbb4e93e67168accb` fetched by exact commit; `git rev-parse HEAD` matches. Upstream `HEAD` equalled this commit on 2026-10-28 |
| PASS | verified-on-host | All 56 Meson wraps classified: 22 selected, 34 explicitly excluded ([profile](../build/h700-engine/mkxp-z-profile.json)) |
| PASS | verified-on-host | [Lock](../build/h700-engine/mkxp-z-lock.json) `LOCK_COMPLETE`: 21 HTTPS archives with wrap SHA-256, 1 git wrap at an immutable commit plus 17 recursive submodule commits, every patch file and patch-directory digest |
| PASS | verified-on-host | All 21 archives downloaded into a private Meson packagecache (outside Git), verified while streaming and re-verified afterwards. 409 MiB used, 30 GiB still free (26-GiB stop guard respected) |
| NOT_PERFORMED | — | License/grant review of the selected closure (#3); embedded-asset review |
| NOT_ATTEMPTED | — | Meson configure, compile, link, device execution |

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

## Next step

Write a Meson cross file for `aarch64-nextui-linux-gnu` (pinned GCC 8.3 and
sysroot, private Mali SDL prefix via a dedicated pkg-config directory, native
Ruby 3.1.3 as `baseruby`). Then run `meson setup --wrap-mode=nodownload`
against this packagecache in the offline container. Configure failures are
the next evidence; nothing has been compiled yet.
