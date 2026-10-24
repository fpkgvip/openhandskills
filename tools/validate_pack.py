#!/usr/bin/env python3
"""Offline structural validation; not a live OpenHands UI/import test."""
import ast
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate(root=ROOT):
    issues=[]
    market=json.loads((root/'.plugin/marketplace.json').read_text())
    if market!=json.loads((root/'.claude-plugin/marketplace.json').read_text()):issues.append('marketplace mirrors differ')
    names=[]
    for entry in market['plugins']:
        plugin=(root/entry['source']).resolve()
        if not plugin.is_relative_to(root.resolve()):issues.append('plugin source escapes pack');continue
        metadata=json.loads((plugin/'.plugin/plugin.json').read_text())
        if metadata!=json.loads((plugin/'.claude-plugin/plugin.json').read_text()):issues.append('plugin mirrors differ')
        if metadata['name']!=entry['name']:issues.append('plugin name mismatch')
        for path in sorted((plugin/'skills').glob('*/SKILL.md')):
            txt=path.read_text();parts=txt.split('---',2)
            if len(parts)!=3 or parts[0].strip():issues.append(f'bad frontmatter: {path.name}');continue
            name=re.search(r'^name:\s*([a-z0-9-]+)\s*$',parts[1],re.M)
            desc=re.search(r'^description:\s*(.+)$',parts[1],re.M)
            if not name or name.group(1)!=path.parent.name or not path.parent.name.startswith('fusionlm-'):issues.append('skill name invalid')
            if not desc:issues.append('description missing')
            else:
                try:
                    d=json.loads(desc.group(1))
                    if not isinstance(d,str) or not d.strip() or len(d)>1024:issues.append('description invalid')
                except Exception:issues.append('description syntax invalid')
            names.append(path.parent.name)
            for ref in re.findall(r'`((?:references|scripts)/[^`\s]+)`',parts[2]):
                if not (path.parent/ref).is_file():issues.append(f'missing resource {path.parent.name}/{ref}')
    if len(names)!=len(set(names)):issues.append('duplicate skill names')
    if len(names)!=7:issues.append('expected seven skills')
    for path in root.rglob('*.py'):
        ast.parse(path.read_text(),filename=str(path))
    copies=list(root.glob('plugins/fusionlm-research-kit/skills/*/scripts/budget_core.py'))
    if len(copies)!=2 or len({p.read_bytes() for p in copies})!=1:issues.append('budget helper copies drifted')
    if any(root.rglob('.mcp.json')) or any(root.rglob('hooks.json')):issues.append('unexpected auto-connected code')
    if any(p.is_symlink() for p in root.rglob('*')):issues.append('symlink in pack')
    return {'ok':not issues,'skill_count':len(names),'skills':names,'issues':issues,'live_openhands_import_tested':False}
if __name__=='__main__':
    result=validate();print(json.dumps(result,indent=2));raise SystemExit(0 if result['ok'] else 1)
