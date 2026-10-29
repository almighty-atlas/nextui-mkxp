# H700 stock-SDL video trial — limited PASS

Recorded 2026-10-27 for [Issue #22](https://github.com/almighty-atlas/nextui-mkxp/issues/22)
and existing [PR #30](https://github.com/almighty-atlas/nextui-mkxp/pull/30).
This is a later evidence update, not a rerun by this documentation agent.
The owner supplied the build facts, physical observation and sanitized lines
below in the task. No binary, private path, raw device log or vendor library is
included. Historical [preparation evidence](../spikes/h700-stock-video/evidence.json)
is retained; its Alpine failure is not the result of this later trial.

## Identity and evidence boundaries

| Item | Evidence / result |
| --- | --- |
| Tested application ELF SHA-256 | `d41477f3a3803ee22e778629d4b5c9a0947cd4449e1717f1e7f347226a09a5f9` |
| Host build | Supplied verified build facts: AArch64 ELF, `SDL_ONLY_HOST_LINKED`, 21 SDL exports, deterministic repeat-link; **not rebuilt or independently inspected in this session** |
| Initial guards | Owner reports `HOST_VERIFIED` and `SOURCE_ONLY` originally present; host verification does not itself permit execution |
| Hardware | Owner: RG35XX Pro, NextUI, AArch64, kernel 4.9.170 |
| Firmware identity | **Exact installed NextUI release/build NOT PROVIDED for this trial**; do not substitute the earlier ADR's release-file hint |
| Device trace | Owner-supplied `RMXP_VIDEO` lines reproduced below; verified-on-H700 evidence by owner, not agent/CI execution |
| Physical observation | **OWNER_OBSERVED_H700:** a colorful moving triangle was visible; after approximately five seconds the device automatically returned to an operable NextUI menu |
| Post-trial safety state | Owner reports `SOURCE_ONLY` restored on the handheld and ELF hash successfully checked again; no continued activation is authorized |

**Result: PASS for one game-free GLES video + timed normal-return trial on the
reported device.** The renderer identifies ARM Mali-G31, rather than a known
software renderer. The program requests an ES2 pathway; the actual context
reports ES 3.2. This is not proof of an exactly ES2-only context or every engine
shader/extension. `297` frames / `5007` ms are loop counters, **not** a game FPS
benchmark or independently measured presentation rate.

## Sanitized device excerpt (verbatim supplied lines)

```text
RMXP_VIDEO stage=start code=0
RMXP_VIDEO sdl_compiled=2.28.5 sdl_linked=2.28.5
RMXP_VIDEO sdl_driver=mali
RMXP_VIDEO stage=sdl_ready code=0
RMXP_VIDEO stage=context_ready code=0
RMXP_VIDEO gl_vendor=ARM
RMXP_VIDEO gl_renderer=Mali-G31
RMXP_VIDEO gl_version=OpenGL ES 3.2 v1.r20p0-01rel0.6bf520cc6fc11e5ebc382522e4d4ab38
RMXP_VIDEO glsl_version=OpenGL ES GLSL ES 3.20
RMXP_VIDEO stage=draw_begin code=0
RMXP_VIDEO stage=draw_end code=0 frames=297 elapsed_ms=5007
RMXP_VIDEO stage=cleanup_complete code=0
RMXP_VIDEO stage=exit_owner_verification_required code=0
```

The final stage explicitly delegates return verification to the owner. Code 0,
SDL version equality, and a void swap call alone do not prove visible output or
UI recovery. Those two observations come from the owner separately. No shell
process exit status, process-tree check or independent orientation measurement
was supplied; none is inferred from the log.

## Verification matrix and remaining gates

| Check | Level | Result / limit |
| --- | --- | --- |
| AArch64 link, SDL exports, repeat-link | verified-on-host (supplied earlier facts) | PASS; no fresh target build/hash verification here |
| SDL `mali`, GL context, draw loop, cleanup stages | verified-on-H700 (owner trace) | PASS for this candidate/run |
| Visible colorful animation, timed return, responsive menu | OWNER_OBSERVED_H700 | PASS; physical observation, not inferred from trace |
| Guard restoration and repeat ELF hash check | OWNER_REPORTED_H700 | PASS as reported; not inspected here |
| Exact NextUI version, orientation, surviving-process audit | untested / incomplete evidence | NOT_TESTED for the missing details |
| Full library path/hash/versioned-symbol and libsamplerate/vendor closure inventory | untested | Successful run exercises the used path, not an exhaustive dependency audit |
| Audio, controller mapping, exit chord, failure/hang recovery, repeated cold starts | untested | NOT_TESTED; responsive NextUI navigation is not engine input verification |
| mkxp-z/Ruby/RGSS startup, saves, games, performance/stability | untested | NOT_TESTED |
| Binary publication, combined-work rights, notices/source/relinking | blocked | BLOCKED by [PR #19](https://github.com/almighty-atlas/nextui-mkxp/pull/19); unchanged |

No device commands, transfer, guard transition, library changes or further test
are part of this update. Do not merge/close issues from this limited result.
Next work is the offline, host-only milestone in the
[minimal engine implementation plan](H700_MINIMAL_ENGINE_PLAN.md), not another
device launch or an engine compatibility claim.

## Documentation-session verification (actually run)

These are **verified-on-host**, not verified-in-CI or a new hardware test.
Existing private native Python/GCC/readelf tools were reused without installation.
This Alpine environment needs the following local tool paths; on a normal host
the portable test command is in [TEST_PLAN](TEST_PLAN.md).

```sh
LD_LIBRARY_PATH=/home/opencode/.cache/nextui-host-tools/usr/lib STOCK_TEST_READELF=/workspace/nextui-mkxp/.git/readelf-host /home/opencode/.cache/nextui-host-tools/usr/bin/python3 -I -B -m unittest discover -s spikes/h700-stock-video -p 'test_*.py' -v
```

```text
Ran 19 tests in 0.108s
OK
```

Includes 15 existing preparation/ELF-policy/guard tests and four new consistency
checks for hash, historical scope, trace/observation separation and local Markdown
links/fences. Positive ELF/assembly fixtures are synthetic/mocked, not the private
tested ELF; consistency tests cannot authenticate an owner's observation.

```sh
PATH=/workspace/nextui-mkxp/.git/stock-host-bin:/usr/bin:/bin LD_LIBRARY_PATH=/home/opencode/.cache/nextui-host-tools/usr/lib /home/opencode/.cache/nextui-host-tools/usr/bin/python3 -I -B -m unittest discover -s /home/opencode/.cache/nextui-stock-video-prepared-v2/scripts/issue_26_tests -p test_proc.py -v
```

```text
Ran 5 tests in 0.377s
OK
```

This is the pinned PR #27 **native mock** suite, including all 26 missing-proc
cases, animation and simulated deadline/cleanup failures. No real SDL/GPU or
AArch64 execution.

```sh
sh -n /home/opencode/.cache/nextui-stock-video-prepared-v2/Tools/h700/RMXP-Video-Test.pak/launch.sh
git diff --check
```

Both exited 0 without output. The unit suite also confirms SOURCE_ONLY exit 90
and SSH refusal 81. No new target artifact, device action or CI run is claimed.
