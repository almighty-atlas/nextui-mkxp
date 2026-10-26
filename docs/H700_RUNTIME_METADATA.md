# Read-only H700 library metadata — source-only draft

**Status: OWNER EXECUTED the read-only metadata probe on the RG35XX Pro once (2026-10-26). No device graphics test or library loading was performed by the probe. Further device actions are not authorized by this PR.**

Existing real device baseline: [Issue #1](https://github.com/almighty-atlas/nextui-mkxp/issues/1) and [PR #20](https://github.com/almighty-atlas/nextui-mkxp/pull/20). The private host work in [PR #27](https://github.com/almighty-atlas/nextui-mkxp/pull/27) demonstrated a linked AArch64 / Linux-4.9 triangle *variant* requiring directly only SDL2 and libc. It did not test H700 video. Its privately built SDL2 needs GLIBC symbols up to **2.27**. The installed loader, libc, SDL and GPU library identities remain **UNKNOWN**.

This independent draft adds only a fixed-path probe, host tests and this documentation. It does not modify or require merging PRs #19–#27. It will not create a Pak, load SDL/EGL/GLES, open a GPU device node, change system libraries or launch code automatically.

## Fixed scope

- Existence and session-specific read/write permission tests for **/dev/ion, /dev/fb0, /dev/mali, /dev/mali0, /dev/dri/card0, /dev/dri/renderD128**. These are metadata tests only; no open/ioctl or permissions changes.
- Only fixed candidate files: AArch64 loader (including the BaseOS v1.4.0 harvested `/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1`), libc, libm, libdl, libpthread, SDL2, EGL, GLES and Mali libraries in **/lib, /usr/lib, /mnt/vendor/lib64, /mnt/SDCARD/.system/h700/lib**. No recursive scans, arbitrary paths, home directories, games, saves or Syncthing data.
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

Nine host tests use a temporary probe copy and synthetic fixtures (one tests local BusyBox applets only when BusyBox is installed; otherwise it is explicitly skipped). They verify the BaseOS-harvested AArch64 loader candidate, argument rejection, missing files, fake AArch64 ELF headers, SHA-256, approved symlink resolution, refusal to read private-path symlink targets, filtered `readelf` fields with redaction, and the supported BusyBox `ash`/`awk`/`od`/`readlink`/`sha256sum` code path. Static checks reject mutating and network commands. A native BusyBox host test, if run, proves only the tested host BusyBox version. None of these tests prove the actual H700's BusyBox configuration, runtime library versions or graphics behavior.

## First owner-observed output and next authorization boundary

The owner voluntarily executed the reviewed, metadata-only probe via an existing SSH session and shared stdout. It performed no firmware writes, opened no device node, loaded no GPU library and did not run a Pak. Any further ELF/device/GPU actions need their own scope review. The probe and its output do not authorize software distribution or a graphics test.

The game-free physical graphics test is separate [Issue #22](https://github.com/almighty-atlas/nextui-mkxp/issues/22), not authorized here. Licenses/distribution remain under [PR #19](https://github.com/almighty-atlas/nextui-mkxp/pull/19).

## Acceptance

- [x] Source-only probe and nine host tests (optional BusyBox test skips explicitly when unavailable).
- [ ] Independent source/BusyBox review and CI on current PR head.
- [x] Owner-performed, metadata-only probe run on 2026-10-26 (user-supplied output).
- [x] Owner-observed selected runtime hashes and /dev/ion /dev/mali0 /dev/fb0 access; dynamic ELF/GLIBC versions explicitly UNKNOWN.
- [ ] Independent rights/runtime compatibility assessment.
- [ ] Separate authorization for any on-screen SDL/GLES trial.

Issues #1 and #22 remain open, and all earlier PR branches remain unchanged.


## Owner-observed output — 2026-10-26

Evidence class: **USER-SUPPLIED H700**, one voluntarily performed read-only inventory. This is distinct from the host fixture CI. The script ran successfully on Linux `4.9.170`; `sha256sum` was available but `readelf` was not.

| Installed candidate | SHA-256 reported by owner |
| --- | --- |
| `ld-linux-aarch64.so.1` | `68a35077a50da30312b60706db5ba027c892c3be4cf42f3fd167ac241e8c01a9` |
| `libc.so.6` | `dd80538bfc685542511168f4cde5dcce476c22d310e727578f17cf23eebb6822` |
| `libm.so.6` | `b24316bc659ab74096d8679a9e423c1673082649bf148b513579b5acb4e9294a` |
| `libdl.so.2` | `7f0db218d2126ed6d8df831a24abb0e1b6e96e3952813944a914051ea712440b` |
| `libpthread.so.0` | `cc12f9592e8d130630b7e95a390aa238dfad6d4092615a65c516e3cf93d30aa3` |
| `libEGL.so.1` | `c978b4c900da7490a9fa7f3899adf2991ab53e63a1960634e4c9ff2891b5b157` |
| `libGLESv2.so.2` | `4efb4bc33a428837b00e0a298aabdf38d2f8eec466232f17f0d3b70860d51590` |
| `libmali.so.0` | `b44fd8ba210067b645116d94431e00afc5918e4ac629013aa9f61e40102bb3dc` |

Every readable sampled candidate was reported **ELF64 little-endian AArch64**. The `/lib` and `/usr/lib` aliases of the loader, libc and GPU libraries gave matching hashes; this proves sampled *content equality only*. `/dev/ion`, `/dev/fb0` and `/dev/mali0` reported `present r=yes w=yes` for the active SSH session, without opening those nodes. The probed `/dev/mali` and DRM nodes were UNKNOWN/absent.

Both NextUI SDL2 candidate filenames returned **UNKNOWN (resolved outside fixed system roots; not read)**. They must not be called missing; the probe intentionally declined to hash them. Before modifying an allowlist, inspect only their canonical target **metadata** and determine the narrow real target root.

`readelf` was absent, so provider-version definitions (including whether `GLIBC_2.27` is actually available), DT_NEEDED, symbol exports and the actual NextUI loader/SDL runtime selection are still **UNKNOWN**. The source-built SDL from PR #27 requires up to GLIBC_2.27 indirectly; the owner-provided hashes are not themselves an ABI-compatibility pass. No EGL/ION/pixmap/display functionality was tested.

Next possible *separately user-initiated* non-GPU investigation: examine this already-fingerprinted `libc.so.6` on the user's own trusted development host with host `readelf`, after verifying its SHA-256, and inspect SDL symlink target path metadata without reading the target. Do not upload vendor libraries or add a GPU display test to this PR.
