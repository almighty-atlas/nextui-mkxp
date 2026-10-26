#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Private host-only post-build crosscheck. No fetching or target execution.

The sysroot is built first with the commands in issue-26-linux49-mali.md.
The reviewed host-tool manifest is local to that build, never a remote input.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import issue_26_sandbox as gate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','compiler','compiler-archive','records','sysroot','sdl','triangle','api'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sysroot-tree-sha256',required=True,
                   help='reviewed digest from the private libc build provenance')
    p.add_argument('--lock',type=Path,default=Path(__file__).resolve().parents[1]/'docs/build/issue-26-inputs.json')
    a=p.parse_args();lock=json.loads(a.lock.read_text())
    for name,value in vars(a).items():
        if isinstance(value,Path):setattr(a,name,value.resolve())
    work=a.workspace.resolve()
    if work.exists():raise ValueError('use a fresh private crosscheck workspace')
    if not re.fullmatch('[0-9a-f]{64}',a.sysroot_tree_sha256) or gate.tree_digest(a.sysroot)!=a.sysroot_tree_sha256:
        raise ValueError('changed/unknown rebuilt sysroot provenance')
    # The compiler root argument is the archive's parent extraction directory.
    print('Checking compiler archive and every extracted input',flush=True)
    count=gate.verify_archive_tree(a.compiler_archive,lock['compiler']['sha256'],a.compiler)
    if gate.tree_digest(a.sdl)!=lock['sdl']['tree_sha256']:raise ValueError('changed SDL source tree')
    source=gate.check_file(a.triangle,lock['triangle']['sha256'],[a.triangle.parent])
    for h in lock['khronos']:gate.check_file(a.api/h['path'],h['sha256'],[a.api])
    records=json.loads(a.records.read_text());work.mkdir(parents=True)
    # A post-build subset: exclude debugger/populate/ldd/gcov wrappers.
    records={name:r for name,r in records.items() if not name.startswith('aarch64-') or
             name.removeprefix('aarch64-nextui-linux-gnu-') in
             {'gcc','cc','gcc-8.3.0','cpp','g++','c++','as','ld','ld.bfd','ar','nm',
              'ranlib','strip','objcopy','objdump','readelf','strings','gcc-ar','gcc-nm','gcc-ranlib'}}
    gate.farm(work/'tools',records)
    (work/'selected-host-tools.json').write_text(json.dumps(records,indent=2)+'\n')
    cc=a.compiler/'x86_64-aarch64-nextui-linux-gnu/bin/aarch64-nextui-linux-gnu-gcc'
    sysroot=a.sysroot.resolve();libs=sysroot/'usr/lib64'
    gcc_headers=cc.parents[1]/'lib/gcc/aarch64-nextui-linux-gnu/8.3.0'
    env=gate.environment(work,work/'tools',{'CC':str(cc),'BUILD_CC':'/usr/bin/gcc',
        'PKG_CONFIG_LIBDIR':str(work/'empty-pkgconfig'),'PKG_CONFIG_SYSROOT_DIR':str(sysroot)})
    (work/'empty-pkgconfig').mkdir()
    logs=work/'logs'
    def run(label,argv,cwd=work,expected=0):
        result=gate.checked_run(argv,cwd,env,records,logs,label)
        print(label,result['exit_code'],flush=True)
        if expected is not None and result['exit_code']!=expected:
            raise ValueError('build stage failed: '+label+'; see private log')
        return result
    flags=['--sysroot='+str(sysroot),'-B'+str(libs)+'/','-static-libgcc','-nostdinc',
           '-isystem',str(gcc_headers/'include'),'-isystem',str(gcc_headers/'include-fixed'),
           '-isystem',str(sysroot/'usr/include'),
           '-L'+str(sysroot/'lib64'),'-L'+str(libs),
           '-Wl,-rpath-link,'+str(sysroot/'lib64')]
    (work/'libc-probe.c').write_text('int main(void) { return 0; }\n')
    run('libc-probe-object',[cc,*flags,'-std=c11','-O2','-fno-ident','-c',
                           work/'libc-probe.c','-o',work/'libc-probe.o'])
    for suffix in ('a','b'):
        run('libc-probe-'+suffix,[cc,*flags,work/'libc-probe.o',
            '-Wl,-Map='+str(work/('probe-'+suffix+'.map')),'-o',work/('probe-'+suffix)])
    facts=gate.elf_facts(work/'probe-a','/usr/bin/readelf',env,records)
    errors=gate.policy_errors(facts,'4.9','2.28',['libc.so.6'])
    if errors:raise ValueError(str(errors))
    # Prove new libc/start files, permitting only the same GCC's support objects.
    linkmap=(work/'probe-a.map').read_text()
    loaded=re.findall(r'^LOAD (.+)$',linkmap,re.MULTILINE)
    gate.validate_search_paths(loaded,[sysroot,cc.parents[1],work])
    old_sysroot=cc.parents[1]/'aarch64-nextui-linux-gnu/libc'
    if any(Path(x).resolve().is_relative_to(old_sysroot.resolve()) for x in loaded):
        raise ValueError('old libc/startup leaked into link')
    for name in ('crt1.o','crti.o','crtn.o','libc.so','libc.so.6','libc_nonshared.a','ld-linux-aarch64.so.1'):
        if not any(Path(x).name==name and Path(x).resolve().is_relative_to(sysroot) for x in loaded):
            raise ValueError('new libc input missing: '+name)
    build=work/'build-sdl';build.mkdir()
    configure=['/usr/bin/sh',a.sdl/'configure','--build=x86_64-pc-linux-gnu',
        '--host=aarch64-nextui-linux-gnu','--prefix=/usr','--enable-video-mali',
        '--enable-video-opengles','--disable-video-opengl','--disable-video-x11',
        '--disable-video-wayland','--disable-video-kmsdrm','--disable-audio',
        '--disable-dbus','--disable-ibus','--disable-fcitx','--disable-hidapi',
        '--disable-libudev','--disable-power','--disable-sensor','--disable-locale',
        '--disable-render','--disable-joystick','--disable-haptic','--disable-shared',
        '--enable-static','--disable-sdl2-config','CFLAGS='+' '.join(flags),
        'CPPFLAGS=-I'+str(a.api)]
    run('sdl-configure',configure,build)
    config=build/'include/SDL_config.h'
    if '#define SDL_VIDEO_DRIVER_MALI 1' not in config.read_text():raise ValueError('Mali config missing')
    # Private copies of real headers, replacing only the generated config.
    includes=work/'include';shutil.copytree(a.sdl/'include',includes/'SDL2')
    shutil.copy2(config,includes/'SDL2/SDL_config.h')
    compile_flags=[*flags,'-I'+str(includes),'-I'+str(a.api),'-std=c11','-O2',
                   '-Wall','-Wextra','-Werror','-fno-ident']
    run('include-search',[cc,*compile_flags,'-E','-v',source,'-o','/dev/null'])
    search=(logs/'include-search.log').read_text()
    match=re.search(r'#include <\.\.\.> search starts here:\n(.*?)End of search list\.',search,re.S)
    if not match:raise ValueError('unrecognized include search output')
    search_paths=[x.strip() for x in match[1].splitlines() if x.strip()]
    allowed=[sysroot,includes,a.api,cc.parents[1]/'lib/gcc']
    gate.validate_search_paths(search_paths,allowed)
    run('triangle-object',[cc,*compile_flags,'-MD','-MF',work/'triangle.d','-c',source,'-o',work/'triangle.o'])
    dependencies=shlex.split((work/'triangle.d').read_text().replace('\\\n',' '))[1:]
    gate.validate_search_paths(dependencies,[*allowed,source.parent])
    obj=gate.elf_facts(work/'triangle.o','/usr/bin/readelf',env,records)
    if obj['machine']!=183 or obj['type']!=1:raise ValueError('wrong triangle object format')
    # A real link attempt, without vendor substitutes, unresolved-symbol bypasses
    # or PowerVR libraries. Missing H700 link inputs are an expected blocker.
    attempt=run('triangle-link',[cc,*flags,work/'triangle.o','-lSDL2','-lGLESv2','-lEGL',
        '-Wl,-Map='+str(work/'triangle.map'),'-o',work/'triangle'],expected=None)
    if attempt['exit_code']==0:raise ValueError('unexpected link success: provenance review required')
    diagnostic=(logs/'triangle-link.log').read_text()
    missing=re.findall(r'cannot find (-l\S+)',diagnostic)
    if not missing:raise ValueError('link failed for an unexpected reason; inspect log')
    result={'compiler_files_verified':count,'probe':facts,
        'same_workspace_probe_bytes_identical':gate.sha256(work/'probe-a')==gate.sha256(work/'probe-b'),
        'triangle_object':obj,'include_search_paths':search_paths,
        'dependencies':dependencies,'probe_load_inputs':loaded,
        'sdl_generated_config_sha256':gate.sha256(config),
        'graphics_status':'LINK_BLOCKED','missing_link_inputs':missing,
        'target_execution':'NEVER','distribution':'BLOCKED'}
    (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Libc probe PASS_STATIC; original object PASS; H700 LINK_BLOCKED',flush=True)


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(1)
