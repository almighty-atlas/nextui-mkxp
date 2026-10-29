# Private Ruby extension batch: build, static audit and H700 PASS

2026-10-28 · Refs #6 · Local continuation of draft PR #31; no push/merge/release.

## Result and proof boundary

**verified-on-H700:** the original grouped trial passed on RG35XX Pro,
AArch64 Linux `4.9.170`, Base OS **1.4.0**, NextUI **NextUI-20261013-0** /
revision **39a06de**. Raw output with no personal paths:
[runtime log](evidence/2026-10-28-ruby-runtime.txt). Exact inputs, output
hashes and evidence levels: [runtime-batch-evidence.json](../build/h700-engine/runtime-batch-evidence.json).

| Result | Check |
| --- | --- |
| PASS / host | Official Ruby 3.1.3 archive SHA-256 and all 11,112 regular source files match |
| PASS / host | Seven saved stock provider files match the live device bytes, checked before and after trial |
| PASS / host | Offline isolated cross-build: 61 encoding/transcoder modules, Fiddle + bundled libffi 3.2.1, StringIO, Date |
| PASS / host | 76 explicit ELF objects including stock providers: architecture, interpreter, kernel note where present, stack/TEXTREL, paths, NEEDED/SONAME, named version definitions and reachable strong symbol candidates |
| PASS / host | 192 relocatable objects and 101 members in three archives are AArch64 |
| PASS / H700 | StringIO, Date, Set, Shellwords load and representative operations |
| PASS / H700 | UTF-16LE/BE, UTF-32LE/BE, ISO-8859-1 and Windows-31J encode/decode roundtrips; no UTF-16 warnings |
| PASS / H700 | Psych `safe_load`/`dump` primitive roundtrip and explicitly permitted Date; object tags and aliases rejected by default |
| PASS / H700 | Fiddle loads, calls stock libc `strlen`, allocates/frees memory |
| BLOCKED | Full mkxp-z source/dependency/license closure and engine build |
| NOT_TESTED | Engine start, RGSS/game function, all other Ruby libraries/APIs, Fiddle callbacks and every generated encoding |

Actual trial exit code **0**, marker `RUBY_RUNTIME_BATCH_PASS`. Only a new
temporary directory `/tmp/nextui-mkxp-runtime-8c9480cec123` was used; old
Ruby staging, games/saves, system libraries and NextUI were not changed.
No service restart or graphics/audio/display test occurred. The archive
was streamed privately from tiny02 to the device and verified there;
no binary or firmware library is tracked or published.

Ruby core, zlib and low-level Psych trials already reported by the owner
were **not repeated**. The interpreter/library and original zlib/Psych
bytes were rehashed and reused, unchanged. Earlier reports remain owner
evidence for those earlier test bodies, not falsely relabelled agent runs.

## Implementation

- `scripts/h700_ruby_batch.py`: fresh private copy of the observed build,
  source/seed verification, image-by-ID, RO inputs/rootfs, network disabled,
  UID 1000, 2 CPUs / 4 GiB memory+swap limit, `make -j2`, 600-second outer
  build bound and output/log budgets. Existing builder's 5-GiB setting is
  untouched and is **not** used for these new builds.
  The final driver also pins the existing native Ruby, compiler archive,
  sysroot receipt and actual sysroot tree. A final Fiddle-only guarded retry
  validated those checks and preserved all 66 tested runtime-module hashes.
- `scripts/h700_ruby_extensions.sh`: native Ruby + generated cross-fake
  module drives reviewed `encs` and extension recipes. No ARM interpreter,
  `make all`, source modification, installation, package fetch or QEMU.
  The final recipe explicitly supplies Autoconf's build identity and rejects
  configure logs with target execution attempts (see safety finding below).
- `scripts/h700_runtime_abi.py`: fingerprinted native readelf; explicit
  hash-bound provider graph, not an emulated dynamic loader. Strong imports
  must have name/version-compatible candidates in reachable dependencies;
  weak missing imports are reported. glibc merged compatibility DSOs are
  handled separately from named version-definition checks. Runtime load
  order, interposition and untested `dlopen` edges are not proven by PASS.
- `scripts/prepare_h700_ruby_trial.py`: fresh audit and source check,
  build-receipt hash agreement, explicit Ruby/extension allowlist and
  pure-Ruby source files only, notices, per-file manifest, private archive.
  No stock provider is copied. The archive is not a release artifact.
- `scripts/h700_ruby_trial.sh` / `tests/hardware/ruby_runtime.rb`: clean
  launch environment, manifest validation, no LD_LIBRARY_PATH override,
  process/phase timeouts and bounded log. Global timeout also bounds native
  C/libffi calls that Ruby's timeout cannot reliably interrupt.

The guard requires 27 GiB initially, stops at **26 GiB** to preserve the
25-GiB hard reserve, and caps a job at 1 GiB. Monitoring cannot reserve
storage against unrelated host writers; the 1-GiB headroom is deliberate.
No Docker cleanup/prune was performed. After the support batch,
31,968,116,736 bytes remained free (about 29.8 GiB).
After the final guarded retry, 31,860,514,816 bytes remained free (about 29.7 GiB).

## Reproduction with the existing private inputs

This is reproducible **continuation of the private build**, not public
clean-room reproduction: the compiler/sysroot/native prefix, seed build,
snapshot and raw receipts are private. See [pipeline dependency plan](H700_RUNTIME_PIPELINE.md)
for the remaining lock/rights work. Public reproduction is NOT_ESTABLISHED.

On tiny02, `TOOLS` below is the existing private tools root and `BUILD`
the existing `.nextui-mkxp-build` root; use observed paths, not host SDK
defaults. `REPO` points to this project checkout. All outputs stay outside
Git. The private `abi-inputs.json` records exact paths/hashes for native
readelf, the already linked `$ORIGIN` Ruby interpreter, shared libruby,
zlib/Psych and seven stock providers. Each object supplies an ID, role,
`file: {path, sha256}` and explicit SONAME aliases (`provides`). Never put
these private files into the public repository just to satisfy a check.

```sh
python3 "$REPO/scripts/h700_ruby_batch.py" \
  --native "$TOOLS/ruby-native-3.1.3" \
  --seed "$TOOLS/ruby-aarch64-3.1.3-v2" \
  --toolchain "$BUILD/toolchains/gcc-8.3" \
  --sysroot "$BUILD/sysroot-runs/sysroot-20261027-212308/sysroot" \
  --zlib "$TOOLS/zlib-aarch64-1.3.2/prefix" \
  --workspace "$FRESH_PRIVATE_JOB"

python3 "$REPO/scripts/h700_runtime_abi.py" --plan "$PRIVATE_ABI_PLAN" \
  --extensions-dir "$FRESH_PRIVATE_JOB/target/.ext/aarch64-linux" \
  --helpers-dir "$FRESH_PRIVATE_JOB/target/ext/fiddle" \
  --relocatable-tree "$FRESH_PRIVATE_JOB/target"

python3 "$REPO/scripts/prepare_h700_ruby_trial.py" --plan "$PRIVATE_ABI_PLAN" \
  --source "$TOOLS/ruby-native-3.1.3/src/ruby-3.1.3" \
  --source-archive "$TOOLS/inputs/ruby-3.1.3.tar.xz" \
  --native "$FRESH_PRIVATE_JOB/target/.ext/aarch64-linux" \
  --helpers "$FRESH_PRIVATE_JOB/target/ext/fiddle" \
  --build-receipt "$FRESH_PRIVATE_JOB/build-result.json" \
  --output "$FRESH_PRIVATE_TRIAL"
```

Commands document a fresh continuation route, **not a request to repeat
the successful unchanged build/trial**. The final unified fresh-build route
has not itself been rerun after guard hardening; successful execution is
attested by the phased build receipts, not a new clean-room replay.
The actual work used
`runtime-batch-20261028T131737Z` under the private tools root, with separate
`extensions-v1`, `extensions-v2`, `extensions-v3`, `extensions-support`, `extensions-final`
and `trial-v1` paths. All logs were preserved:

1. Initial encoding/Fiddle build passed; audit found an absolute `/target`
   RPATH in the unused helper `libffi.so.6.0.4`. It was not deployed.
2. First corrective retry failed configure because a Ruby `-e` wrapper
   changed `$0`, so mkmf did not select the build-tree context. No tests
   were attempted on that failed build.
3. Corrected wrapper preserves extconf `$0`, updates `LIBRUBYARG_SHARED`
   and clears mkmf `RPATHFLAG`. All 61 successful encoding modules were
   reused with exact hash agreement. Final Fiddle bytes were unchanged;
   the helper's path problem was eliminated and it passed static checks.
4. StringIO is required by high-level Psych (`psych/nodes/node.rb`);
   Date covers timestamp parsing. They were built in one support batch,
   reusing all successful encoding/Fiddle outputs. Only required trial
   libraries were selected; this does not establish the entire stdlib.
5. New readelf parser tests caught a note/version section-boundary issue:
   glibc SystemTap note `Name:` fields must not be interpreted as VERNEED.
   Fixed before packaging; the negative regression fixture is automatic.
6. **Safety finding in final log review:** bundled libffi configure supplied
   `--host` but not a build identity. Autoconf tried `./conftest` while in
   `cross_compiling=maybe`; the x86_64 kernel rejected it with `Exec format
   error`, exit 126. No ARM code ran, but the attempted execution was not
   acceptable. The final recipe exports the supported precious variable
   `build_alias=x86_64-pc-linux-gnu`, forcing cross mode before the probe.
   A negative log regression test and post-configure guard reject execution
   attempts. `extensions-final` rebuilt only Fiddle, reused the 61 encodings
   and StringIO/Date, and passed this guard and the full static audit.
   **All 66 module hashes match the already tested bundle exactly**; no
   repeat hardware trial was needed. Earlier receipts/logs were retained.

Private final bundle: SHA-256
`8c9480cec12323e926fd6f2ba87a89edd8a1cd38506497fc628fa599c3da115a`,
4,723,358 bytes, 870 manifest entries including 66 native modules.
All ELF runtime files passed before staging; the expanded final
intermediate/archive audit was also run after the trial, without rerun.

## Verification and remaining blockers

Offline verification:

```sh
python3 -m unittest discover -s tests
sh -n scripts/h700_ruby_extensions.sh
sh -n scripts/h700_ruby_trial.sh
git diff --check
```

Actual result: **94 unit tests PASS**, Python compileall PASS, both shell
syntax checks PASS and `git diff --check` PASS. These checks are local, not CI.
Tests use synthetic metadata/guard fixtures;
the private actual-ELF audit and physical trial are separate evidence.
The same original Ruby test also passed on native x86_64 Ruby in the
offline tools image before the device trial (the native-only run additionally
exercised Pathname; the H700 suite deliberately selects no Pathname extension).

No mkxp-z archive/checkout or media/text dependency cache was present in
the inspected private build input roots. The engine lock still lacks
exact selected SDL_image/nested decoder closure, complete patch/grant and
embedded-asset review. Consequently no engine configure/link/run was
attempted. No game support, graphics integration or complete engine
pipeline is claimed. Next: lock the chosen external dependency prefix
and Ruby embedding headers/pkg-config contract, then the engine link.
