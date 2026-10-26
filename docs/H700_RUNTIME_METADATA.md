# Read-only H700 library metadata — source-only draft

**Status: NOT EXECUTED on the RG35XX Pro. No device run is authorized by this PR.**

Existing real device baseline: [Issue #1](https://github.com/almighty-atlas/nextui-mkxp/issues/1) and [PR #20](https://github.com/almighty-atlas/nextui-mkxp/pull/20). The private host work in [PR #27](https://github.com/almighty-atlas/nextui-mkxp/pull/27) demonstrated a linked AArch64 / Linux-4.9 triangle *variant* requiring directly only SDL2 and libc. It did not test H700 video. Its privately built SDL2 needs GLIBC symbols up to **2.27**. The installed loader, libc, SDL and GPU library identities remain **UNKNOWN**.

This independent draft adds only a fixed-path probe, host tests and this documentation. It does not modify or require merging PRs #19–#27. It will not create a Pak, load SDL/EGL/GLES, open a GPU device node, change system libraries or launch code automatically.

## Fixed scope

- Existence and session-specific read/write permission tests for **/dev/ion, /dev/fb0, /dev/mali, /dev/mali0, /dev/dri/card0, /dev/dri/renderD128**. These are metadata tests only; no open/ioctl or permissions changes.
- Only fixed candidate files: AArch64 loader, libc, libm, libdl, libpthread, SDL2, EGL, GLES and Mali libraries in **/lib, /usr/lib, /mnt/vendor/lib64, /mnt/SDCARD/.system/h700/lib**. No recursive scans, arbitrary paths, home directories, games, saves or Syncthing data.
- If pre-installed: od+awk interpret the first 20 ELF header bytes, sha256sum computes hashes, and optional readelf prints only DT_NEEDED basenames, GLIBC version needs, GLIBC provider-version definitions and presence (not contents) of RPATH/RUNPATH.
- Symlinks and ancestor paths are resolved with readlink -f; only candidates resolving inside the allowlisted system/NextUI library roots are read. Canonical paths and symlink targets are not printed. Missing commands result in **UNKNOWN**, not invented compatibility.
- The prior H700 inventory did **not** find readelf. No tools are to be installed merely for this probe. No ldd or loader execution.
- No private logs, process environments, device IDs, network data, raw firmware, symbol-table dumps, temp files, SSH service changes or output-file writes.

## Limits

Candidate hashes do **not** identify what a NextUI-launched Pak will actually load. An SSH shell may have a different library-search configuration. A libc that defines GLIBC_2.27 is also **not** proof of SDL runtime compatibility: actual loader/libc pairing, full dependencies, dlopen closure, vendor EGL/GLES/ION/pixmap extensions, screen output and clean return still require separate evidence.

If readelf remains unavailable, any further host-side ELF inspection of specifically approved stock firmware copies requires separate authorization. Do not ask the owner to upload binary libraries or complete firmware by default. Available stock images do not establish redistribution rights.

## Host-only validation

Run on the **development host only**:

- sh -n tools/probe-h700-runtime.sh
- python3 -I -B -m unittest discover -s tests -v

Eight host tests use a temporary probe copy and synthetic fixtures (one tests local BusyBox applets only when BusyBox is installed; otherwise it is explicitly skipped). They verify argument rejection, missing files, fake AArch64 ELF headers, SHA-256, approved symlink resolution, refusal to read private-path symlink targets, filtered `readelf` fields with redaction, and the supported BusyBox `ash`/`awk`/`od`/`readlink`/`sha256sum` code path. Static checks reject mutating and network commands. A native BusyBox host test, if run, proves only the tested host BusyBox version. None of these tests prove the actual H700's BusyBox configuration, runtime library versions or graphics behavior.

## Future handoff: NOT AUTHORIZED YET

Review the exact source and CI result first. A later, **separate human approval** is required even for running this metadata-only script in the existing SSH session. At that future point the owner can transfer the reviewed file without modifying firmware or .system; redact stdout before sharing. The current PR deliberately contains **no device-execution instruction**.

The game-free physical graphics test is separate [Issue #22](https://github.com/almighty-atlas/nextui-mkxp/issues/22), not authorized here. Licenses/distribution remain under [PR #19](https://github.com/almighty-atlas/nextui-mkxp/pull/19).

## Acceptance

- [x] Source-only probe and eight host tests (optional BusyBox test skips explicitly when unavailable).
- [ ] Independent source/BusyBox review and CI on current PR head.
- [ ] Separate owner authorization for read-only device metadata execution.
- [ ] Owner-observed ABI/runtime metadata with explicit UNKNOWN fields.
- [ ] Independent rights/runtime compatibility assessment.
- [ ] Separate authorization for any on-screen SDL/GLES trial.

Issues #1 and #22 remain open, and all earlier PR branches remain unchanged.
