#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline private GNU-source sysroot recipe for Issue #26; never runs target code."""
import argparse
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import issue_26_sandbox as gate

# Explicit host executables only, no PATH lookup or network fetchers. OS tools
# and their interpreters/shared libraries are the trusted bootstrap boundary.
HOST_TOOLS='''sh bash make gcc cc g++ c++ as ld ar nm ranlib objcopy objdump readelf
sed grep egrep fgrep awk sort head tail tr cut find cat mkdir cp ln mv rm chmod
touch install printf date expr dirname basename pwd uname readlink realpath test
cmp diff wc uniq od tee xargs yes sleep echo perl python3 gzip bzip2 xz tar patch
rmdir file strings id ls'''.split()
CROSS_TOOLS='''gcc cc gcc-8.3.0 cpp g++ c++ as ld ld.bfd ar nm ranlib strip objcopy
objdump readelf strings gcc-ar gcc-nm gcc-ranlib'''.split()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','archives','compiler','compiler-archive'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--lock',type=Path,default=Path(__file__).resolve().parents[1]/'docs/build/issue-26-inputs.json')
    a=p.parse_args();lock=json.loads(a.lock.read_text());r=a.workspace.resolve()
    for name,value in vars(a).items():
        if isinstance(value,Path):setattr(a,name,value.resolve())
    if r.exists():raise ValueError('workspace must be fresh')
    gate.verify_archive_tree(a.compiler_archive,lock['compiler']['sha256'],a.compiler)
    r.mkdir(parents=True);records={}
    for name in HOST_TOOLS:
        records[name]=gate.tool_record('/usr/bin/'+name,'explicit trusted OS bootstrap',
                                     reviewed_script=name in ('egrep','fgrep'))
    for filename,item in lock['archives'].items():
        gate.extract(a.archives/filename,item['sha256'],r/'source'/filename.split('.tar')[0])
    gate.farm(r/'tools',records)
    env=gate.environment(r,r/'tools')
    def run(label,argv,cwd):
        result=gate.checked_run(argv,cwd,env,records,r/'logs',label)
        print(label,result['exit_code'],flush=True)
        if result['exit_code']:raise ValueError('build failed: '+label+'; inspect private log')
    for name,flags in [('m4-1.4.21',[]),('bison-3.8.2',[]),
                       ('gawk-5.3.2',['--without-readline','--without-libsigsegv']),('make-4.3',[])]:
        build=r/('build-'+name);build.mkdir()
        run(name+'-configure',['/usr/bin/sh',r/'source'/name/name/'configure',
                              '--prefix='+str(r/'native'),'--disable-nls',*flags],build)
        make=records['make']['path']
        run(name+'-make',[make,'-j2'],build)
        run(name+'-install',[make,'install'],build)
        for tool in ('m4','bison','gawk','make'):
            native=r/'native/bin'/tool
            if native.exists():records[tool]=gate.tool_record(native,'private hash-locked GNU source build')
        gate.farm(r/'tools',records)
        if name == 'm4-1.4.21':
            run('m4-version', [records['m4']['path'], '--version'], build)
            if not (r/'logs/m4-version.log').read_text().startswith('m4 (GNU M4) 1.4.21\n'):
                raise ValueError('native m4 version mismatch')
            smoke = r/'m4-smoke.m4'
            smoke.write_text("define(`answer',`42')answer\n")
            run('m4-smoke', [records['m4']['path'], smoke], build)
            if (r/'logs/m4-smoke.log').read_text() != '42\n':
                raise ValueError('native m4 macro expansion mismatch')
    base=a.compiler/'x86_64-aarch64-nextui-linux-gnu'
    for name in CROSS_TOOLS:
        path=base/'bin'/('aarch64-nextui-linux-gnu-'+name)
        # Reviewed pinned CT-ng wrapper: CTNG_LD_IS selects bfd/gold. The fresh
        # environment omits that variable, so it execs its sibling ld.bfd.
        records[path.name]=gate.tool_record(path,'verified GCC release host executable; ld selector reviewed',
                                           reviewed_script=name=='ld')
    gate.farm(r/'tools',records)
    (r/'host-tools.json').write_text(json.dumps(records,indent=2)+'\n')
    cc=base/'bin/aarch64-nextui-linux-gnu-gcc'
    env=gate.environment(r,r/'tools',{'CC':str(cc),'BUILD_CC':'/usr/bin/gcc'})
    make=records['make']['path'];kernel=r/'build-linux';kernel.mkdir()
    run('linux-headers',[make,'-C',r/'source/linux-4.9.170/linux-4.9.170','O='+str(kernel),
        'ARCH=arm64','HOSTCC=/usr/bin/gcc','CC='+str(cc),
        'INSTALL_HDR_PATH='+str(r/'kernel-headers'),'headers_install'],kernel)
    build=r/'build-glibc';build.mkdir()
    run('glibc-configure',['/usr/bin/sh',r/'source/glibc-2.28/glibc-2.28/configure',
        '--build=x86_64-pc-linux-gnu','--host=aarch64-nextui-linux-gnu','--prefix=/usr',
        '--with-headers='+str(r/'kernel-headers/include'),'--enable-kernel=4.9.0',
        '--disable-werror','--disable-nscd'],build)
    if 'cross-compiling = yes' not in (build/'config.make').read_text():
        raise ValueError('refuse install: cross-compiling is not yes')
    run('glibc-make',[make,'-j2'],build)
    run('glibc-install',[make,'install_root='+str(r/'sysroot'),'install'],build)
    shutil.copytree(r/'kernel-headers/include',r/'sysroot/usr/include',dirs_exist_ok=True)
    # Metadata only; the caller must review it before the post-build crosscheck.
    manifest={'source_lock_sha256':gate.sha256(a.lock),
              'sysroot_tree_sha256':gate.tree_digest(r/'sysroot'),
              'target_execution':'NEVER','distribution':'BLOCKED'}
    (r/'sysroot-provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(1)
