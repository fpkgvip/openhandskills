#!/usr/bin/env python3
"""Copy this kit's skills; never install packages, call APIs or overwrite differing skills."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'plugins'/'fusionlm-research-kit'/'skills'

def tree_hash(path):
    h=hashlib.sha256()
    for f in sorted(path.rglob('*')):
        if f.is_symlink():raise ValueError('symlinks are not supported')
        if f.is_file() and '__pycache__' not in f.parts:
            h.update(f.relative_to(path).as_posix().encode());h.update(f.read_bytes())
    return h.hexdigest()

def install(destination):
    destination=Path(destination).expanduser()
    if destination.is_symlink():raise ValueError('destination must not be a symlink')
    entries=sorted(p for p in SOURCE.iterdir() if p.is_dir())
    for src in entries:
        dst=destination/src.name
        if dst.exists() and (not dst.is_dir() or tree_hash(src)!=tree_hash(dst)):
            raise ValueError('different installed skill exists; choose another destination or review it manually')
    destination.mkdir(parents=True,exist_ok=True)
    result=[]
    for src in entries:
        dst=destination/src.name
        if dst.exists():result.append({'name':src.name,'status':'already-identical'});continue
        shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        result.append({'name':src.name,'status':'installed'})
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group();g.add_argument('--user',action='store_true');g.add_argument('--destination',default=None);a=p.parse_args()
    destination=Path.home()/'.agents'/'skills' if a.user else Path(a.destination or '.agents/skills')
    try:
        print(json.dumps({'destination':str(destination),'skills':install(destination),'note':'Verify discovery in a new conversation if needed. No settings or packages changed.'},indent=2));return 0
    except (ValueError,OSError) as exc:
        print(json.dumps({'error':str(exc),'destination':str(destination)}));return 2
if __name__=='__main__':raise SystemExit(main())
