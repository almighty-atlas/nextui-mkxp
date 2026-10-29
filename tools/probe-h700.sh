#!/bin/sh
# Read-only fixed-scope inventory. No arguments, root, network, config sourcing,
# recursive scans, device opens, executable launches from the SD card, or writes.
# Optional tools are resolved on the existing trusted terminal PATH.
LC_ALL=C
export LC_ALL
set -f
if [ "$#" -ne 0 ]; then
    printf '%s\n' 'Usage: sh tools/probe-h700.sh (no arguments or custom paths)' >&2
    exit 2
fi
have() { command -v "$1" >/dev/null 2>&1; }
section() { printf '\n== %s ==\n' "$1"; }
unknown() { printf '%s\n' 'UNKNOWN (unavailable, unreadable or unsupported)'; }
# Fixed text inputs only; data is never interpreted as shell code.
text_fields() {
    if [ -r "$1" ] && [ -f "$1" ] && have awk; then
        awk "$2" "$1" 2>/dev/null || unknown
    else
        unknown
    fi
}
# Presence/access checks never open a device or enumerate directory contents.
presence() {
    if [ -e "$1" ]; then
        probe_r=no; probe_w=no; probe_x=no
        [ ! -r "$1" ] || probe_r=yes
        [ ! -w "$1" ] || probe_w=yes
        [ ! -x "$1" ] || probe_x=yes
        printf '%s: present; access r=%s w=%s x=%s\n' "$1" "$probe_r" "$probe_w" "$probe_x"
    else
        printf '%s: UNKNOWN (absent or inaccessible)\n' "$1"
    fi
}
printf '%s\n' 'H700 inventory v1; device evidence NOT_TESTED until reviewed by a human.'
printf '%s\n' 'Presence/access is not proof of working graphics, audio, input or Pak launch.'
section 'RELEASE / MODEL'
# NextUI makefile writes release name + build hash at the root .system level.
printf '%s\n' 'NextUI recorded release/build (/mnt/SDCARD/.system/version.txt; not authenticated):'
# shellcheck disable=SC2016 # AWK program is intentionally passed literally; $fields belong to awk.
text_fields /mnt/SDCARD/.system/version.txt '
 NR <= 2 { gsub(/[^A-Za-z0-9 ._+()\/-]/, "?"); print substr($0,1,120); n++ }
 END { if (!n) print "UNKNOWN (empty release file)" }'
printf '%s\n' 'OS identification (not the NextUI release):'
# shellcheck disable=SC2016 # AWK program is intentionally passed literally; $fields belong to awk.
text_fields /etc/os-release '
 /^(NAME|VERSION_ID|PRETTY_NAME)=/ { gsub(/[^A-Za-z0-9 ="._+()\/-]/, "?"); print substr($0,1,120); n++ }
 END { if (!n) print "UNKNOWN (no selected OS fields)" }'
printf 'PLATFORM hint: '
case ${PLATFORM-} in h700) printf 'h700\n';; *) unknown;; esac
printf 'DEVICE hint: '
case ${DEVICE-} in
    rg35xxpro|rg35xxplus|rg35xxh|rg35xxsp|rg28xx|rg34xx|rg34xxsp|rg40xxv|rg40xxh|rgcubexx|rgsp)
        printf '%s (runner hint; confirm physical model manually)\n' "$DEVICE";;
    *) unknown;;
esac
section 'KERNEL / USERLAND / EXECUTABLE ABI'
# uname -a would disclose hostname; only request architecture and release.
for probe_flag in -m -r; do
    printf 'uname %s: ' "$probe_flag"
    if have uname; then uname "$probe_flag" 2>/dev/null || unknown; else unknown; fi
done
printf 'getconf LONG_BIT (tool userland hint): '
if have getconf; then getconf LONG_BIT 2>/dev/null || unknown; else unknown; fi
printf 'getconf GNU_LIBC_VERSION (tool libc hint): '
if have getconf; then getconf GNU_LIBC_VERSION 2>/dev/null || unknown; else unknown; fi
printf '%s\n' '/bin/sh ELF header (does not establish the ABI of every installed binary):'
if have od && have awk && [ -f /bin/sh ] && [ -r /bin/sh ]; then
    # Decimal bytes: ELF magic, EI_CLASS, EI_DATA, e_machine at offsets 18/19.
    probe_header=$(od -An -t u1 -N 20 /bin/sh 2>/dev/null)
    printf '%s\n' "$probe_header" | awk '
    { for (i=1;i<=NF;i++) b[++n]=$i }
    END {
      if (n!=20 || b[1]!=127 || b[2]!=69 || b[3]!=76 || b[4]!=70) {
        print "UNKNOWN (not a readable ELF header)"; exit
      }
      c=(b[5]==1 ? "ELF32" : (b[5]==2 ? "ELF64" : "UNKNOWN"))
      e=(b[6]==1 ? "little" : (b[6]==2 ? "big" : "UNKNOWN"))
      m=(b[6]==1 ? b[19]+256*b[20] : (b[6]==2 ? 256*b[19]+b[20] : -1))
      a=(m==183 ? "AArch64" : (m==40 ? "ARM" : "other/UNKNOWN"))
      printf "class=%s endian=%s e_machine=%d (%s)\n",c,e,m,a
    }'
else unknown; fi
printf '%s\n' '/bin/sh requested interpreter (if dynamic and readelf available):'
if have readelf && have awk && [ -f /bin/sh ] && [ -r /bin/sh ]; then
    readelf -l /bin/sh 2>/dev/null | awk '
      /Requesting program interpreter:/ { gsub(/[^A-Za-z0-9 \/:._\[\]-]/,"?"); print; n++ }
      END { if (!n) print "UNKNOWN (no PT_INTERP reported; static or unavailable)" }'
else unknown; fi
section 'MEMORY / SWAP (no backing filenames)'
# shellcheck disable=SC2016 # AWK program is intentionally passed literally; $fields belong to awk.
text_fields /proc/meminfo '
 /^(MemTotal|MemAvailable|MemFree|SwapTotal|SwapFree):/ && $2 ~ /^[0-9]+$/ {
   print $1, $2, "kB"; n++ }
 END { if (!n) print "UNKNOWN (no selected memory fields)" }'
# shellcheck disable=SC2016 # AWK program is intentionally passed literally; $fields belong to awk.
text_fields /proc/swaps '
 NR>1 && NF==5 && $3 ~ /^[0-9]+$/ && $4 ~ /^[0-9]+$/ && $5 ~ /^-?[0-9]+$/ {
   t=($2=="file" || $2=="partition" ? $2 : "UNKNOWN")
   printf "swap type=%s size_kB=%s used_kB=%s priority=%s\n", t,$3,$4,$5; n++ }
 END { if (!n) print "No swap entries reported (or format unavailable)" }'
section 'DEVICE NODE PRESENCE / CURRENT ACCESS'
for probe_node in /dev/dri/card0 /dev/dri/card1 /dev/dri/renderD128 /dev/fb0 /dev/snd/controlC0 /dev/snd/pcmC0D0p /dev/input/event0 /dev/input/js0; do
    presence "$probe_node"
done
printf '%s\n' 'Access flags reflect this session; no node was opened or permissions changed.'
section 'INPUT DESCRIPTORS (no names, Phys, Uniq or event streams)'
# shellcheck disable=SC2016 # AWK program is intentionally passed literally; $fields belong to awk.
text_fields /proc/bus/input/devices '
 /^I: Bus=[0-9A-Fa-f]+ Vendor=[0-9A-Fa-f]+ Product=[0-9A-Fa-f]+ Version=[0-9A-Fa-f]+$/ {print; n++}
 /^H: Handlers=/ {
   printf "handlers:"; for(i=2;i<=NF;i++) {
     h=$i; sub(/^Handlers=/,"",h)
     if(h ~ /^(event[0-9]+|js[0-9]+|kbd|mouse[0-9]+|mousedev)$/) printf " %s",h
   }; print ""
 }
 END { if (!n) print "UNKNOWN (no selected input IDs)" }'
section 'LOADER / LIBRARY CANDIDATES (metadata only; no loading)'
# Only fixed system directories and relevant basename patterns, no recursion.
# Re-enable globbing here only; never expand a path supplied by the caller.
set +f
probe_count=0
for probe_dir in /lib /lib64 /lib/aarch64-linux-gnu /lib/arm-linux-gnueabihf /usr/lib /usr/lib64 /usr/lib/aarch64-linux-gnu /usr/lib/arm-linux-gnueabihf /mnt/SDCARD/.system/h700/lib; do
    for probe_lib in "$probe_dir"/ld-linux*.so* "$probe_dir"/ld-musl-*.so* "$probe_dir"/libc.so* "$probe_dir"/libSDL2*.so* "$probe_dir"/libEGL*.so* "$probe_dir"/libGLES*.so* "$probe_dir"/libdrm*.so* "$probe_dir"/libgbm*.so* "$probe_dir"/libasound*.so* "$probe_dir"/libopenal*.so* "$probe_dir"/libpulse*.so*; do
        [ -f "$probe_lib" ] || continue
        # Restrict names to printable library characters, even on unusual media.
        probe_name=${probe_lib##*/}
        case $probe_name in *[!A-Za-z0-9._+-]*) continue;; esac
        printf '%s\n' "$probe_lib"
        probe_count=$((probe_count + 1))
    done
done
set -f
[ "$probe_count" -ne 0 ] || unknown
printf '%s\n' 'Library versions/ABI/symbol compatibility and actual loader search order: UNKNOWN.'
section 'NEXTUI / PAK DIRECTORY PRESENCE (no game or Pak names)'
for probe_dir in /mnt/SDCARD /mnt/sdcard /mnt/SDCARD/.system/h700 /mnt/SDCARD/Emus/h700 /mnt/SDCARD/Tools/h700 /mnt/SDCARD/.userdata/h700; do
    presence "$probe_dir"
done
section 'DOCUMENTED RUNNER VARIABLE PRESENCE (values suppressed)'
# Explicit allowlist; no eval, env, printenv, set dump, or variable path reads.
for probe_value in "SDCARD_PATH=${SDCARD_PATH:+set}" "BIOS_PATH=${BIOS_PATH:+set}" "ROMS_PATH=${ROMS_PATH:+set}" "SAVES_PATH=${SAVES_PATH:+set}" "CHEATS_PATH=${CHEATS_PATH:+set}" "SYSTEM_PATH=${SYSTEM_PATH:+set}" "CORES_PATH=${CORES_PATH:+set}" "USERDATA_PATH=${USERDATA_PATH:+set}" "LOGS_PATH=${LOGS_PATH:+set}"; do
    case $probe_value in *=set) printf '%s (value suppressed)\n' "$probe_value";;
        *) printf '%sUNKNOWN (not inherited in this session)\n' "$probe_value";; esac
done
section 'TOOL AVAILABILITY'
for probe_tool in awk od uname getconf readelf file; do
    if have "$probe_tool"; then printf '%s: available\n' "$probe_tool"; else printf '%s: UNKNOWN (missing)\n' "$probe_tool"; fi
done
section 'REMAINING UNKNOWN / HANDOFF'
printf '%s\n' 'Confirm exact physical model and installed NextUI release in the UI.'
printf '%s\n' 'If ELF/interpreter is UNKNOWN, inspect /bin/sh with readelf on a trusted host from a separately reviewed firmware copy; do not install tools here.'
printf '%s\n' 'Functional EGL/GLES/SDL/audio/input, library symbol floor and Pak lifecycle: NOT_TESTED.'
printf '%s\n' 'Review/redact output before sharing; do not add environment dumps or private logs.'
exit 0
