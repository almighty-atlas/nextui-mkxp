# Safe H700 hardware inventory

**Only run on your own RG35XX Pro with NextUI.** This is a read-only starting point for M0: it does not install packages, require `sudo`, change system settings, or modify files. Missing commands are expected on stripped-down firmware.

Run from an available SSH/terminal session, copy the output into the hardware-baseline issue after reviewing it for identifying names/paths. **Do not upload full environment variables, Wi-Fi configurations, network identifiers, secrets or game files.**

```sh
printf '\n== VERSION / ABI ==\n'
uname -a
uname -m
getconf LONG_BIT 2>/dev/null || true
cat /etc/os-release 2>/dev/null || true
printf '\n== MEMORY ==\n'
grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree):' /proc/meminfo
cat /proc/swaps 2>/dev/null || true
printf '\n== GRAPHICS DEVICES ==\n'
ls -l /dev/dri /dev/fb0 2>/dev/null || true
printf '\n== LIBRARY PATHS ==\n'
ls -ld /lib /lib64 /usr/lib /usr/lib64 2>/dev/null || true
printf '\n== TOOLS ==\n'
for c in ldd readelf file gcc glxinfo es2_info; do
  if command -v "$c" >/dev/null 2>&1; then
    command -v "$c"
  fi
done
printf '\n== SD CARD CAPACITY ==\n'
df -h 2>/dev/null || true
```

Also manually record the **NextUI version**, exact device model, available controller buttons, observed behavior of launching/exiting one **existing, known-working** standalone Pak, and whether the firmware uses an official stable build.

## Evidence template

- Date / NextUI version / model / firmware source:
- `uname -m` / userland bitness / relevant ELF interpreter:
- Device nodes / verified GLES + EGL + SDL library paths:
- Audio devices/backend and input API:
- Memory total / available / swap:
- Can run standalone Pak without `sudo`:
- Unavailable commands, ambiguity and blockers:
- Redactions made before attaching logs:

A listing alone is **not** proof that EGL/GLES/DRM works: a separate small runtime smoke test must confirm that.
