#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Issue #26 host-only input/environment boundary; never a target runner."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import tarfile
import time


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def check_file(path, expected, roots):
    p=Path(path).resolve(strict=True)
    if not any(p.is_relative_to(Path(r).resolve()) for r in roots):
        raise ValueError('unapproved resolved path')
    if not p.is_file() or not re.fullmatch('[0-9a-f]{64}',expected) or sha256(p)!=expected:
        raise ValueError('unknown or changed file provenance')
    return p


def extract(archive, expected, destination):
    if sha256(archive)!=expected or not re.fullmatch('[0-9a-f]{64}',expected):
        raise ValueError('archive digest mismatch')
    dest=Path(destination)
    if dest.exists() or dest.is_symlink():raise ValueError('extraction destination exists')
    with tarfile.open(archive,'r:*') as tf:
        entries=tf.getmembers()
        if len(entries)>300000 or sum(m.size for m in entries if m.isfile())>6*1024**3:
            raise ValueError('archive resource limit')
        paths={}
        for m in entries:
            p=PurePosixPath(m.name)
            if p.is_absolute() or '..' in p.parts or '\\' in m.name:raise ValueError('unsafe member name')
            if str(p)=='.' and m.isdir():continue
            if str(p)=='.' or p in paths or not (m.isdir() or m.isfile() or m.issym()):
                raise ValueError('duplicate/special/hardlink member')
            if m.issym():
                t=PurePosixPath(m.linkname)
                if t.is_absolute() or '\\' in m.linkname:raise ValueError('absolute link')
                parts=list(p.parent.parts)
                for part in t.parts:
                    if part=='..':
                        if not parts:raise ValueError('escaping link')
                        parts.pop()
                    elif part!='.':parts.append(part)
            paths[p]=m
        for p in paths:
            if any(a in paths and not paths[a].isdir() for a in p.parents):
                raise ValueError('non-directory member ancestor')
        links={p:PurePosixPath(m.linkname) for p,m in paths.items() if m.issym()}
        for p,target in links.items():
            pending=list(p.parent.parts)+list(target.parts);stack=[];hops=0
            while pending:
                part=pending.pop(0)
                if part=='.':continue
                if part=='..':
                    if not stack:raise ValueError('composite symlink escape')
                    stack.pop();continue
                stack.append(part);current=PurePosixPath(*stack)
                if current in links:
                    hops+=1
                    if hops>40:raise ValueError('cyclic/excessive symlink chain')
                    stack.pop();pending=list(links[current].parts)+pending
        dest.mkdir(parents=True)
        for p,m in paths.items():
            out=dest/str(p)
            if m.isdir():out.mkdir(parents=True,exist_ok=True)
            elif m.isfile():
                out.parent.mkdir(parents=True,exist_ok=True)
                with tf.extractfile(m) as src,out.open('xb') as f:shutil.copyfileobj(src,f)
                out.chmod(m.mode & 0o755)
                # Keep GNU generated-file dates; never trigger unpinned autotools.
                os.utime(out,(m.mtime,m.mtime),follow_symlinks=False)
        for p,m in paths.items():
            if m.issym():
                out=dest/str(p);out.parent.mkdir(parents=True,exist_ok=True);out.symlink_to(m.linkname)
    return len(paths)


def environment(workspace, tool_farm, extra=None):
    """Fresh allowlist. HOME is omitted, never reassigned."""
    temp=Path(workspace).resolve()/'tmp';temp.mkdir(parents=True,exist_ok=True)
    result={'PATH':str(Path(tool_farm).resolve()),'LC_ALL':'C','LANG':'C',
            'TMPDIR':str(temp),'CONFIG_SITE':'/dev/null','PYTHONNOUSERSITE':'1',
            'PYTHONDONTWRITEBYTECODE':'1','SOURCE_DATE_EPOCH':'1533081600'}
    allowed={'CC','CXX','BUILD_CC','AR','AS','LD','RANLIB','NM','OBJCOPY','OBJDUMP',
             'PKG_CONFIG_LIBDIR','PKG_CONFIG_SYSROOT_DIR','M4'}
    if extra:
        if set(extra)-allowed:raise ValueError('unapproved build environment key')
        if any(not isinstance(v,str) or '\x00' in v for v in extra.values()):
            raise ValueError('invalid environment value')
        result.update(extra)
    return result


def tool_record(path, role, reviewed_script=False):
    resolved=Path(path).resolve(strict=True)
    with resolved.open('rb') as f:head=f.read(20)
    if head[:4]==b'\x7fELF':
        if len(head)<20 or head[4:6]!=b'\x02\x01' or struct.unpack('<H',head[18:20])[0]!=62:
            raise ValueError('host tool is not x86_64 ELF')
    elif not head.startswith(b'#!') or not reviewed_script:
        raise ValueError('unknown host tool format or unreviewed wrapper')
    return {'path':str(resolved),'sha256':sha256(resolved),'role':role,
            'format':'ELF64-x86_64' if head[:4]==b'\x7fELF' else 'reviewed-script'}


def farm(directory, records):
    d=Path(directory);d.mkdir(parents=True,exist_ok=True)
    if set(p.name for p in d.iterdir())-set(records):raise ValueError('unknown tool farm entry')
    for name,r in records.items():
        if not re.fullmatch('[A-Za-z0-9_.+-]+',name):raise ValueError('bad tool name')
        p=check_file(r['path'],r['sha256'],[Path(r['path']).parent]);target=d/name
        if target.is_symlink():target.unlink()
        elif target.exists():raise ValueError('tool destination is not a symlink')
        target.symlink_to(p)


def validate_environment(env, records):
    allowed={'PATH','LC_ALL','LANG','TMPDIR','CONFIG_SITE','PYTHONNOUSERSITE',
             'PYTHONDONTWRITEBYTECODE','SOURCE_DATE_EPOCH','CC','CXX','BUILD_CC',
             'AR','AS','LD','RANLIB','NM','OBJCOPY','OBJDUMP','PKG_CONFIG_LIBDIR',
             'PKG_CONFIG_SYSROOT_DIR','M4'}
    if set(env)-allowed or any(not isinstance(v,str) or '\x00' in v for v in env.values()):
        raise ValueError('unapproved inherited environment')
    if env.get('LC_ALL')!='C' or env.get('LANG')!='C' or env.get('CONFIG_SITE')!='/dev/null':
        raise ValueError('unapproved locale/configuration')
    path=env.get('PATH','')
    if not path or ':' in path or not Path(path).is_absolute():raise ValueError('unapproved PATH')
    directory=Path(path)
    if env.get('TMPDIR')!=str(directory.parent/'tmp') or not Path(env['TMPDIR']).is_dir():
        raise ValueError('unapproved temporary directory')
    if 'PKG_CONFIG_LIBDIR' in env:
        pkg=Path(env['PKG_CONFIG_LIBDIR'])
        if pkg!=directory.parent/'empty-pkgconfig' or not pkg.is_dir() or any(pkg.iterdir()):
            raise ValueError('unapproved pkg-config directory')
    if set(p.name for p in directory.iterdir())!=set(records):raise ValueError('unknown/missing PATH entry')
    for name,r in records.items():
        entry=directory/name
        if not entry.is_symlink() or entry.resolve()!=Path(r['path']).resolve():
            raise ValueError('changed PATH tool')
        check_file(entry,r['sha256'],[Path(r['path']).parent])
    for key in ('CC','CXX','BUILD_CC','AR','AS','LD','RANLIB','NM','OBJCOPY','OBJDUMP','M4'):
        if key in env:
            selected=Path(env[key]).resolve(strict=True)
            if not any(selected==Path(r['path']).resolve() for r in records.values()):
                raise ValueError('unknown tool environment path')


def checked_run(argv, cwd, env, records, logs, label, timeout=1800):
    if not re.fullmatch('[A-Za-z0-9_.-]+',label):raise ValueError('unsafe log label')
    validate_environment(env,records)
    exe=Path(argv[0]).resolve(strict=True)
    matches=[r for r in records.values() if Path(r['path']).resolve()==exe]
    if not matches:raise ValueError('executable outside host tool allowlist')
    check_file(exe,matches[0]['sha256'],[exe.parent])
    tool_record(exe,'execution-format-check',reviewed_script=matches[0].get('format')=='reviewed-script')
    if any(k.startswith(('LD_','PKG_CONFIG_')) and k not in ('PKG_CONFIG_LIBDIR','PKG_CONFIG_SYSROOT_DIR') for k in env):
        raise ValueError('hostile loader/pkg-config environment')
    if any(k in env for k in ('HOME','PYTHONPATH','BASH_ENV','ENV','GCC_EXEC_PREFIX','CPATH',
                              'C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','LIBRARY_PATH','COMPILER_PATH')):
        raise ValueError('unapproved inherited environment')
    logdir=Path(logs);logdir.mkdir(parents=True,exist_ok=True);started=time.monotonic()
    with (logdir/(label+'.log')).open('w') as output:
        p=subprocess.run([str(x) for x in argv],cwd=cwd,env=env,stdout=output,
                         stderr=subprocess.STDOUT,timeout=timeout)
    r={'argv':[str(x) for x in argv],'cwd':str(cwd),'exit_code':p.returncode,
       'elapsed_seconds':round(time.monotonic()-started,3),'environment':env,
       'initial_executable_sha256':matches[0]['sha256']}
    (logdir/(label+'.json')).write_text(json.dumps(r,indent=2)+'\n');return r


def validate_search_paths(paths, roots):
    for path in paths:
        p=Path(path).resolve(strict=True)
        if not any(p.is_relative_to(Path(root).resolve()) for root in roots):
            raise ValueError('unexpected host include/link input')


def verify_archive_tree(archive, expected, root):
    """Verify an already unpacked compiler, including hardlink contents.

    This does not extract archives or bless unrecorded compiler search inputs.
    The archive digest must come from the separately reviewed input lock.
    """
    if sha256(archive)!=expected:raise ValueError('compiler archive digest mismatch')
    base=Path(root).resolve(strict=True);seen=set();count=0
    with tarfile.open(archive) as tf:
        members=tf.getmembers();hashes={};hardlinks={}
        # Hash regular members in physical order. extractfile(hardlink) can
        # repeatedly seek backwards through a compressed archive.
        for m in members:
            name=PurePosixPath(m.name)
            if name.is_absolute() or '..' in name.parts or '\\' in m.name:
                raise ValueError('unsafe compiler member')
            p=base/str(name)
            if not p.resolve().is_relative_to(base):raise ValueError('compiler link escapes root')
            if m.isdir():continue
            if name in seen:raise ValueError('duplicate compiler input')
            seen.add(name)
            if m.issym():
                if not p.is_symlink() or str(p.readlink())!=m.linkname:raise ValueError('changed compiler symlink')
            elif m.islnk():
                target=PurePosixPath(m.linkname)
                if target.is_absolute() or '..' in target.parts or '\\' in m.linkname:
                    raise ValueError('unsafe compiler hardlink')
                hardlinks[name]=target
            elif m.isfile():
                if p.is_symlink():raise ValueError('regular compiler input replaced by link')
                h=hashlib.sha256()
                with tf.extractfile(m) as f:
                    for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
                hashes[name]=h.hexdigest()
                check_file(p,hashes[name],[base]);count+=1
            else:raise ValueError('special compiler input')
        for name,target in hardlinks.items():
            if (base/str(name)).is_symlink():raise ValueError('compiler hardlink replaced by symlink')
            visited={name}
            while target in hardlinks:
                if target in visited:raise ValueError('cyclic compiler hardlink')
                visited.add(target);target=hardlinks[target]
            if target not in hashes:raise ValueError('unknown compiler hardlink target')
            check_file(base/str(name),hashes[target],[base]);count+=1
    actual={PurePosixPath(p.relative_to(base).as_posix()) for p in base.rglob('*')
            if p.is_symlink() or p.is_file()}
    if actual!=seen:raise ValueError('unknown/missing compiler tree input')
    return count


def tree_digest(directory):
    """Content pin for a clean source tree; Git administrative files excluded."""
    root=Path(directory).resolve();items=[]
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if '.git' in rel.parts:continue
        if p.is_symlink():
            if not p.resolve().is_relative_to(root):raise ValueError('source symlink escapes root')
            items.append((rel.as_posix(),'link',str(p.readlink())))
        elif p.is_file():items.append((rel.as_posix(),'file',sha256(p)))
    return hashlib.sha256(json.dumps(items,separators=(',',':')).encode()).hexdigest()


def elf_facts(path, readelf, env, records):
    validate_environment(env,records)
    selected=Path(readelf).resolve(strict=True)
    matches=[r for r in records.values() if Path(r['path']).resolve()==selected]
    if not matches:raise ValueError('unknown readelf provenance')
    check_file(selected,matches[0]['sha256'],[selected.parent])
    tool_record(selected,'native readelf')
    p=Path(path)
    if not p.is_file():raise ValueError('not a regular ELF file')
    with p.open('rb') as f:head=f.read(20)
    if len(head)!=20 or head[:6]!=b'\x7fELF\x02\x01':raise ValueError('not ELF64 little-endian')
    r=subprocess.run([str(readelf),'--wide','-h','-l','-d','--version-info','--notes',str(p)],
                     env=env,capture_output=True,text=True,timeout=30)
    if r.returncode:raise ValueError('readelf failed')
    text=r.stdout;versions=[];in_needs=False
    notes=set(re.findall(r'OS: Linux, ABI: ([0-9.]+)',text))
    if len(notes)>1:raise ValueError('conflicting kernel ABI notes')
    for line in text.splitlines():
        if line.startswith('Version needs section'):in_needs=True
        elif line.startswith('Version ') and 'section' in line:in_needs=False
        if in_needs:versions+=re.findall(r'Name:\s*(\S+)',line)
    def match(pattern):
        m=re.search(pattern,text);return m.group(1).strip() if m else None
    return {'sha256':sha256(p),'machine':struct.unpack('<H',head[18:20])[0],
            'type':struct.unpack('<H',head[16:18])[0],
            'interpreter':match(r'Requesting program interpreter:\s*([^\]]+)'),
            'gnu_linux_abi':match(r'OS: Linux, ABI: ([0-9.]+)'),
            'needed':sorted(set(re.findall(r'\(NEEDED\).*?\[([^\]]+)\]',text))),
            'rpaths':re.findall(r'\((?:RPATH|RUNPATH)\).*?\[([^\]]*)\]',text),
            'required_versions':sorted(set(versions))}


def policy_errors(facts, max_kernel, max_glibc, allowed_needed):
    def ver(x):
        if not isinstance(x,str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}',x):
            raise ValueError('malformed version')
        return tuple(int(a) for a in x.split('.'))+(0,)*(3-len(x.split('.')))
    errors=[]
    kernel_limit=ver(max_kernel);glibc_limit=ver(max_glibc)
    if not isinstance(facts,dict):return ['malformed ELF facts']
    if facts.get('machine')!=183:errors.append('wrong target machine')
    if facts.get('type') not in (2,3):errors.append('not an executable/shared ELF')
    if facts.get('interpreter') not in (None,'/lib/ld-linux-aarch64.so.1'):
        errors.append('unexpected interpreter')
    if facts.get('type')==2 and facts.get('interpreter')!='/lib/ld-linux-aarch64.so.1':
        errors.append('missing executable interpreter')
    if not facts.get('gnu_linux_abi'):errors.append('unknown kernel note')
    else:
        try:
            if ver(facts['gnu_linux_abi'])>kernel_limit:errors.append('kernel baseline too high')
        except ValueError:errors.append('malformed kernel note')
    if facts.get('rpaths'):errors.append('unexpected runtime search path')
    if allowed_needed is None:errors.append('unknown dependency policy')
    elif not isinstance(facts.get('needed'),list) or any(not isinstance(v,str) for v in facts['needed']):
        errors.append('malformed NEEDED')
    elif set(facts['needed'])-set(allowed_needed):errors.append('unexpected NEEDED')
    versions=facts.get('required_versions')
    if not isinstance(versions,list):return errors+['malformed version requirements']
    for v in versions:
        if not isinstance(v,str) or not re.fullmatch(r'GLIBC_[0-9]+(?:\.[0-9]+){1,2}',v):
            errors.append('unreviewed symbol version')
        elif ver(v[6:])>glibc_limit:errors.append('GLIBC requirement too high')
    return errors
