# Minimal mkxp-z startup on H700 — implementation plan

2026-10-27. **PLAN ONLY; no engine implementation, source import, new cross-build
or device change in this update.** Attached to Issue #22 / PR #30 as the next-step
assessment after the [limited video PASS](H700_VIDEO_EVIDENCE.md), not an attempt
to implement or close #4–#7 in this PR. Binary publication remains BLOCKED by
[PR #19](https://github.com/almighty-atlas/nextui-mkxp/pull/19).

## 1. Inspected baseline and issue ordering

- Local main `107db135b8e8ef72f6d61c78be14416330727b0d`; PR #30 preparation
  `6c41ad73a4ccab077a68512a2daae830f895b50c`. The tree contains planning docs and
  `spikes/h700-stock-video/{prepare.py,test_prepare.py,evidence.json,README.md}`;
  **no engine checkout, engine build system or engine test project**.
- Read README, AGENTS, architecture, roadmap, test/compatibility/source docs;
  open issue bodies and open PR list, PR #30/#27/#19 and reviews; PR #21 ADR and
  PR #19 distribution gate/inventory. These PRs remain separate/unmerged.
- #1: hardware/firmware baseline incomplete (exact firmware identity for this
  trial missing). #2: standalone architecture/discovery proposed in PR #21,
  not an approved/implemented engine Pak. #3: rights gate in PR #19 unresolved.
- #22: one original game-free video/lifecycle trial passes, not full engine
  readiness. #24/#26: toolchain and Linux-4.9 source-build research; successful
  PR #27 host evidence must not be discarded or rerun merely to repeat history.
- #4 depends on #1/#2/#3: next **bounded source/static preparation**, conditional
  on those reviews before real build use. #5 depends on #4; #6 on #5; #7 on #6.
  #8/#10/#11 (discovery, controls, saves) and #12–#17 (games/releases) stay later.
  #9 offline guard work is complementary; do not silently implement it here.

The video result removes a narrow feasibility unknown: the used SDL `mali`
path can produce visible shader animation and return normally on this device.
It does not provide a reusable engine dependency closure, firmware fingerprint,
license clearance or cross-host reproducibility. The current Alpine host's
pinned glibc-host compiler still cannot start natively; no compatible host/container
has been provisioned. Source/static work can proceed without solving that here.

## 2. Source-grounded engine configuration and dependency budget

Research candidate: mkxp-z **2.4.2**, immutable commit
`37a04d14413454551a7b6aadbb4e93e67168accb` from PR #19, not latest main.
Read upstream [meson.build][M], [options][O], [src/meson.build][D],
[main.cpp][I], [binding][B] and [embedded assets][A]. These are research
citations, not vendored code or evidence of a successful configure/build.

| Layer | Minimum plan / hard constraint |
| --- | --- |
| Native build tools | Pin trusted x86_64 glibc host tool inventory (or separately reviewed rootless image digest), Python, Meson >=1.4, Ninja, CMake and GNU source-build tools. No floating image, sudo or paid service |
| Cross compiler/sysroot | Reuse PR #27 pins: GCC 8.3 recipe `d37268f5160ec6cd4da541524c8111797e060c36`, archive SHA-256 `d4ac4ef1968668f93f625f2b226c69d74739ae58ff640d2ce3aaae6b4d1b93d3`; complete glibc 2.28 with Linux-4.9.170 headers / minimum kernel 4.9.0. Never revert to SDK's kernel-4.19 sysroot |
| C++ runtime | New gate: real C++14 compile/link, libstdc++/libgcc closure, GLIBCXX/CXXABI and transitive GLIBC version requirements. The C triangle proves none of these. Do not assume firmware provides compatible libstdc++ |
| SDL2 + graphics | Prefer shared SDL ABI from the pinned Mali fork `d4a7d7503524cc469fe775242f3f925d4dd56c88` / H700 patch recipe `04faa348c112617fc6b99be62308099ee6d43581` for private build inputs, installed SDL at runtime. Confirm **all engine** imports, not only the triangle's 21. Resolve GL via SDL; no vendor import DSO, direct vendor link or software substitute |
| Ruby/RGSS | Candidate MRI 3.1 (upstream wrap 3.1.3), libffi, libyaml, zlib, iconv; separate host Ruby/build generators from AArch64 libruby/configuration. Pin every helper/patch and prohibit target configure execution. No proprietary RGSS DLL |
| Graphics/files/text | PhysicsFS, SDL_image + reviewed PNG/JPEG closure, SDL_ttf + FreeType, pixman, uchardet, GL headers and header-only helpers. Inventory exact enabled sources. Current upstream SDL_image fallback also enables JXL/Brotli/Highway: do not assume PNG-only without a reviewed build profile/patch |
| Sound/video decode | OpenAL Soft (+ fmt where selected), SDL_sound, Ogg/Vorbis, Theora/TheoraPlay, FluidSynth (+ gcem and actual transitive closure) are requested by this source. Retain required link dependencies even for a silent smoke. No invented `audio=disabled` engine option |
| Assets | Upstream embeds icon.png, gamecontrollerdb.txt and liberation.ttf by default; CJK option selects another font. Audit file-specific rights/notices before copying/building; no game/RTP/font substitution of unknown provenance |

Candidate Meson profile, **not an executed or complete build command**:

```text
-Dgfx_backend=gles -Dforce32=false -Dworkdir_current=true -Dmri_version=3.1
-Dsdl_system=enabled -Dangle=disabled -Dopenssl=disabled
-Dextra_shaders=disabled -Duse_miniffi=false -Dcjk_fallback_font=false
-Dalsa=disabled -Djack=disabled -Doss=disabled
-Dpipewire=disabled -Dpulseaudio=disabled
--wrap-mode=nodownload
```

Here `sdl_system=enabled` means the **private target prefix**, never host SDL.
`PKG_CONFIG_LIBDIR`/sysroot and cross/native machine files must make that explicit.
Upstream defaults prefer static vendored libraries; do not inherit uncontrolled
fallbacks or host packages. Preseed and hash all actually selected wrap sources,
patch archives, nested sources and generators; `nodownload` alone does not stop
arbitrary sub-build download commands. Audit those separately. Missing inputs
must fail before configure, without network access or target emulation.

Silent first startup should use a pinned OpenAL Soft null backend if its source
supports it; confirm that backend and selection before claiming viability.
`main.cpp` opens an OpenAL device and the RGSS thread creates an AL context before
script execution: disabling ALSA alone is **not** enough to skip audio init.
Real ALSA sound is a separate #7 stage. No dummy replacement library.

Use `customScript` with `rgssVersion=1` for a later original Ruby fixture rather
than distributing a game's Scripts archive. The binding has an actual custom
script branch. Confirm configuration/no-Game.ini behavior on the pinned source
before defining the fixture layout. This avoids assuming undocumented command-line
game-selection or a `--version` path initializes the engine.

## 3. First milestone: offline input contract + C++ ABI calibration (#4 slice)

**Small deliverable:** a reviewed build-input manifest, fail-closed offline
preflight and tiny original C++14 executable; **no mkxp-z build or Pak yet**.
This is preferable to importing a complete engine/dependency graph now.

Proposed files for a **later, separate #4 branch/PR** from then-current main:

1. `build/h700-engine/inputs.json`: immutable engine/tool/helper/source pins,
   checksums, patch order, licenses/notices, build-only vs link vs runtime roles,
   enabled/excluded feature list and explicit unresolved entries. Seed from the
   existing PR #19 inventory / PR #27 lock by reviewed selection, not branch merge
   or wholesale copying. Unknown required input = BLOCKED, not placeholder PASS.
2. `build/h700-engine/{cross.ini.in,native.ini.in}`: AArch64/Linux/little-endian,
   absolute reviewed tools/sysroot/private prefix, `needs_exe_wrapper=true`, no
   executable wrapper or QEMU. Restrict pkg-config to target prefix; clean child
   env excludes host include/lib overrides. Record actual include/link search.
3. `scripts/check_h700_engine_inputs.py`: standard-library-only offline checker;
   reads explicit cache/manifest, checks bytes before extraction, rejects unsafe
   paths/symlink escapes, missing/changed inputs, moving refs and unreviewed
   patches; emits bounded deterministic JSON of first blockers. Never fetches,
   runs configure, ARM, device probes or deploys. A receipt is not build attestation.
4. `tests/test_h700_engine_inputs.py`: synthetic source/metadata fixtures clearly
   labelled as such, positive case and negative cases for checksum mutation,
   missing cache, unsafe archive members, absent license, host path contamination,
   wrong triple/kernel floor, unresolved profile and blocked distribution state.
5. `spikes/h700-cxx-abi/probe.cpp` + small host build driver: original exception /
   `std::string` / allocation exercise to force actual C++ runtime linkage. Build
   and execute **native host** variant offline where tools exist. Cross-build
   privately only after tool/input reviews on a capable host; inspect but never
   run target. This calibration is deliberately not an SDL or engine test.

Acceptance: local offline unit tests run with no third-party Python packages;
valid fixture passes and every rejection fails deterministically; native C++14
probe compiles/runs; genuine cross-probe (when available) records full tool/source
receipt, ELF hash/link map, architecture, interpreter, GNU ABI, NEEDED, versioned
imports, stack and path policy. Target symbols must map to reviewed providers;
GLIBCXX/CXXABI/libgcc/libc availability cannot be invented from the triangle.
Keep target output private and distribution BLOCKED. No genuine cross inputs here
means **cross-probe BLOCKED**, not synthetic metadata promoted to real evidence.

Safe unit tests should run automatically in that follow-up's pinned read-only CI
after checkout, with the full PR-base-to-head diff checked and no artifact upload.
If workflow-write permissions still block CI, report it; do not weaken token
permissions or call local results verified-in-CI. Native probe needs a pinned
available compiler; absence is explicit BLOCKED, not a silent test skip/PASS.

## 4. Subsequent bounded stages, each with a stop condition

| Stage / issue | Concrete output and acceptance | STOP condition |
| --- | --- | --- |
| Dependency closure / #4 | Preseed reviewed sources; private offline target prefix, dependency graph/licenses, native-vs-target Ruby helper audit, exact compiler/link search and build receipts | Missing hash/grant, network fallback, host object/library or required target execution; no speculative workaround |
| First engine link / #5 | Pinned mkxp-z with profile above, private AArch64 executable and map; repeat link and document bytes. No SDL fallback to generic KMSDRM, no vendor binary bundled | Unsupported dependency/configuration; report exact first failing command/symbol. Same-workspace repeat is not cross-host reproducibility |
| Static engine ABI / #6 | Inspect engine and every required DSO using host readelf, no target ldd: ELF64 LE AArch64, `/lib/ld-linux-aarch64.so.1`, kernel floor <=4.9.170, GLIBC/GLIBCXX/CXXABI providers, NEEDED + dlopen closure, no private paths/TEXTREL/executable stack | Unreviewed provider/library version or packaging rights. Do not reuse triangle's exact two-NEEDED/21-import validator as engine policy; upstream currently sets `$ORIGIN` RPATH, which needs explicit package policy/review or a narrow build patch |
| Asset-free startup / #7, host first | Original custom Ruby script creates procedural colored bitmap/sprite, calls Graphics.update for a bounded loop then disposes/exits; no text/audio/media/game assets needed for content, though engine embedded assets still need review. Native host smoke validates script/init/teardown with explicit mock/headless limits | Null OpenAL unavailable, missing GL features/fonts/init, unbounded failure handling; no claim of Mali behavior from host |
| Future single H700 engine trial / #7 | Only after rights/ABI/package review and separate exact-hash owner approval: physical NextUI launch, sanitized engine stages, visible procedural output and responsive return. Record exact firmware. Retain guards until that approval; restore SOURCE_ONLY/hash after trial | Any loader/backend/return failure; stop, no automatic driver/firmware/permission repair. Five-second script loop cannot bound stuck driver/Ruby/native calls |

Later #7 must test actual audio/input deliberately; the silent/null-backend
fixture does not complete those criteria. #8/#10/#11 then address game selection,
safe paths, controls/exit chord, per-game configuration and saves, without writing
into engine bundle or modifying existing games. No NextUI save states, standard
in-game menu, game switcher or instant resume is promised. Games, performance,
memory tuning and releases are not in this minimal-start milestone.

## 5. Exact next implementation action

**Create the separate #4 input-contract follow-up** (after prerequisite review),
starting with `inputs.json` and a standard-library offline validator plus negative
fixture tests. Make unresolved engine dependency hashes/licenses/C++ providers
first-class BLOCKED results; do not fetch/build mkxp-z yet. Then add the native
C++14 calibration to that bounded milestone. This PR only documents that plan.
No further handheld action is required. The licensing/source/relinking review,
exact firmware identity, build host availability and expanded runtime closure
remain independent gates, not regressions of the successful triangle trial.

[M]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/meson.build
[O]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/meson_options.txt
[D]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/meson.build
[I]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/main.cpp
[B]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/binding/binding-mri.cpp
[A]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/assets/meson.build
