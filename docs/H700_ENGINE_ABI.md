# Installed H700 engine: static ABI candidates and H700 loader PASS

2026-10-28 · Refs #6 · Stacked on PR #33 to use the unmerged build and
roadmap; not an independent clean-main change. Main was inspected, not merged.

**verified-on-host:** the installed engine passes the explicit provider graph
audit. **No engine entry-point execution on H700 occurred.** The device was
initially unreachable; after the owner restored access, the bounded loader-only
test passed. The engine was copied only into a private device `/tmp` directory.

## Evidence

[`engine-abi-evidence.json`](../build/h700-engine/engine-abi-evidence.json)
records the engine/provider/tool hashes and private raw plan/report hashes.
Engine SHA-256:
`33b15913859596645d4051bed403e6f0e0953e6d8366db3b06665a9a96ce73f3`.

| Check | Result |
| --- | --- |
| ELF class/endian/machine | ELF64 little-endian AArch64 PASS |
| Interpreter | `/lib/ld-linux-aarch64.so.1` PASS |
| GNU minimum-kernel note | 4.9.0, below measured 4.9.170 |
| Direct GLIBC requirements | At most GLIBC_2.28; no GLIBC_PRIVATE |
| Stack / TEXTREL | RW / none |
| Installed paths | DT_RPATH exactly `$ORIGIN`; no RUNPATH |
| Closure | 10 objects, 926 strong imports, 0 missing strong candidates |
| Weak imports | 31 unresolved, reported rather than treated as proof of safety |
| COPY relocations | stdout and stderr, GLIBC_2.17, 8-byte OBJECTs in engine and libc |
| Hardware loader | **verified-on-H700 PASS:** `--verify` and `--list` both exit 0 |

The static graph is **not an ld.so simulation**: it does not prove dynamic
load order, interposition, optional weak-code paths or `dlopen` dependencies.
The loader check is a separate gate and does not prove an
engine start, rendering, sound or controls.

## Exact runtime-provider table

All providers were hash-matched to the device before it became unreachable.
No provider bytes are tracked or publicly distributed. Nine provider hashes
are in the evidence JSON; all are available on the observed firmware, none
are bundled in the prepared loader test.

| SONAME | Observed device location | Required by |
| --- | --- | --- |
| ld-linux-aarch64.so.1 | `/lib/ld-linux-aarch64.so.1` | Engine, libc, libm, librt |
| libc.so.6 | `/lib/aarch64-linux-gnu/` | Engine and runtime providers |
| libm.so.6 | `/lib/aarch64-linux-gnu/` | Engine, SDL, samplerate |
| libpthread.so.0 | `/lib/aarch64-linux-gnu/` | Engine, SDL |
| libdl.so.2 | `/lib/aarch64-linux-gnu/` | Engine, SDL |
| librt.so.1 | `/lib/aarch64-linux-gnu/` | Engine |
| libgcc_s.so.1 | `/lib/aarch64-linux-gnu/` | Engine |
| libSDL2-2.0.so.0 | `/mnt/SDCARD/.system/h700/lib/` | Engine |
| libsamplerate.so.0 | `/mnt/SDCARD/.system/h700/lib/` | **Actual NextUI SDL**, not private link SDL |

Do not use the private link SDL as a substitute for auditing the real device
SDL. The actual SDL has the extra samplerate dependency. libstdc++ and most
engine libraries are statically linked; a successful dynamic closure check
does not satisfy their separate source/license obligations.

## Narrow policy changes, not general bypasses

`scripts/h700_runtime_abi.py` keeps its default RPATH/COPY rejection. A
hash-bound program entry may explicitly declare:

```json
{
  "policy": {
    "rpath": "origin-only",
    "copy_relocations": {
      "stdout@GLIBC_2.17": {"provider": "libc.so.6", "size": 8},
      "stderr@GLIBC_2.17": {"provider": "libc.so.6", "size": 8}
    }
  }
}
```

- RPATH permission is restricted to programs and **exactly** `$ORIGIN`, with
  no RUNPATH simultaneously. Other directories, empty components, parent
  paths and unknown policy keys fail. DT_RPATH is inherited by dependencies;
  only use a fresh private staging directory, no writable shared bundle,
  no setuid/capability-bearing executable, and no arbitrary bundled libraries.
  Device access uses the existing root account; this is not an unprivileged
  device sandbox. The loader
  diagnostic explicitly supplies the measured NextUI library path.
- COPY permission requires the exact complete relocation allowlist, symbol
  version/provider relationship, local relocation address, strong OBJECT
  definitions, unique reachable foreign definition, and equal nonzero sizes
  in the program, provider and approval. A missing/extra COPY, wrong version,
  weak/function symbol, ambiguity, wrong address or size stops validation.
- Provider/tool/engine SHA-256 pins are checked before and after inspection.
  These are metadata checks; the real runtime binding remains unverified.

## Reproduction and next step

On tiny02, the private job `engine-build-20261028T172043Z` contains
`engine-abi-plan.json` and `engine-abi-report.json`. From this checkout:

```sh
python3 scripts/h700_runtime_abi.py --plan "$PRIVATE_JOB/engine-abi-plan.json"
python3 -m unittest discover -s tests
sh -n scripts/h700_engine_loader.sh
```

The native readelf tool only reads AArch64 bytes. The complete private report
SHA-256 is `f16dcda5ea6b04792f85b35b4742f12fefaa14641c00651f798628cc794be75f`.
Local verification: **131 unit tests PASS**, Python compileall PASS,
`sh -n scripts/h700_engine_loader.sh` PASS and `git diff --check` PASS.
These checks ran on the host, not CI. Synthetic fixtures cover strict RPATH,
COPY size/type/version/address/allowlist failures and end-to-end policy
application; the actual ELF audit is separate host evidence.

`scripts/h700_engine_loader.sh` is prepared for a fresh private device stage
under `/tmp/nextui-mkxp-loader-*`, containing only the hash-checked engine and
the script. It bounds each loader command to 10 s (+2 s kill), uses a clean
environment and strips ASLR addresses from displayed logs. It runs only
`ld.so --verify` and `--list`, not the engine entry point. Verify source and
destination hashes, device identity and adequate `/tmp` space before copying.
Never stage stock libraries or replace libc/graphics libraries.

### Actual loader result

The owner restored device access. NextUI-20261013-0 (`39a06de`), kernel
4.9.170 and all nine provider hashes matched again before and after the test.
The 34,914,232-byte engine and hash-bound script were staged privately under
`/tmp/nextui-mkxp-loader-33b159138595` (no bundled libraries). Both commands
returned 0; the overall bounded script returned 0 and printed
`ENGINE_LOADER_PASS`. The [sanitized log](evidence/2026-10-28-engine-loader.txt)
shows all expected resolved paths, including SDL and samplerate from NextUI.
Script SHA-256: `d330116653011db4b1d6da92f20403308daddc76b94507eddac8157cb0d25821`.

This checks loader resolution, not lazy function binding, graphics, audio,
Ruby embedding or gameplay. The roadmap remains **70%** until the next
hardware milestone is actually met. Next: prepare an asset-free engine smoke
test with an explicit human checklist for visible output and controls.
