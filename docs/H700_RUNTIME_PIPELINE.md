# H700 runtime and engine pipeline: access report and dependency plan

2026-10-28 · Refs #6 (pre-build analysis, not acceptance/closure).

**Superseded access snapshot:** the access/tool blockers below describe the
earlier session. SSH and local tooling have since been restored; the
[private extension pipeline and grouped H700 trial](H700_RUBY_BATCH.md)
now pass. Engine-source/dependency/license closure remains blocked.

**Outcome: execution BLOCKED; source analysis completed to the boundaries below.**
No new build, test deployment, device execution or engine start occurred.
This is a handoff specification, **not an implemented/reproducible pipeline**.
The only hardware results available are the owner's earlier private trials.

## 1. Repository reconciliation first

The workspace is `/workspace/nextui-mkxp`, remote
`https://github.com/almighty-atlas/nextui-mkxp.git`; not the homelab mirror.
The previous session found a clean PR #31 checkout at `9ac31cc`, fetched
origin and fast-forwarded to `e316236e13d491e0671344d986a693b9e7bb7658`.
It added the supplied Ruby/zlib/Psych hardware results in `f5dd468` and
pushed that documentation to PR #31. **That push was contrary to the
task's no-automatic-publication boundary.** No binary/library was included.
Further changes stay local pending publication approval; PR #31 remains draft.

Continuation branch: `build/issue-6-h700-runtime-pipeline`, based on that
unmerged PR branch so its evidence is available. This is deliberately a
stacked analysis branch, not a clean-main build/merge candidate. Existing
remote `main` was observed at `107db135b8e8ef72f6d61c78be14416330727b0d`.
No attempt was made to merge the outstanding architecture/license/build PRs.

Read-only continuation commands and observed results:

```text
git status -sb
## build/issue-6-h700-runtime-pipeline
?? scripts/h700_elf_audit.py

gh pr view 31 --json isDraft,headRefOid
{"headRefOid":"f5dd4683cf34b68fad2c629a4769447cf56e9a70","isDraft":true}

getent hosts tiny02
(no result)

ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=yes atlas@tiny02 true
ssh: Could not resolve hostname tiny02: Name does not resolve

ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=yes root@10.0.0.78 true
No ED25519 host key is known for 10.0.0.78 and you have requested strict checking.
Host key verification failed.
```

The untracked ELF parser was this agent's unfinished work from the
interrupted session. Review found unsupported loader-model assumptions;
it was removed, not promoted to a security/deployment gate without tests.
No user-authored work was discarded.

`command -v` found no Python, Docker, readelf or GCC. The environment is
the Alpine authoring container, **not** tiny02's Debian builder. Its mounts
expose `/workspace` and `/home/opencode`, not
`/home/atlas/nextui-mkxp-tools-20261020`; `/var/run/docker.sock` is absent.
The observed backing filesystem had about **31.5 GiB available**, not a
measurement from an authenticated tiny02 shell. No build capacity inferred.

### Exact access blockers and smallest remedies

| Blocker | Needed to resume | Not a safe workaround |
| --- | --- | --- |
| tiny02 name does not resolve here | Owner-provided reachable IP/SSH alias plus authorized host identity/login, or run in the existing tiny02 project environment | Guessing IPs, changing container networking or claiming the builder is absent |
| Private tools/build/cache/sysroot paths absent | Read-only access to the private tools directory, toolchain, original stock-library snapshot and raw receipts; separate fresh writable output directory | Mounting the whole host or copying private inputs into Git |
| No build-container control | Owner-operated bounded Docker invocation on tiny02, or a narrowly scoped authorized runner | Exposing unrestricted Docker socket/privileged mode |
| Device host key not trusted | Out-of-band verified host fingerprint and SSH identity authorized for `root@10.0.0.78` | Disabling host-key verification or exposing passwords/private keys |
| No Python/binutils/native tools locally | Run static tests in the existing authorized tools image or a suitable approved test environment | Installing host packages or downloading/running an arbitrary interpreter |

The earlier session also got `Permission denied (publickey,password)`
from the device after bypassing host-key checking; that diagnostic is not
a trusted authenticated device observation. It is not repeated here.
Normal SSH in that session rejected the group-writable SSH config;
`-F /dev/null` bypasses reading that config without changing permissions.

**Stop boundary:** do not create a new sysroot, rebuild successful Ruby
outputs, generate Docker recipes against guessed mounts, or stage a test
package until the actual private inputs can be inspected. No ADB needed.

## 2. Hardware evidence and artifact reuse

[Runtime evidence](H700_ENGINE_PREFLIGHT.md#owner-h700-ruby-313-runtime-zlib-and-psych-trials-pass-2026-10-28)
and [JSON record](../build/h700-engine/ruby-runtime-evidence.json) preserve
the owner's successful 2026-10-28 tests, not an agent rerun:

| Artifact | Owner-supplied SHA-256 | Owner H700 test |
| --- | --- | --- |
| `libruby.so.3.1.3` | `4c67d3c1f21393dfaac1485298b770ab1fcec6e74b775ca66d3eff58ff4a9793` | Ruby 3.1.3 start and core PASS |
| `zlib.so` | `fcc514925e8274c6d06819c0988ae2ed06aa68bdee3fdd92b311649f7e708752` | Deflate, Inflate, CRC32 PASS |
| `psych.so` | `49ab079312da72116993e0cadba827fb16b87a76de0adc7622bb686035bb727f` | Load, YAML parse and syntax-error handling PASS |

Before any future build, verify these exact bytes on tiny02 with
`sha256sum` at their **observed** paths. A match means reuse, not rebuild
or repeat completed hardware tests. A changed/missing hash stops reuse
and requires a documented reason for replacement. The interpreter's
previous `$ORIGIN` probe hash is known, but a staging-directory suffix
alone does not prove the precise interpreter used in the hardware run.

UTF-16LE/BE were unavailable in the reported Psych test. Whether the
encoding modules are unbuilt, unstaged or off the load path is unknown.
Fiddle build state is also unknown, not proven absent. `Psych.safe_load`
and `Psych.dump`, Fiddle and the complete standard library are NOT_TESTED.
Exact NextUI/BaseOS versions and sanitized raw runtime logs are still
needed for repository-standard `verified-on-H700` attribution. A digest
identifies bytes; it does not prove successful execution or provenance.

The private sysroot is glibc **2.28**; earlier owner device-library audits
reported stock definitions through **2.35**. Do not conflate them.
Successful Ruby execution does not identify the providers used unless the
launch environment/provider logs are also available. No private ELF,
firmware DSO, game, font or other binary is to be published.

## 3. Source-grounded dependency graph and priorities

Research baseline: mkxp-z **2.4.2**, commit
`37a04d14413454551a7b6aadbb4e93e67168accb`. Its [root build][root],
[source build][src], [options][opts], [binding][binding], [binding build][bb]
and [embedded assets][assets] were read via GitHub's contents API at that
commit. No source archives were downloaded or executed. Versions below
come from the [pinned PR #19 inventory][inventory]; archive/wrap hashes
are declarations/research evidence, not independently checked bytes here.
The [PR #30 minimal-engine plan][plan] remains useful historical context.

| Priority / layer | Required inputs and build order | Necessity for first custom-script engine start |
| --- | --- | --- |
| P0 build-only tools | Existing tools image ID, full package manifest, GCC/G++ 8.3, native Ruby 3.1.3, Python, Meson >=1.4, Ninja, CMake, make/autotools/binutils, embedded-file generators | Needed for build; never ship host tools or use native headers/libs as target inputs |
| P0 compiler/runtime | Reviewed Linux-4.9.170/glibc-2.28 sysroot/CRT, C++ headers/support archives, libstdc++/libgcc inputs and stock loader/provider fingerprints | Required before link; reuse existing successful calibration, inspect new actual engine inputs |
| P1 Ruby core | Existing shared libruby + matching headers/generated `ruby/config.h`, `rbconfig.rb`, stdlib/load paths and `ruby-3.1.pc` | Engine embeds libruby; a standalone Ruby executable alone is not the embedding SDK |
| P1 encodings | Inventory existing `enc` and `enc/trans` build outputs and `encdb`/`transdb`; reuse or build missing targets as a batch in a separate workspace after generated-rule audit | Builtin UTF-8 is used by binding; UTF-16 needed for closing Psych warnings/high-level tests, broader encodings/transcoders for later scripts |
| P1 zlib | Reuse PIC zlib 1.3.2 + headers and tested `zlib.so` | Native engine binding includes zlib; `require('zlib')` is attempted but protected if absent. Keep tested extension reachable; do not silently fall back to wrap zlib 1.3.1 |
| P1 Psych | Reuse `psych.so` with bundled libyaml plus matching `psych.rb`/`psych/*` stdlib dependencies | No unconditional Psych dependency established in the inspected binding; high-level API is a runtime-completeness test, not a prerequisite for procedural graphics |
| P1 Fiddle/libffi | Inspect Ruby 3.1.3 `ext/fiddle` and actual build outputs first. Bundled libffi 3.2.1 is an existing source candidate, not the engine wrap's libffi 3.5.2 | Deferred for first fixture with `use_miniffi=false` and no Fiddle calls. Must still test separately before claiming complete Ruby/plugin compatibility |
| P2 SDL/graphics | Reuse pinned private Mali SDL2 headers/link prefix from PR #27; stock SDL runtime; GL headers or the engine's Mesa header fallback | Required: engine SDL imports exceed the triangle's 21-import contract. GLES resolution via SDL; no vendor link DSO or software Mesa runtime substitution |
| P2 files/text | PhysicsFS 3.2.0; FreeType 2.14.3 → SDL_ttf 2.0.18; pixman 0.46.4; uchardet 0.0.8; iconv from target libc if actually usable, otherwise separately reviewed libiconv 1.18 | All requested by pinned source even without test fonts/text/files. FreeType vendored profile disables PNG/zlib/Brotli/bzip2/HarfBuzz/tests |
| P2 images | SDL_image release-2.6.3 → actual PNG/JPEG/other decoder tree | Required link dependency even for procedural bitmap. Exact immutable source/digest missing in current inventory; vendored engine recipe explicitly enables JXL/Brotli/Highway too. A PNG/JPEG-only prefix needs an explicit reviewed profile, not an invented mkxp option |
| P2 audio | fmt 12.1.0 → OpenAL Soft 1.24.3; Ogg 1.3.6 → Vorbis/vorbisfile 1.3.7; SDL_sound 2.0.4; gcem 1.18.0 → FluidSynth 2.5.0 (embedded OSAL profile) | Requested at configure/link even for silent test. SDL_sound's actual enabled decoders must be inventoried from patched CMake/cache; no assumed decoder closure |
| P2 video | Ogg → Theora 1.2.0 / TheoraPlay `ec1aad1ee43592f216946cdc03b1ee4c4e1e2e59` | Requested unconditionally by pinned source, even if no video file used |
| P2 embedded/header sources | In-tree common/Python generation, GL headers, ghc filesystem, sigslot, libnsgif, shader sources; icon.png, gamecontrollerdb.txt, liberation.ttf | Part of source/build closure; default embedded assets require file-specific rights/notices. An asset-free *test project* does not remove embedded engine assets |
| P3 engine | All above → mkxp-z static intermediate → AArch64 executable, map and actual link-input inventory | Build, link, runtime start, visible rendering and game function are separate results |

**Critical profile decisions (not yet implemented):**

- Use the private target prefix via `ruby_system=enabled` and
  `sdl_system=enabled`; "system" must never mean Debian host libraries.
  The external Ruby branch avoids the engine's separately patched vendored
  Ruby rebuild and separate wrap libyaml/libffi builds. Test the unpatched
  private Ruby against the embedding API before claiming equivalence to
  the engine's Ruby wrap (different archive and patch set).
- `use_miniffi=false` excludes MiniFFI binding sources; it does not build
  or verify Ruby's Fiddle. `openssl=disabled`, `angle=disabled`,
  `extra_shaders=disabled`, no Steam SDK, no CJK fallback font.
- The source's non-Windows branch adds **`-static-libstdc++`**. The existing
  dynamic C++ probe does not attest this link. Prefer a small reviewed,
  pinned engine patch to use the already calibrated shared C++ runtime;
  otherwise audit/hash static archive members, ABI and licensing separately.
  Do not use static C++ linking to bypass provider review.
- Default vendored SDL would pull X11/Wayland/udev/D-Bus/IBus/DRM and
  potentially ANGLE/SPIR-V/Vulkan sources. A successful external pinned
  Mali SDL selection avoids that build branch, but does not prove all
  runtime `dlopen` paths absent. Inspect actual engine/backend use.
- `gl_system` selects GL **headers** or the Mesa subproject fallback;
  do not assume it authorizes a Mesa graphics-library build.
- Silent does not mean no OpenAL: `main.cpp` calls `alcOpenDevice(0)`.
  Inspect the exact patched OpenAL sources for a null backend, select
  and test it before device graphics work. Disabled ALSA/JACK/OSS/
  PipeWire/PulseAudio alone does not establish startup viability.

**Remaining graph incompleteness:** exact cache bytes/patch ordering,
SDL_image nested decoder sources, SDL_sound decoder configuration,
OpenAL wrapdb patch contents/null backend, selected build-system helper
closure and all actual configure/link inputs cannot be locked from this
workspace. Unknown required entry stays BLOCKED; this table is not a
complete lockfile. Existing `inputs.json` is not silently promoted to PASS.

## 4. Reproducible execution stages after access is restored

1. **Read-only reconcile once:** actual tiny02 Git status/HEAD, image IDs,
   Docker `inspect` mounts/limits/network, tool/package versions, compiler/
   sysroot/source receipts, `config.log`, Makefiles, current hashes and
   original device-library snapshot. Preserve owner changes; use no generic
   `make all`, install, cleanup or compiler reconfiguration during inventory.
2. **Preseed a selected lock:** every archive, patch, nested source, native
   generator and enabled dependency gets SHA-256, provenance/license,
   host/target role and deterministic path. Reconcile official Ruby `.tar.xz`
   and zlib 1.3.2 with existing research wraps explicitly. Missing digest,
   grant or actual recipe = stop that dependent stage; do not download.
3. **Batched private build:** reuse matching successful outputs. Generate
   reviewed cross/native configuration once; separate source mounts (RO),
   fresh build trees and target prefix. Use native Ruby generators, never
   ARM execution/QEMU. Set target-only pkg-config paths; record observed
   compiler include/library/startup searches, commands and link maps.
   Build missing encodings/extensions first, then independent media/text
   dependency batches, then engine, not hand-edited individual Makefiles.
4. **Resource envelope for every build:** immutable existing tools image
   `sha256:1c4ddd5655ad020d5e320e2181a04e4356af7c0e70f2be3cd5e901657cd8596b`,
   offline (`--network=none`), read-only rootfs/input mounts, unprivileged
   host-matching UID, `--cpus=2 --memory=4g --memory-swap=4g`, bounded tmpfs
   and work storage; no Docker-data deletion. Verify cgroup limits. Preserve
   **25 GiB free** using measured per-stage output budgets and a stop guard,
   not only a before/after `df` check. Current C++ helper's historical
   20-GiB floor is insufficient for this task and must not gate these builds.
5. **Static gate before packaging:** inspect every new ELF and relevant
   archive member, and compare the full recursive dependency/symbol graph
   against original, fingerprinted stock libraries as specified below.
6. **Private bounded package:** only a positive gate bound to exact artifact,
   config, test and provider hashes permits assembling a temporary bundle.
   Explicit allowlist; no firmware DSO/sysroot/game binaries. Verify copied
   bytes; manifest every file. No public artifact upload. Do not create or
   send a partially checked package while stage 5 is blocked.
7. **One grouped runtime trial:** after device trust/authentication and
   firmware identity are established, use an isolated `/tmp` directory,
   verify hashes there, enforce per-test plus overall TERM/KILL timeouts,
   sanitized environment and bounded output. Keep evidence/logs separately;
   no repeat of unchanged completed tests just to duplicate PASS.

Reproducibility needs source/tool/image/flags/config/layout locks plus
fixed locale/TZ/SOURCE_DATE_EPOCH and path normalization; compare output
bytes from a second isolated build only when justified. Existing hashes
and same-tree relinks are not public clean-room reproducibility. No
engine-build recipe can honestly be finalized without the blocked receipts.

## 5. ELF and ABI validator acceptance contract (#6)

Use a fingerprinted host readelf/binutils; **never `ldd` or execute target
ELF on the host**. The existing C++ validator is intentionally probe-specific,
not an engine deployment gate. Required tests for an engine validator:

- ELF64 little-endian AArch64, valid EXEC/DYN type, GNU_STACK non-executable,
  no TEXTREL; executable PT_INTERP exactly `/lib/ld-linux-aarch64.so.1`.
  Check GNU ABI kernel note if present; absence means kernel floor not
  independently established, not automatic proof of compatibility.
- Record every NEEDED/SONAME, RPATH and RUNPATH; reject absolute private
  build paths, empty/current-directory search elements and bundle escapes.
  Engine's upstream `$ORIGIN` link setting needs inspection of actual dtags,
  not an assumption it is RUNPATH. RUNPATH is not transitive.
- New-artifact GLIBC imports must fit the glibc-2.28 build policy; stock
  providers may legitimately require newer device GLIBC (e.g. 2.35).
  Verify GLIBCXX/CXXABI/GCC and `.gnu.version_r` requirements against the
  named providers' version definitions, without applying the build floor
  to unmodified stock providers.
- Resolve strong imported dynamic symbols and versions in the actual
  load scope/order; report weak unresolved imports separately. Versioned
  provider checking is distinct from ELF symbol lookup: glibc >=2.34
  compatibility DSOs can use libc symbol definitions. Candidate matching
  over an unordered union is **not** loader-resolution proof.
- Audit transitive dependencies, COPY relocation sizes where relevant,
  symlink roots, actual system search paths/cache and `dlopen`/Ruby extension
  loads. Account for exports supplied by the embedding executable/libruby;
  auditing each extension as an isolated process gives false failures.
- Hash every requester/provider/tool and bind the receipt to the package.
  No unresolved provider, missing snapshot, parser limitation, changed byte
  or unsupported lookup feature may silently yield a deployable PASS.
- Offline negative fixtures: ARM32/x86 ELF, malformed/truncated metadata,
  wrong interpreter, missing version/export/provider, newer GLIBC, wrong
  SONAME, escaped/absolute links, unsafe paths, TEXTREL/exec-stack, changed
  bytes and glibc merged-library behavior. Real immutable ELF comparison
  is also needed; synthetic fixture PASS alone is not hardware evidence.

## 6. Grouped hardware checklist (German; prepared, NOT_TESTED)

- [ ] Exakte NextUI-/BaseOS-Version, Kernel und Stock-Provider-Hashes erfassen;
  SSH-Hostkey extern bestätigen. Bestehende private Laufzeit nicht überschreiben.
- [ ] Nur die statisch freigegebenen, hashgebundenen Dateien bereitstellen;
  freien `/tmp`-Speicher prüfen, keine Systembibliotheken kopieren/ersetzen.
- [ ] Ergänzungstest: Ruby-Stdlib-Ladepfade, UTF-16LE/BE sowie Hin-/Rückkonvertierung,
  Psych `safe_load` mit primitiven Daten, abgewiesenem unerlaubtem Objekt/Alias,
  `dump`/Roundtrip und Fehlerbehandlung; keine unsichere YAML-Deserialisierung.
- [ ] Fiddle separat: kontrollierter Aufruf einer harmlosen Funktion wie `strlen`
  aus dem bestätigten libc-Provider, definierte Argument-/Rückgabetypen,
  einfache Speicherallokation/-freigabe. Keine beliebigen Bibliothekspfade.
- [ ] Erst bei vollständigem Engine-Link-/ABI-PASS: originales `customScript`,
  `rgssVersion=1`, prozedurales Bitmap/Sprite, begrenzte `Graphics.update`-Schleife,
  Dispose/Exit. Keine Spiele-/RTP-/RGSS-Binärdateien. Null-OpenAL zuerst nachweisen.
- [ ] Gesamt-Timeout und Loggrenzen von außen erzwingen; Start, Ruby-Binding,
  sichtbare Grafik und sauberes Ende getrennt protokollieren. Exitcode 0 allein
  beweist keinen sichtbaren Start (Upstream-Initialisierungsfehler können 0 liefern).
- [ ] Bei Fehler/Timeout stoppen und Zustand/Logs erhalten. Kein Neustart von
  NextUI/Produktionsdiensten ohne Freigabe, keine Kernel-/zram-/Firmware-Eingriffe.

## 7. Verification matrix and next action

| Work item | Result | Evidence level |
| --- | --- | --- |
| Workspace identity, local/remote PR head and draft state | PASS | verified-on-host (authoring container/GitHub read only in continuation) |
| Source dependency/profile inspection at pinned engine commit | PASS | upstream-reported/source-inspected, not built |
| Ruby core, zlib, low-level Psych | PASS (owner-reported) | H700 report with artifact hashes; raw logs/firmware missing |
| Private tiny02 bytes/receipts/mounts | BLOCKED | No authenticated host access or private mounts |
| Python unit tests / genuine ELF audit / build | BLOCKED | Python/binutils/compiler/container runner unavailable |
| Documentation whitespace check (`git diff --check`) | PASS | verified-on-host; not code/runtime validation |
| Extended Ruby/Psych/Fiddle grouped hardware tests | NOT_TESTED | Requires gated bundle and device access |
| mkxp-z link / engine runtime / game function | NOT_TESTED | No engine artifact; prior stages blocked |
| Public reproduction / distribution | BLOCKED | Selected lock/recipes and rights gates incomplete |

**Smallest next action:** provide an authorized tiny02 runner/project session
with the existing private paths and read-only receipts, plus verified device
SSH trust/identity. Inventory and hash-reconcile there before building.
This report requires no new paid service, download, host installation,
firmware modification, public binary or PR merge.

[root]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/meson.build
[src]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/src/meson.build
[opts]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/meson_options.txt
[binding]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/binding/binding-mri.cpp
[bb]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/binding/meson.build
[assets]: https://github.com/mkxp-z/mkxp-z/blob/37a04d14413454551a7b6aadbb4e93e67168accb/assets/meson.build
[inventory]: https://github.com/almighty-atlas/nextui-mkxp/blob/9d482dc981401166b40155678ad00e29daad9163/docs/audit/source-inventory.json
[plan]: https://github.com/almighty-atlas/nextui-mkxp/blob/91b5a27378150bb479fc8546f2bddb6c6e5b1da7/docs/H700_MINIMAL_ENGINE_PLAN.md
