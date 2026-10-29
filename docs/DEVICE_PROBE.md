# Safe H700 hardware inventory

Issue [#1](https://github.com/almighty-atlas/nextui-mkxp/issues/1): **owner-supplied H700 inventory received; functional runtime tests remain NOT_TESTED.** See [H700 baseline](H700_BASELINE.md).
The executable [tools/probe-h700.sh](../tools/probe-h700.sh) is a fixed-scope,
read-only inventory for the owner's RG35XX Pro. It writes only to terminal output
and needs no elevated privileges. Do not change permissions, enable services or
install tools to make it work. Missing commands/files produce UNKNOWN.

## Manual handoff: one command

Review the script in this PR first. Copy the reviewed `tools/probe-h700.sh` file
using your existing file-transfer/SD-card workflow to the root of the NextUI SD
card as `probe-h700.sh`. Do not place it inside `.system`, install it as a Pak,
run downloaded code through a pipe, or launch any firmware initialization script.
If the card is not already accessible at `/mnt/SDCARD`, stop and report that
UNKNOWN; the probe will not mount it.

From an **already available local terminal or SSH session** on your own device:

```sh
sh /mnt/SDCARD/probe-h700.sh
```

No SSH service, network discovery or connectivity setup is provided or assumed.
If no terminal/SSH session already exists, this handoff is **BLOCKED**; report that
constraint instead of enabling SSH or changing firmware. Running with `sh` also
works on an SD card without executable-file support. No `sudo` is needed; use the
existing session without elevating it. Access flags reflect that session's user.
The script also has a shebang/executable bit for filesystems that support it.

**Deutsch:** Datei und PR zuerst prüfen. Nur in einer bereits verfügbaren
Terminal-/SSH-Sitzung den obigen Befehl ausführen. Ausgabe vor dem Teilen auf
persönliche Angaben prüfen; Firmwareversion und Modell zusätzlich am Gerät
ablesen. Ohne vorhandenes Terminal bleibt der Gerätetest blockiert.

## What is measured, and why

| Field | Evidence / limits |
| --- | --- |
| NextUI release/build | First two sanitized lines of fixed `/mnt/SDCARD/.system/version.txt`. Recorded metadata, not authenticated installed-file identity. Missing file means UNKNOWN; record release from UI manually |
| OS release / model | Only NAME, PRETTY_NAME, VERSION_ID from `/etc/os-release`; never source it. Only known PLATFORM/DEVICE hint values printed. DEVICE is a runner hint, not independent model detection |
| Kernel vs userland | `uname -m` and `-r`, never `-a`/hostname. `getconf LONG_BIT` describes the tool's userland; does not establish every binary's ABI |
| ELF / loader / libc | Decode first 20 bytes of fixed `/bin/sh` with `od`/`awk`: ELF class, byte order, machine. Optional `readelf -l /bin/sh` interpreter and `getconf GNU_LIBC_VERSION`. Never execute loader, `ldd`, library or SD-card binary |
| Libraries | Non-recursive fixed-directory globs for loader/libc, SDL2, EGL/GLES, DRM/GBM, ALSA/OpenAL/PulseAudio; presence only. Includes standard armhf/aarch64 dirs and NextUI's H700 lib dir. No arbitrary path argument or library-loading test |
| Memory/swap | Selected numeric `/proc/meminfo` fields; `/proc/swaps` type/size/used/priority with backing filename suppressed |
| Devices/access | Fixed graphics, framebuffer, audio and input node presence + effective read/write/execute access tests. These are not numeric mode bits, ACL/group inventory, opens or functional tests |
| Input | Only bus/vendor/product/version IDs and recognized handler tokens from `/proc/bus/input/devices`; omit Name, Phys, Sysfs, Uniq, capability dumps and all event streams |
| Pak paths/variables | Fixed NextUI directory presence only, no Pak/game/save names. Explicit documented path-variable allowlist reports set/unset, with all path values suppressed; never used to open files. Terminal sessions may not inherit runner variables |

Available tools are reported by name, not path. No recursive filesystem scan,
process list, Wi-Fi/MAC/IP/SSID, tokens, environment dump, block-device identity,
mount list or arbitrary user-file reads. Data is never evaluated as shell code;
there are no arguments, test-root overrides, sourced scripts or configuration
writes. Only the device nodes' metadata is tested; none is opened. Optional tools
must be the trusted ones already on the terminal's PATH. Probe stdout may be
captured manually by the user, but the probe creates no log file.

## Reference contract (upstream-reported, not device evidence)

NextUI inspected at `5291344b3aceae5fa197437a70824afb41e2d338`:

- [makefile](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/makefile)
  writes release name and build hash into root `SYSTEM/version.txt`.
- [H700 launcher](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/paks/MinUI.pak/launch.sh)
  defines the selected path variables and library paths. It mutates system/runtime
  state and must **not** be sourced or executed for this probe.
- [Device mapper](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/skeleton/SYSTEM/h700/bin/h700-device.sh)
  maps the RG35xxPro hint to `rg35xxpro`; it also has fallbacks, so a hint is not proof.
- [PAKS.md](https://github.com/LoveRetro/NextUI/blob/5291344b3aceae5fa197437a70824afb41e2d338/PAKS.md)
  describes `Tools/<platform>` / `Emus/<platform>`, ROM tags, and standalone limits.

The actual installed firmware can differ. Paths not found are UNKNOWN, never a
reason to mount a card or edit the installation. No upstream code was imported.
The separate license audit in PR #19 is unchanged.

## Unknowns and smallest next checks

- If model/release is missing, record the physical model and NextUI UI version;
  do not scrape vendor binaries or private configuration.
- If userland/ELF/interpreter is UNKNOWN, inspect fixed `/bin/sh` using `readelf`
  on a trusted host from a separately reviewed firmware copy. No on-device
  installation required. A static shell has no PT_INTERP; absence is not proof
  of a missing loader.
- Library filenames and `getconf` do not establish the oldest supported symbol
  version or the real Pak loader resolution. Later inspect an agreed sysroot's
  ELF metadata and actual runner context before choosing a toolchain.
- EGL/GLES, SDL, audio and input **functionality remain NOT_TESTED**, even when
  nodes/libraries exist. They need a separately reviewed, game-free runtime smoke
  test after M0 gates. This issue does not compile or start that test.
- A terminal can lack runner variables. Mark UNKNOWN; do not source launchers or
  create a probe Pak to obtain them. Review the installed firmware's documented
  contract later if needed.

## Existing standalone Pak lifecycle (human checklist)

The probe does not launch, signal or remove Paks. If you already have a trusted,
known-working standalone Pak and choose to observe it, first record its name and
version without game/save paths. Launch through its normal NextUI entry. Exit
using **that Pak's documented exit method**; MENU/POWER/SELECT+START are not
universal standalone exit commands. If it has no known safe exit method, stop
and mark this check BLOCKED instead of force-killing processes or power cycling.
Record return to NextUI and any display/audio/input change; do not alter settings.

Removal is not required for this inventory. To document a safe future removal,
exit the Pak first, verify which files its maintainer says it owns and where saves
live, then use the existing file manager/SD workflow to remove **only that Pak's
folder** from `Tools/h700` or `Emus/h700` if explicitly desired. Do not remove
Roms, Saves, `.userdata`, `.system`, or shared dependencies. If save placement is
unknown, removal remains BLOCKED. No blanket deletion command is provided.

## Redacted results template (attach to issue #1)

- Evidence: **USER-SUPPLIED H700 INVENTORY RECEIVED** on 2026-10-25; see [H700 baseline](H700_BASELINE.md). Runtime hardware checks remain NOT_TESTED.
- Probe commit / date / session type (terminal or existing SSH):
- Physical model / exact installed NextUI release / official or custom source:
- Release-file value versus UI version (match, mismatch, UNKNOWN):
- Kernel architecture / tool userland bitness / `/bin/sh` ELF and interpreter:
- libc hint / libraries present / unresolved ABI or symbol requirements:
- Device-node presence/access / input IDs and handlers:
- Memory/swap numeric facts:
- Pak directory presence / runner variables set or UNKNOWN:
- Existing trusted standalone Pak launch/exit/removal observations or NOT_TESTED:
- Missing commands, unknowns and smallest next verification:
- Redactions applied:
- Reviewed probe output (no extra private logs):

Before posting, remove any unexpected identifying names/paths/release labels.
Do not append full environments, network settings, serials, games, saves, private
logs or screenshots containing such data. Then attach the redacted output and
installed firmware version to issue #1. Owner-supplied inventory has now been summarized in [H700 baseline](H700_BASELINE.md).
The remaining runtime checks and UI confirmation remain open; keep issue #1 open.

## Verification performed in cloud

Commands: `sh -n tools/probe-h700.sh`, `sh tools/probe-h700.sh` (cloud host only),
`python3 -m unittest discover -s tests -v`, `git diff --check`.
Seven fixture tests cover missing files/tools, failing commands, ELF32 big-endian
and ELF64 AArch64, non-ELF data, secret-bearing fields, suppressed environment/path
values, device FIFO not opened, unchanged fixture files, argument rejection,
executable mode, syntax and a static forbidden-command/redirection contract.
Test fixtures rewrite fixed paths in a temporary copy; the production script has
no arbitrary-root feature. Static lexical checks supplement human review; they
are not a general shell security proof.

| Level | Result |
| --- | --- |
| STATIC | PASS: shell syntax, fixture safety contract, whitespace |
| HOST | PASS: seven synthetic fixtures and cloud-host execution; not handheld facts |
| BusyBox runtime / ShellCheck | NOT_TESTED locally: commands unavailable; no packages installed. POSIX shell/BusyBox-compatible syntax and applet options used; CI runs optional checks if installed |
| CI | Workflow added; status is reported separately on the PR |
| H700 inventory | OWNER-SUPPLIED observation documented in [H700 baseline](H700_BASELINE.md); on-device EGL/SDL/audio/input/Pak behavior remains NOT_TESTED |
