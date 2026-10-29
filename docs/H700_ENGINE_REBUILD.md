# Fresh engine rebuild (#5)

2026-10-29, **verified-on-host**: a completely new setup/compile directory
produced byte-identical engine outputs, both before and after upstream install.
No prior object files/build directory were reused. All selected dependencies
were configured/compiled again from the existing checksum-verified source cache.

| Check | Original (2026-10-28) | Repeat (2026-10-29) |
| --- | --- | --- |
| Setup | PASS | PASS, 65 s |
| Compile | 684/684, 463 s | 684/684, 412 s |
| Build ELF (34,914,232 bytes) | `245e5cb3…0558c` | Same SHA-256 and `cmp` PASS |
| Installed ELF | `33b15913…73f3` | Same SHA-256 and `cmp` PASS |
| Pak runtime: ELF, LICENSE.txt, 842 Ruby files | 844 files | Every relative filename and byte hash equal |
| Full upstream install tree | 1,080 files | 69 `.gemspec` files differ only in generated `s.date` (October 28 vs 29) |

The last row matters: this is **not** a claim that every upstream installation
byte is reproducible. The current private Pak's installer intentionally selects
only `*.rb` from stdlib; the dated default-gem metadata is not in its runtime.
A future package shipping gemspecs must fix the source-date policy first.

## Reproduce using the checked-in driver

Preparation computer: Linux x86_64, unprivileged Docker access; existing fixed
tools image and reviewed prerequisites. `NATIVE` is the native Ruby build parent
with `prefix/`; `SDL_RUN` is the prior reviewed raw SDL run. Host locations may
vary; the driver maps them to its fixed internal build paths.

```sh
# JOB must not exist. These commands do not download or execute AArch64 code.
python3 scripts/mkxp_z_configure.py --phase setup \
  --native "$NATIVE" --toolchain "$TOOLCHAIN" --sysroot "$SYSROOT" \
  --source "$ENGINE_SOURCE" --packagecache "$PACKAGECACHE" \
  --sdl-run "$SDL_RUN" --workspace "$JOB" \
  --reserve-gib 5 --budget-gib 3 --timeout 1200

python3 scripts/mkxp_z_configure.py --phase compile \
  --native "$NATIVE" --toolchain "$TOOLCHAIN" --sysroot "$SYSROOT" \
  --job "$JOB" --reserve-gib 5 --budget-gib 3 --timeout 1800
```

The reserve is the owner's existing 5-GiB minimum: fresh setup needs at least
7 GiB free and stops at 6 GiB. Docker has no network, read-only root, 2 CPUs,
4 GiB, no capabilities, no-new-privileges and caller UID/GID. Compiler, sysroot
and native Ruby are mounted read-only; the fresh job is the only persistent
writable output. Do not prune or delete unrelated host data to make room.

Perform upstream installation inside the same fixed image into a **fresh private
DESTDIR**, with the job mounted as `/job` and native Ruby at `/work`:

```sh
meson install -C /job/build --no-rebuild --destdir /job/staged --tags mkxp-z
```

This strips the build RPATH and retains `$ORIGIN`. Compare the build ELF and
staged ELF to the previous run with `cmp` and `sha256sum`. For the runtime file
manifest, sort relative names from `mkxp-z.aarch64`, `LICENSE.txt` and
`stdlib/**/*.rb`, SHA-256 each, serialize the name-to-digest map with sorted JSON
keys and separators `(',', ':')`, then hash that UTF-8 JSON. Both runs agree:
`2cdc8c1436a10840451e59efda6c220fae38cbc8a27b7b867dd450a7778b2f6d`.

## Evidence and boundaries

[Machine-readable evidence](../build/h700-engine/engine-rebuild-evidence.json)
binds the driver, source/profile/lock, private configure/compile receipts, full
artifact hashes and exact comparison boundaries. Logs are retained privately.
The log scanner found no target-execution attempts. Readelf again reports
ELF64/AArch64, `/lib/ld-linux-aarch64.so.1`, RW stack and installed `$ORIGIN`.
The older linker warns about libffi's GNU property note; no flag was added to
ignore unresolved symbols, and the engine is byte-identical to the earlier
accepted private binary.

This completes the fresh-repeat experiment for the engine, **not** a source
bootstrap of the prebuilt compiler, native Ruby, SDL or private tools image.
That remains #4. No new target executable was run or transferred, and no public
artifact/release or source/relink clearance is implied (#16). Knight Blade's
owner-verified private playability stays **100%**, independently of this host run.
