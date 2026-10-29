# Input configuration and session supervisor candidate (#10)

Status: **verified-on-host**, cross-compiled for AArch64, **not executed on H700**.
The implementation is original MIT-licensed code; no R36S port code was copied.
It depends only on Linux/POSIX interfaces, not SDL internals or a modified mkxp-z.

## Controller mapping

`config/h700-controls.json` reproduces the previously reviewed Knight Blade
FORMAT_VER 3 mapping. Its encoded SHA-256 is
`cc11f43b8f75d7de64c79ffa56a1a02528ef0483b0d811f1fc0bc77618425b6b`, matching
the private H700 fixture documented in #39. That earlier observation confirms
physical A as SDL B, physical B as SDL A, and Start opening the game menu; it
does not certify every control in every Essentials game.

| Physical control / SDL source | RGSS target |
| --- | --- |
| D-pad and left stick | movement |
| Physical A / SDL B | C (confirm) |
| Physical B / SDL A | B (cancel) |
| Start | B (menu) |
| SDL X / SDL Y | A / X |
| Left/right stick click | Y / Z |
| Left/right shoulder | L / R |
| Select, Guide, right stick axes, triggers | unbound by default |

The file format follows mkxp-z `src/input/keybindings.{h,cpp}` and SDL2 enum
values reviewed during the prior engine work. It contains a little-endian
12-byte header and 16-byte binding records. The Python encoder validates
versions, types, unique sources, allowed targets and essential movement,
confirm and cancel controls. No copyrighted assets or binaries are involved.

Copy/edit the JSON for a game, then generate a **fresh** output:

```sh
python3 scripts/rmxp_controls.py config/h700-controls.json /private/keybindings.mkxp1
```

After backing up the current mapping, place the reviewed file at
`.userdata/h700/nextui-mkxp/<ID>/data/nextui-mkxp/game/keybindings.mkxp1`.
The #40 candidate preserves an existing per-game file. The encoder itself
never overwrites an existing output. There is no universal Pokémon Essentials
mapping: verify the game's use of RGSS A/X/Y/Z/L/R explicitly.

## Native process supervision

`native/rmxp-session.c` starts exactly one requested command in a dedicated
process group and reports the actual `waitid` result. Unlike a shell's numeric
exit status, it distinguishes explicit exit 143 from termination by signal 15.
Metadata contains fixed fields only, not command lines or private paths.
Child output remains the caller's responsibility; use the Pak's bounded log.

```sh
# Build for the current Linux host; this does NOT produce an H700 binary.
cc -std=c11 -O2 -Wall -Wextra -Werror native/rmxp-session.c -o /private/rmxp-session
/private/rmxp-session -- /absolute/path/to/engine
```

On supervisor TERM/INT/HUP, the owned group receives TERM. If it has not exited
after the grace period (default 3000 ms, configurable 100–10000), it receives
KILL. Once the leader exits, remaining group members receive TERM, then KILL
after a 100 ms cleanup window. The leader remains unreaped until these signals
are sent, preventing PID reuse from targeting another group. The process acts
as a child subreaper and reaps adopted descendants with a bounded cleanup loop.
It never uses `killall`, signals unrelated groups, changes governors/services,
modifies device input state or grabs an input device.

The child disables core dumps, resets inherited termination handlers, closes
the input descriptor before exec and requests KILL if its supervisor dies.
No user save file is deleted or repaired. Forced termination can interrupt a
game's write: prefer the game's Shutdown menu and do not use the chord while
saving. Signals cannot immediately stop a kernel-uninterruptible task, and
intentionally daemonized descendants that leave the owned group are outside
this supervisor's cleanup contract. Successful software cleanup is not proof
of Mali/ALSA teardown or a restored NextUI screen; those require device tests.

## Optional hold-to-quit chord

There is deliberately **no default event node or guessed physical keycode**.
The proposed physical combination is Start+Select, held 1.5 seconds. Confirm
both Linux evdev codes and the input node on the installed firmware first.
SDL button numbers in the JSON above are not evdev keycodes.

```sh
/private/rmxp-session --input "$VERIFIED_EVENT_NODE" \
  --keys "$FIRST_EVDEV_CODE" "$SECOND_EVDEV_CODE" \
  --hold-ms 1500 --grace-ms 3000 -- /absolute/path/to/engine
```

The node is opened read-only/nonblocking, checked as a real evdev character
device, and queried for support of both codes. No `EVIOCGRAB` or event writes
occur. SDL continues receiving normal buttons; the combination may therefore
also affect the game's menu. Both buttons must first be released. A continuous
hold triggers TERM once; repeats do not count as fresh presses. `SYN_DROPPED`
causes resynchronization and disarming. Input loss or malformed/flooding input
disables the chord rather than killing the game. In-game Shutdown still works.

Synthetic event injection exists only in a test build compiled with
`RMXP_TEST_INPUT`; production builds reject `--test-fd`.

## Actual verification (2026-10-29)

- Local harness initially lacked `linux/input.h`; no host packages were installed.
- **14 host tests PASS** (with #40/#41 integration) inside the existing network-disabled, read-only-source,
  unprivileged Debian tools container on the build host, GCC 14.2.0.
- Both production and test builds compile with `-Wall -Wextra -Werror`.
- Tests cover mapping compatibility/overrides, essential controls, existing-file
  preservation, real exit versus signal, chord timing, repeats/startup holds,
  event loss, `SYN_DROPPED`, TERM-ignoring children, descendant cleanup and
  preservation of unrelated processes. All engines/input events are synthetic.
- H700-target **cross-build PASS**, using the existing GCC 8.3.0 toolchain and
  Linux-4.9/glibc-2.28 sysroot. ELF64 AArch64; interpreter
  `/lib/ld-linux-aarch64.so.1`; only `libc.so.6` in NEEDED; only GLIBC_2.17
  version requirement; no RPATH/RUNPATH; non-executable GNU_STACK.
- Source SHA-256: `f48f3d5a80c16d7927a2c16d85542f16b2ea85b8ac3d6ef58840090a475a9ccc`.
- Private target binary SHA-256:
  `3e1aa386ec7fbf08e3d4f97610604e5d97ddfbe09fee31168232a26288f1396d`.
- Production binary contains no `--test-fd` string. It was not transferred to
  or executed on H700 and is not included in Git/artifacts/releases.

Reproduce host checks with Linux development headers, C compiler and Python 3:

```sh
python3 -m unittest discover -s tests -v
```

The build used the existing tools image ID
`sha256:1c4ddd5655ad020d5e320e2181a04e4356af7c0e70f2be3cd5e901657cd8596b`,
with no network, all capabilities dropped, uid/gid 1000, no-new-privileges,
read-only toolchain/sysroot/source and a private writable output directory.
The compiler/sysroot came from the prior engine work; a clean-room public
toolchain reproduction remains a separate gate.

Target compile command (mounted paths, existing inputs):

```sh
C=/build/toolchains/gcc-8.3/x86_64-aarch64-nextui-linux-gnu/bin/aarch64-nextui-linux-gnu
"$C-gcc" --sysroot=/sysroot -B/sysroot/usr/lib64/ -std=c11 -O2 \
  -Wall -Wextra -Werror -fPIE -pie -static-libgcc -Wl,-z,relro,-z,now \
  -Wl,-rpath-link,/sysroot/usr/lib64 /src/native/rmxp-session.c \
  -o /out/rmxp-session.aarch64
"$C-readelf" -h -l -d -W /out/rmxp-session.aarch64
"$C-readelf" --version-info -W /out/rmxp-session.aarch64
```

## Deferred acceptance

The updated #40 preparation tool supports `install --session` for the reviewed
target helper, includes it in runtime hash checks, and parses optional per-game
`session.conf` as three data lines (event node, first code, second code). The
native metadata is preserved through bounded logging and understood by #41's
exporter. Their combined host integration distinguishes explicit exit 143 from
signal 15 without exposing raw logs. This is not target verification.
Before enabling the
chord, verify loader execution, actual keycodes, hold/release behavior, menu
side effects, save preservation, audio silence and NextUI return on H700.
Test forced-exit fallback only with disposable synthetic content first.
CI activation remains blocked by the credential's missing workflow permission;
the supplied workflow template is inactive. #10 stays open.
