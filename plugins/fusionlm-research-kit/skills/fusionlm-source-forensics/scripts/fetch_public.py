#!/usr/bin/env python3
"""Bounded anonymous public-source download. No auth, cookies or environment proxies."""
import argparse
import datetime
import hashlib
import ipaddress
import json
import os
import socket
from urllib import request,error,parse

class FetchError(Exception):
    pass
class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None

def validate_url(url):
    u=parse.urlsplit(url)
    if u.scheme not in ('https','http') or not u.hostname: raise FetchError('only public HTTP(S) sources are supported')
    if u.username or u.password: raise FetchError('URL credentials are forbidden')
    if u.port not in (None,80,443): raise FetchError('nonstandard ports require a separately reviewed retrieval method')
    if u.hostname.lower()=='localhost' or u.hostname.lower().endswith(('.local','.internal')): raise FetchError('local destination refused')
    if any(re.search(r'(?i)^(?:api[_-]?key|access[_-]?token|auth|authorization|password|secret|token|key|signature)$',k) for k,v in parse.parse_qsl(u.query)): raise FetchError('credential-like URL parameters refused')
    try: addresses={row[4][0].split('%')[0] for row in socket.getaddrinfo(u.hostname,u.port or (443 if u.scheme=='https' else 80),type=socket.SOCK_STREAM)}
    except socket.gaierror: raise FetchError('source DNS lookup failed') from None
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses): raise FetchError('non-public destination refused')
    return url

import re

def fetch(url,max_bytes=2_000_000,opener=None):
    if max_bytes<1 or max_bytes>50_000_000: raise FetchError('max-bytes must be 1..50000000')
    opener=opener or request.build_opener(request.ProxyHandler({}),NoRedirect())
    current=url
    for _ in range(6):
        validate_url(current)
        req=request.Request(current,headers={'User-Agent':'fusionlm-research-skills/1.0','Accept':'text/html,application/pdf,text/plain,application/json,*/*;q=0.1'})
        try:
            with opener.open(req,timeout=30) as response:
                body=response.read(max_bytes+1)
                if len(body)>max_bytes: raise FetchError('source exceeds byte ceiling; use a reviewed larger limit or another reader')
                return body,{'original_url':url,'final_url':current,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'content_type':response.headers.get('Content-Type',''),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'evidence_level':'retrieved-bytes-not-verified-claim','security_note':'DNS preflight is best effort, not an OS network sandbox or DNS-rebinding defence.'}
        except error.HTTPError as exc:
            if exc.code in (301,302,303,307,308) and exc.headers.get('Location'):
                current=parse.urljoin(current,exc.headers['Location']); continue
            raise FetchError(f'public fetch refused or failed (HTTP {exc.code}); use lawful browser/source alternatives') from None
    raise FetchError('redirect limit reached')

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('url'); p.add_argument('--output',required=True); p.add_argument('--max-bytes',type=int,default=2_000_000); a=p.parse_args()
    try:
        if os.path.exists(a.output) or os.path.exists(a.output+'.metadata.json'): raise FetchError('choose a new output filename')
        body,meta=fetch(a.url,a.max_bytes)
        fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(body)
        fd=os.open(a.output+'.metadata.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:json.dump(meta,f,indent=2)
        print(json.dumps(meta)); return 0
    except FetchError as exc: print(json.dumps({'error':str(exc)})); return 2
    except Exception: print(json.dumps({'error':'Retrieval failed; no raw headers, environment or credentials logged.'})); return 2
if __name__=='__main__':raise SystemExit(main())
