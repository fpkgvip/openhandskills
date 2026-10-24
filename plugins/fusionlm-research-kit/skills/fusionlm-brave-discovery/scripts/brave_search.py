#!/usr/bin/env python3
"""Brave Web Search only. No credential argument, redirects, proxies or silent unbudgeted calls."""
import argparse
import json
import os
import re
import time
import uuid
from pathlib import Path
from urllib import error, parse, request
from budget_core import BudgetError, reserve, settle, micro

ENDPOINT='https://api.search.brave.com/res/v1/web/search'
PREFERRED=('BRAVE_SEARCH_API_KEY','BRAVE_API_KEY','BRAVE_SEARCH_KEY','BRAVE_SEARCH_TOKEN')
MAX_RESPONSE=2_000_000
class SearchError(Exception):
    pass
class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def select_secret(env_name=None):
    if env_name:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',env_name): raise SearchError('invalid secret environment-variable name')
        names=[env_name]
    else:
        names=[n for n in PREFERRED if os.environ.get(n)]
        if not names:
            names=[n for n in os.environ if 'BRAVE' in n.upper() and re.search(r'KEY|TOKEN',n.upper()) and os.environ.get(n)]
            if len(names)>1: raise SearchError('multiple custom Brave secrets; select a variable NAME with --secret-env')
    for name in names:
        value=os.environ.get(name,'').strip()
        if value:
            if '\n' in value or '\r' in value: raise SearchError('invalid credential representation')
            return name,value
    raise SearchError('Brave secret is not exposed to this conversation environment')

def query_params(query,count,offset,freshness):
    if not query.strip() or len(query)>600 or len(query.split())>75: raise SearchError('query must be nonempty, <=600 characters and <=75 words')
    if not 1<=count<=20 or not 0<=offset<=9: raise SearchError('count or offset outside documented limits')
    if freshness and not re.fullmatch(r'pd|pw|pm|py|\d{4}-\d{2}-\d{2}to\d{4}-\d{2}-\d{2}',freshness): raise SearchError('unsupported freshness format')
    result={'q':query,'count':count,'offset':offset,'extra_snippets':'true','text_decorations':'false','result_filter':'web,discussions'}
    if freshness: result['freshness']=freshness
    return result

def safe_result(data,secret):
    result={}
    for section in ('web','discussions'):
        rows=(data.get(section) or {}).get('results') or []
        result[section]=[{'title':str(r.get('title',''))[:500],'url':str(r.get('url',''))[:4000],'description':str(r.get('description',''))[:1500],'extra_snippets':[str(s)[:700] for s in (r.get('extra_snippets') or [])[:5]],'page_age':r.get('page_age')} for r in rows[:20] if isinstance(r,dict)]
    return json.loads(json.dumps(result,ensure_ascii=False).replace(secret,'[REDACTED]'))

def wait_seconds(headers,attempt):
    normal={k.lower():v for k,v in headers.items()}
    raw=normal.get('retry-after') or normal.get('x-ratelimit-reset') or ''
    try: return min(60,max(1,float(str(raw).split(',')[0].strip())))
    except ValueError: return min(60,2**attempt)

def search(query,ledger,ceiling,count=10,offset=0,freshness=None,env_name=None,retries=2,request_id=None,opener=None):
    name,secret=select_secret(env_name)
    if secret in query or re.search(r'(?i)\bbearer\s+\S+|\b(?:flm_live_|github_pat_|sk-)[A-Za-z0-9_-]{16,}',query): raise SearchError('refusing secret-like query content')
    params=query_params(query,count,offset,freshness)
    if micro(ceiling)<=0: raise SearchError('per-request bound must be positive')
    base_id=request_id or 'brave-'+uuid.uuid4().hex
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',base_id): raise SearchError('invalid nonsensitive request id')
    opener=opener or request.build_opener(request.ProxyHandler({}),NoRedirect())
    for attempt in range(retries+1):
        rid=f'{base_id}:a{attempt+1}'
        reserve(ledger,rid,ceiling,'brave-search')
        req=request.Request(ENDPOINT+'?'+parse.urlencode(params),headers={'Accept':'application/json','X-Subscription-Token':secret,'User-Agent':'fusionlm-research-skills/1.0'})
        retry=False; headers={}; status_code=None
        try:
            with opener.open(req,timeout=30) as response:
                headers=dict(response.headers.items())
                raw=response.read(MAX_RESPONSE+1)
                if len(raw)>MAX_RESPONSE: raise SearchError('response exceeds local size limit')
                data=json.loads(raw.decode('utf-8'))
                if not isinstance(data,dict): raise SearchError('unexpected response shape')
                result=safe_result(data,secret)
                result['meta']={'endpoint':'Brave Web Search','request_id':rid,'credential_env':name,'cost_basis':'conservative-booked-upper-bound','booked_request_usd':str(ceiling),'rate_headers':{k:v for k,v in headers.items() if k.lower().startswith('x-ratelimit-')}}
                return json.loads(json.dumps(result,ensure_ascii=False).replace(secret,'[REDACTED]'))
        except error.HTTPError as exc:
            status_code=exc.code; headers=dict(exc.headers.items()) if exc.headers else {}
            retry=exc.code==429 or 500<=exc.code<=599
            remaining=next((v for k,v in headers.items() if k.lower()=='x-ratelimit-remaining'),'')
            limits=next((v for k,v in headers.items() if k.lower()=='x-ratelimit-limit'),'')
            try:
                rs=[int(v.strip()) for v in remaining.split(',')]; ls=[int(v.strip()) for v in limits.split(',')]
                if len(rs)>1 and len(ls)>1 and rs[1]==0 and ls[1]>0: retry=False
            except ValueError: pass
        except (error.URLError,TimeoutError,OSError):
            retry=True
        except (json.JSONDecodeError,UnicodeError):
            raise SearchError('unexpected response encoding; content not logged') from None
        finally:
            settle(ledger,rid,ceiling,'upper-bound')
        if not retry or attempt==retries:
            raise SearchError(f'Brave request failed (HTTP {status_code or "network"}); response body and credential not logged')
        time.sleep(wait_seconds(headers,attempt+1))
    raise SearchError('retry limit reached')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check-secret',action='store_true'); p.add_argument('--secret-env')
    p.add_argument('--query'); p.add_argument('--ledger'); p.add_argument('--request-ceiling-usd')
    p.add_argument('--count',type=int,default=10); p.add_argument('--offset',type=int,default=0)
    p.add_argument('--freshness'); p.add_argument('--retries',type=int,choices=range(4),default=2)
    p.add_argument('--request-id'); p.add_argument('--output')
    a=p.parse_args()
    try:
        if a.check_secret:
            name,_=select_secret(a.secret_env)
            print(json.dumps({'available':True,'environment_variable':name,'network_called':False})); return 0
        if not a.query or not a.ledger or not a.request_ceiling_usd: raise SearchError('query, ledger and verified request ceiling are required')
        if a.output and Path(a.output).exists(): raise SearchError('output file already exists; choose a new artifact name')
        result=search(a.query,a.ledger,a.request_ceiling_usd,a.count,a.offset,a.freshness,a.secret_env,a.retries,a.request_id)
        payload=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if a.output:
            fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as f: f.write(payload)
            print(json.dumps({'saved':a.output,'request_id':result['meta']['request_id']}))
        else: print(payload,end='')
        return 0
    except (SearchError,BudgetError) as exc:
        print(json.dumps({'error':str(exc)})); return 2
    except Exception:
        print(json.dumps({'error':'Local operation failed; inspect non-secret configuration and ledger. No raw exception or response was printed.'})); return 2
if __name__=='__main__': raise SystemExit(main())
