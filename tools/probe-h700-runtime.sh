#!/bin/sh
# H700 runtime-library metadata inventory v1. Review source before any device run.
# Fixed candidates only. Never execute target ELF/loader/ldd or open GPU nodes.
LC_ALL=C; export LC_ALL
set -f
if [ "$#" -ne 0 ]; then
    printf '%s\n' 'No arguments accepted.' >&2
    exit 2
fi
have() { command -v "$1" >/dev/null 2>&1; }
unknown() { printf '%s\n' 'UNKNOWN'; }

printf '%s\n' 'H700 runtime metadata inventory v1 — NOT_TESTED on physical H700.'
printf '%s\n' 'Fixed system-library candidates, no device opens, no file modifications.'
printf 'kernel_release: '
if have uname; then uname -r 2>/dev/null || unknown; else unknown; fi
printf 'sha256sum_available: '
if have sha256sum; then printf 'yes\n'; else printf 'no\n'; fi
printf 'readelf_available: '
if have readelf; then printf 'yes\n'; else printf 'no\n'; fi
printf '\n== DEVICE NODE METADATA ==\n'
for node in /dev/ion /dev/fb0 /dev/mali /dev/mali0 /dev/dri/card0 /dev/dri/renderD128; do
    if [ -e "$node" ]; then
        r=no; w=no
        [ ! -r "$node" ] || r=yes
        [ ! -w "$node" ] || w=yes
        printf '%s: present r=%s w=%s (not opened)\n' "$node" "$r" "$w"
    else
        printf '%s: UNKNOWN (absent or inaccessible)\n' "$node"
    fi
done

# Canonicalize symlink targets when supported, but never print their contents
# or read symlink targets outside fixed system/NextUI library directories.
within_system_roots() {
    case "$1" in
        /lib/*|/usr/lib/*|/mnt/vendor/lib64/*|/mnt/SDCARD/.system/h700/lib/*) return 0 ;;
        *) return 1 ;;
    esac
}

elf_header() {
    if ! have od || ! have awk; then unknown; return; fi
    od -An -tu1 -N20 "$1" 2>/dev/null | awk '
      {for(i=1;i<=NF;i++) b[++n]=$i}
      END {
        if(n!=20 || b[1]!=127 || b[2]!=69 || b[3]!=76 || b[4]!=70) {print "UNKNOWN (not ELF)"; exit}
        e=b[6]==1 ? "little" : (b[6]==2 ? "big" : "UNKNOWN")
        c=b[5]==2 ? "ELF64" : (b[5]==1 ? "ELF32" : "UNKNOWN")
        m=b[6]==1 ? b[19]+256*b[20] : 256*b[19]+b[20]
        printf "%s %s machine=%d%s\n",c,e,m,(m==183 ? " AArch64" : "")
      }'
}

# Optional readelf reveals only allowlisted NEEDED sonames/GLIBC version needs.
# Never print RPATH contents, symbol tables, user paths or entire ELF headers.
elf_details() {
    if ! have readelf || ! have awk; then
        printf '%s\n' '  dynamic_dependencies_and_glibc_needs: UNKNOWN (readelf/awk unavailable)'
        return
    fi
    printf '%s\n' '  DT_NEEDED (selected basenames; no runtime search paths):'
    readelf -W -d "$1" 2>/dev/null | awk '
      /\(NEEDED\)/ {
        if(match($0,/\[[^]]+\]/)) {
          x=substr($0,RSTART+1,RLENGTH-2)
          if(x ~ /^lib[A-Za-z0-9_.+-]+$/) print "    " x
          else print "    REDACTED"
          n++
        }
      }
      END {if(!n) print "    UNKNOWN (none reported or unsupported)"}'
    printf '%s\n' '  GLIBC version needs (not installed provider versions):'
    readelf -W -V "$1" 2>/dev/null | awk '
      /^Version needs section/ {needs=1; next}
      /^Version (definition|symbols) section/ {needs=0}
      needs && /Name: GLIBC_[0-9]+\.[0-9]+/ {
        for(i=1;i<=NF;i++) if($i=="Name:" && $(i+1) ~ /^GLIBC_[0-9]+\.[0-9]+(\.[0-9]+)?$/) {
          v=$(i+1); if(!seen[v]++) print "    " v; n++
        }
      }
      END {if(!n) print "    UNKNOWN (none reported or unsupported)"}'
    printf '%s\n' '  GLIBC provider version definitions (not runtime verification):'
    readelf -W -V "$1" 2>/dev/null | awk '
      /^Version definition section/ {defs=1; next}
      /^Version (needs|symbols) section/ {defs=0}
      defs && /Name: GLIBC_[0-9]+\.[0-9]+/ {
        for(i=1;i<=NF;i++) if($i=="Name:" && $(i+1) ~ /^GLIBC_[0-9]+\.[0-9]+(\.[0-9]+)?$/) {
          v=$(i+1); if(!seen[v]++) print "    " v; n++
        }
      }
      END {if(!n) print "    UNKNOWN (none reported or unsupported)"}'
    printf '  runtime_search_paths: '
    if readelf -W -d "$1" 2>/dev/null | awk '/\((RPATH|RUNPATH)\)/ {found=1} END {exit !found}'; then
        printf '%s\n' 'PRESENT (values suppressed)'
    else
        printf '%s\n' 'UNKNOWN/none'
    fi
}

printf '\n== FIXED LIBRARY CANDIDATES ==\n'
for candidate in \
    /lib/ld-linux-aarch64.so.1 \
    /lib/aarch64-linux-gnu/ld-linux-aarch64.so.1 \
    /lib/aarch64-linux-gnu/libc.so.6 \
    /lib/aarch64-linux-gnu/libm.so.6 \
    /lib/aarch64-linux-gnu/libdl.so.2 \
    /lib/aarch64-linux-gnu/libpthread.so.0 \
    /usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1 \
    /usr/lib/aarch64-linux-gnu/libc.so.6 \
    /usr/lib/aarch64-linux-gnu/libm.so.6 \
    /usr/lib/aarch64-linux-gnu/libdl.so.2 \
    /usr/lib/aarch64-linux-gnu/libpthread.so.0 \
    /lib/libEGL.so.1 /lib/libGLESv2.so.2 /lib/libmali.so.0 \
    /usr/lib/libEGL.so.1 /usr/lib/libGLESv2.so.2 /usr/lib/libmali.so.0 \
    /usr/lib/aarch64-linux-gnu/libEGL.so.1 \
    /usr/lib/aarch64-linux-gnu/libGLESv2.so.2 \
    /mnt/vendor/lib64/libmali.so.0 \
    /mnt/vendor/lib64/libEGL.so.1 \
    /mnt/vendor/lib64/libGLESv2.so.2 \
    /mnt/SDCARD/.system/h700/lib/libSDL2-2.0.so.0 \
    /mnt/SDCARD/.system/h700/lib/libSDL2-2.0.so.0.2800.5
 do
    printf '%s\n' "$candidate"
    if [ ! -f "$candidate" ] || [ ! -r "$candidate" ]; then
        printf '%s\n' '  status: UNKNOWN (not a readable regular file)'
        continue
    fi
    # No canonicalizer => no file reads: the input or one ancestor could
    # resolve via a symlink into a private/user-controlled location.
    if ! have readlink; then
        printf '%s\n' '  status: UNKNOWN (readlink -f unavailable; not read)'
        continue
    fi
    resolved=$(readlink -f "$candidate" 2>/dev/null) || resolved=
    if [ -z "$resolved" ] || ! within_system_roots "$resolved" || [ ! -f "$resolved" ]; then
        printf '%s\n' '  status: UNKNOWN (unresolved or outside fixed system roots; not read)'
        continue
    fi
    printf '%s\n' '  status: readable system candidate (not loaded)'
    printf '  ELF: '; elf_header "$candidate"
    printf '  sha256: '
    if have sha256sum && have awk; then
        sha256sum "$candidate" 2>/dev/null | awk '
        length($1)==64 && $1 !~ /[^0-9a-fA-F]/ {print $1; n++}
        END {if(!n) print "UNKNOWN (sha256sum unavailable or failed)"}'
    else
        unknown
    fi
    elf_details "$candidate"
 done
printf '\n%s\n' 'Installed loader resolution, ABI compatibility and working graphics remain UNKNOWN.'
printf '%s\n' 'Review and redact stdout before sharing. No raw libraries, logs, paths to saves or network data.'
