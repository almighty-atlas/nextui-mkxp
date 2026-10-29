#!/bin/sh
# SPDX-License-Identifier: MIT
# Container-only batch. /target is a FRESH copy, every other input is read-only.
set -eu
export PATH=/usr/bin:/bin LC_ALL=C LANG=C TZ=UTC
export PKG_CONFIG_LIBDIR=/target/empty-pkgconfig
# Autoconf otherwise starts in cross_compiling=maybe with --host alone and
# probes ./conftest. build_alias is a supported precious configure variable.
export build_alias=x86_64-pc-linux-gnu
unset RUBYOPT RUBYLIB LD_PRELOAD LD_LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH
cd /target
test "$(pwd -P)" = /target
test -f aarch64-linux-fake.rb
grep -q '^CROSS_COMPILING = yes$' Makefile
test ! -e /work/src/ruby-3.1.3/bin/extlibs.rb
if test "${1-full}" != support-only; then
    test ! -e .ext/aarch64-linux/fiddle.so
fi
/work/prefix/bin/ruby --disable=gems -e 'abort unless RUBY_PLATFORM == "x86_64-linux" && RUBY_VERSION == "3.1.3"'

# The reviewed common.mk encs target uses native Ruby + fake.rb, never target Ruby.
# Command-line assignment propagates to the encoding submake; no /usr/lib RPATH.
if test "${1-full}" = full; then
    test ! -d .ext/aarch64-linux/enc
    make -j2 V=1 encs LIBRUBYARG_SHARED=-l:libruby.so.3.1
    printf 'ENCODING_BATCH_BUILD_PASS\n'
else
    test "${1-}" = reuse-encodings || test "${1-}" = support-only
    test -f .ext/aarch64-linux/enc/utf_16le.so
    test -f .ext/aarch64-linux/enc/utf_16be.so
    printf 'EXISTING_ENCODINGS_REUSED\n'
fi

configure_extension() {
    extension=$1
    shift
    module=$extension
    if test "$extension" = date; then module=date_core; fi
    if test -f "/target/.ext/aarch64-linux/$module.so"; then
        printf 'EXISTING_SUPPORT_EXTENSION_REUSED %s\n' "$extension"
        return
    fi
    mkdir -p "/target/ext/$extension"
    cd "/target/ext/$extension"
    /work/prefix/bin/ruby --disable=gems -I/target -r/target/aarch64-linux-fake \
    -I/work/src/ruby-3.1.3/lib \
    -e 'require "rbconfig"; RbConfig.fire_update!("LIBRUBYARG_SHARED", "-l:libruby.so.3.1"); RbConfig.fire_update!("RPATHFLAG", ""); $0 = ARGV.first; load ARGV.shift' \
    "/work/src/ruby-3.1.3/ext/$extension/extconf.rb" \
    "--srcdir=/work/src/ruby-3.1.3/ext/$extension" "$@"
    make -j2 V=1 LIBRUBYARG_SHARED=-l:libruby.so.3.1
}

# Bundled sources are already in the official Ruby archive. No extlibs download.
if test "${1-full}" != support-only; then
    configure_extension fiddle --enable-bundled-libffi
    printf 'FIDDLE_BATCH_BUILD_PASS\n'
fi
# StringIO is unconditionally required by high-level Psych; Date covers timestamps.
configure_extension stringio
configure_extension date
printf 'PSYCH_SUPPORT_BATCH_BUILD_PASS\n'
