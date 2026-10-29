# External sources and M0 provenance audit

Audited **2026-10-25**, for [issue #3](https://github.com/almighty-atlas/nextui-mkxp/issues/3).
**STATIC only. GO for further source research; BLOCKED for R36S code import,
engine release or claims of legal clearance.** No upstream implementation or
binary is included in this change. Read the [distribution gate](DISTRIBUTION_GATE.md)
and [command evidence](audit/ISSUE-003-EVIDENCE.md) before later build work.

## Immutable audit baselines

| Source | Inspected revision | Evidence and meaning |
| --- | --- | --- |
| This repository `main` | `fa081c9` (full SHA in evidence) | Documentation-only baseline; no engine, dependencies, license for original implementation, or CI existed |
| [mkxp-z](https://github.com/mkxp-z/mkxp-z/tree/37a04d14413454551a7b6aadbb4e93e67168accb) | `37a04d14413454551a7b6aadbb4e93e67168accb` | Research pin, **not** a selected H700 build version |
| [R36S port](https://github.com/Periko21/mkxp-z-r36s/tree/b665091c1ff571a7a468bbf33af2f7c803c75220) | `b665091c1ff571a7a468bbf33af2f7c803c75220` | Separate scripts/patches repository; no immutable engine revision for its released executable established |

The machine-readable [inventory](audit/source-inventory.json) records all **56**
mkxp-z dependency wraps (including non-Linux/optional candidates), all **138**
wrap patch references with locally computed hashes, and **24** R36S tracked
files with hashes, last-change commits/authors, terms claims and import status.
It preserves exact source URLs, declared archive checksums/revisions and wrapdb
patch archive checksums. Archive checksums were **not verified by downloading**
those archives. `UNKNOWN` is an explicit unresolved license/revision, not approval.
The JSON is an audit snapshot, not a resolved dependency graph or release SBOM.

## Engine and critical dependencies

Each license is scoped to the identified source, not a blanket grant for every
bundled file. The primary texts below were read; archive identity and complete
file-level coverage still need review before building a release.

| Component / revision | SPDX / evidence | Conservative obligations / status |
| --- | --- | --- |
| mkxp-z at audit pin, upstream project version 2.4.2 | `GPL-2.0-or-later`: [main.cpp grant](https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/main.cpp), [COPYING](https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/COPYING), [README](https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/README.md) | Preserve Ancurio/Amaryllis Kulla and other contributors' notices, mark modifications, provide complete corresponding source under applicable GPL version; inspect embedded exceptions below |
| OpenAL Soft 1.24.3 | `LGPL-2.0-or-later`: [grant](https://github.com/kcat/openal-soft/blob/1.24.3/al/buffer.cpp), [COPYING](https://github.com/kcat/openal-soft/blob/1.24.3/COPYING) | Library source, notices, modifications, and usable replacement/relinking route; static linkage requires concrete link materials or fully verified source rebuild route; no H700 link choice yet |
| FluidSynth 2.5.0 | `LGPL-2.1-or-later`: [grant](https://github.com/FluidSynth/fluidsynth/blob/v2.5.0/src/synth/fluid_synth.c), [LICENSE](https://github.com/FluidSynth/fluidsynth/blob/v2.5.0/LICENSE) | Same relinking review; separately inventory enabled GLib, libinstpatch, codecs/backends and any soundfont; no soundfont approved |
| Ruby 3.1.3 + mkxp-z patches | `Ruby OR BSD-2-Clause`: [COPYING](https://github.com/ruby/ruby/blob/v3_1_3/COPYING), [patch list](https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/subprojects/ruby-3.1.wrap) | Select/document a permitted branch; retain copyright, license and disclaimer. Audit every extension, stdlib/gem and patch separately. Ruby core terms do not clear OpenSSL, libyaml, zlib or other extensions |
| SDL2 2.28.1 | `Zlib`: [LICENSE.txt](https://github.com/libsdl-org/SDL/blob/release-2.28.1/LICENSE.txt), [wrap + local changes](https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/subprojects/sdl2.wrap) | Retain notice in source; mark altered sources and do not misrepresent origin; preserve author attribution. SDL license does not clear every codec/backend or R36S patch |
| Optional OpenSSL 3.0.8 | `Apache-2.0`: [LICENSE.txt](https://github.com/openssl/openssl/blob/openssl-3.0.8/LICENSE.txt), [pinned wrap](https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/subprojects/openssl.wrap) | Preserve license, applicable notices/NOTICE and change notices; review GPLv3 combination and patents. Version is provenance evidence, **not a security recommendation** |

These links use upstream tags for dependency license texts; the wrap's archive
SHA-256 pins its intended bytes. Resolve tags to commits and verify matching
archive contents in the later lockfile; no claim that a mutable tag is immutable.

## Other source, dependency and embedded-content inventory

All unverified SPDX entries in JSON remain `UNKNOWN`; the following R36S license
claims are leads only, sourced from its [NOTICE](https://github.com/Periko21/mkxp-z-r36s/blob/b665091c1ff571a7a468bbf33af2f7c803c75220/NOTICE.md).
The current Meson pins below must not be assigned to the historical R36S binary.
Exact URLs/checksums/patches for wraps are in JSON.

| Component / candidate revision | License evidence / unresolved obligation |
| --- | --- |
| SDL_image release-2.6.3, SDL_ttf release-2.0.18, SDL_sound 2.0.4 | R36S claims Zlib; inspect each actual fork/release and nested codecs. SDL_image wrap recursively clones submodules: record every gitlink and notice before enabling. R36S instead uses `mkxp-z/SDL_image` branch `mkxp-z` |
| FreeType VER-2-14-3 | R36S claims `FTL OR GPL-2.0-only`; validate actual package/options and choose branch (FTL has binary documentation attribution). Do not infer terms of bundled compression/font code |
| PhysicsFS 3.2.0; Pixman 0.46.4; uchardet 0.0.8 | R36S claims Zlib, MIT and MPL/GPL/LGPL alternatives respectively. File-level tri-license election and compatibility unresolved |
| Ogg 1.3.6; Vorbis 1.3.7; Theora 1.2.0; theoraplay `ec1aad1ee43592f216946cdc03b1ee4c4e1e2e59` | R36S claims BSD-3-Clause for Xiph codecs; theoraplay requires independent notice review. Preserve actual copyright/conditions/disclaimers |
| zlib 1.3.1; libpng/JPEG via SDL_image; R36S bzip2 1.0.8 | R36S says respective permissive licenses. Nested codec revisions not resolved. No libpng/bzip2 top-level wrap at current engine pin; do not invent one |
| GLib 2.84.1, libffi 3.5.2, libyaml 0.2.5, fmt 12.1.0, xxHash 0.8.3, gcem 1.18.0 | Additional candidates visible in current wraps; exact enabled graph and license texts not audited. BLOCKED if selected until resolved |
| ALSA, libdrm, Mesa/GBM/EGL/GLES, glibc, loader, input headers | Runtime/system/build-only distinction pending exact H700 sysroot; R36S uses ALSA 1.2.11 and development stubs. Header/stub use and `dlopen` do not automatically waive all obligations; no driver/sysroot binaries approved for shipping |
| GCC `libstdc++`, `libgomp`, `libgcc_s` | R36S claims `GPL-3.0-or-later WITH GCC-exception-3.1`. Exact toolchain package/source versions UNKNOWN; assess eligible compilation process and preserve notices/exception before redistributing |
| `src/filesystem/ghc/*` | In-tree MIT grant names Steffen Schümann; [file evidence](https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/filesystem/ghc/filesystem.hpp). Preserve full MIT notice; original component revision UNKNOWN |
| `src/display/libnsgif/*` | MIT headers name Richard Wilson, Sean Fox, Michael Drake, James Bursa/John Tytgat; [evidence](https://github.com/mkxp-z/mkxp-z/tree/37a04d14413454551a7b6aadbb4e93e67168accb/src/display/libnsgif). Resolve original revision/full notice |
| `src/util/rapidcsv.h`, `json5pp.hpp`, other embedded headers | rapidcsv header claims BSD-3-Clause (Kristofer Berggren); remaining exact notices and original revisions require full file review. Root GPL alone is insufficient |
| `assets/liberation.ttf`, `wqymicrohei.ttf`, `icon.png`, `gamecontrollerdb.txt` | Embedded by [assets/meson.build](https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/assets/meson.build). R36S claims OFL-1.1 for Liberation Sans; exact font release/notice and icon/database rights UNKNOWN. CJK font optional, default off; independently review or omit/replace before release |
| Shaders; optional ANGLE/Vulkan; Steamworks | [shader build](https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/shader/meson.build) marks xBRZ GPLv3; extra shaders default auto. ANGLE Vulkan also sets a GPLv3 feature. Review individual shader/ANGLE terms, not only HTTPS. Steamworks SDK is excluded; no SDK files approved |

## R36S patch and original-file review

The [file inventory](audit/source-inventory.json) has an entry for **every tracked
R36S file**, rather than treating NOTICE as a grant for all files. Git attributes
all observed commits to **Pere**; commit authorship is evidence, not proof of
copyright ownership. Root `LICENSE` is the GPLv2 text; README/NOTICE explicitly
say GPLv2+ for mkxp-z/exitwatch. Many scripts and standalone diffs have no separate
grant or author header. Confirm scope and any third-party contributions with a
human before import. In particular do not silently relicense SDL patches as Zlib.

| Candidate | Modified target / origin | Decision and required follow-up |
| --- | --- | --- |
| `patches/0001-sdl2-kmsdrm-async-pageflip-fallback.patch` | SDL `SDL_kmsdrmopengles.c`; retry rejected async page flip | Reference only; confirm patch author's license, exact SDL base and [reported issue #16174](https://github.com/libsdl-org/SDL/issues/16174) provenance; report is not a license grant |
| `0002-sdl2-kmsdrm-honour-double-buffer-hint.patch` | SDL `SDL_kmsdrmvideo.c`; double-buffer hint | Reference only; same license/base review |
| `0003-mkxpz-nintendo-face-buttons.patch` | mkxp-z `src/input/keybindings.cpp`; face-button mapping | Reference only; verify original GPL notice and contributor grant; H700 mapping untested |
| `0004-mkxpz-optional-verbose-sdl-logging.patch` | mkxp-z `src/main.cpp`; opt-in SDL logging | Reference only; same grant/base review |
| `0005-mkxpz-cross-build-adjustments.patch` | `linux/Makefile`, `src/meson.build`, root `meson.build` | Reference only; build/codec/backend/iconv/rpath edits; script mutations are additional inputs, not all captured by this diff |
| `build/03-source-and-patches.sh` | Inline target/Makefile/Meson/input/logging edits, pixman/uchardet/zlib/bzip2 substitutes, forked SDL/SDL_image | Not a pinned recipe: clones engine HEAD, SDL branch `mkxp-z-2.28.1`, SDL_image branch `mkxp-z`; downloads without checksum verification. Historical engine/dependency SHAs UNKNOWN |
| `build/patch-kmsdrm.py` | Applies SDL edits procedurally | Compare to patches 0001/0002 after identifying base; do not assume byte-equivalence or apply both |
| `build/04-build-deps.sh` | libpng configure/prebuilt header workaround; clears Ruby bundled gems, flattens DESTDIR; backend flags | Record all generated/source mutations, extension inventory, exact dependency sources and commands before reuse |
| `build/01-host-toolchain.sh`, `02-gpu-stubs.sh`, `target-armv7old.sh` | Host apt/toolchain/symlinks, graphics headers/stubs, ARM32 target | Not run. Unpinned apt packages/Khronos main header and host-wide changes are unsuitable inputs for this H700 audit |
| `build/05-build-and-package.sh`, `build/exitwatch.c` | Engine/ARM32 libraries/helper/zip | Not run. Script copies binaries but has no explicit license/NOTICE/source/relink-kit copy steps; cannot establish contents/compliance of any published zip without separately inspecting it |
| `launcher.sh`, `build/launcher.sh`, `infinite-fusion/PokemonInfiniteFusion.sh`, `tools/*`, both `mkxp.json` files | Original launcher/helper/configuration candidates | Reference only; confirm grants per file, no blind copying. zram/sysctl/clock/save-moving behavior outside this issue and not authorized for adoption |

## Linking and legal interpretation requiring review

- **GPL source delivery:** GPLv2 §§1–3 and GPLv3 §§4–6 require the appropriate
  notices, modified-file notices and complete corresponding source when conveying
  covered binaries. Prefer accompanying exact source to relying on an upstream
  URL or an unplanned written offer. Include scripts controlling compilation and
  installation, interface definitions, local patches and necessary non-system
  linked components. A git SHA alone is not source delivery.
- **Static LGPL:** [OpenAL LGPLv2 §6](https://github.com/kcat/openal-soft/blob/1.24.3/COPYING)
  and [FluidSynth LGPLv2.1 §6](https://github.com/FluidSynth/fluidsynth/blob/v2.5.0/LICENSE)
  require a usable route to modify the library and relink. Supply complete library
  source/changes and executable link materials (objects/archives, link order,
  flags, toolchain instructions) or a verified full source route satisfying the
  selected license. A GPL source rebuild can supply the application side, but
  an unpinned script or source URL is not proof it works. Preserve the user's
  modification/reverse-engineering rights required by the selected terms.
- **Dynamic LGPL:** A suitable shared-library mechanism can avoid supplying
  application relink objects under §6(b), if it actually works with a compatible
  modified library. Still provide required library source/notices and preserve
  replacement rights; test replacement paths. Dynamic linking does not remove
  mkxp-z's GPL obligations or clear bundled dependencies.
- **HTTPS/OpenSSL:** Apache-2.0 is incompatible with GPLv2-only combinations;
  mkxp-z's later-version permission provides a potential GPLv3 route, subject
  to reviewing all combined code. See [GNU compatibility guidance](https://www.gnu.org/licenses/license-list.html#apache2).
  Current option is `openssl` (`auto`), not historical `enable-https`. Disabling
  HTTPS alone does **not** establish a GPLv2-only result: extra shaders and ANGLE
  Vulkan can also trigger GPLv3. Ruby extensions must also be checked. Record
  actual configuration/link closure and license election; do not invent an
  OpenSSL linking exception.
- **Separate files:** Ruby, fonts, runtime libraries and helpers retain their
  terms; packaging them together does not erase their obligations. Review whether
  any GPLv3 installation-information requirement applies to the actual delivery
  arrangement (§6); do not assume it always applies or never applies to a Pak.

These are conservative engineering gates, not a legal opinion. All unresolved
rights, compatibility choices and release sign-off require human review.

## NextUI and target references

[Official NextUI docs](https://nextui.loveretro.games/docs/),
[PAKS.md](https://github.com/LoveRetro/NextUI/blob/main/PAKS.md),
[LoveRetro/NextUI](https://github.com/LoveRetro/NextUI) and
[historical pvaibhav port](https://github.com/pvaibhav/NextUI) remain research
references, not imported dependencies. NextUI has advertised PolyForm
Noncommercial terms; no pinned file-level NextUI license audit was performed in
#3. Pin and review any actual files before reuse; using the Pak interface does
not authorize redistributing firmware code. No H700 behavior was tested here.
