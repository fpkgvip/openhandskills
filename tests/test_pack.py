import importlib.util
import io
import json
import os
import socket
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock
from urllib import error

ROOT=Path(__file__).resolve().parents[1]
SKILLS=ROOT/'plugins'/'fusionlm-research-kit'/'skills'
sys.path.insert(0,str(SKILLS/'fusionlm-brave-discovery'/'scripts'))
import budget_core as budget
import brave_search as brave

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
fetcher=load('fetch_public',SKILLS/'fusionlm-source-forensics/scripts/fetch_public.py')
validator=load('validate_pack',ROOT/'tools/validate_pack.py')
installer=load('install_skills',ROOT/'tools/install_skills.py')

class Response:
    def __init__(self,data=b'{}',headers=None):self.data=data;self.headers=headers or {}
    def read(self,n):return self.data[:n]
    def __enter__(self):return self
    def __exit__(self,*args):return False
class Opener:
    def __init__(self,*results):self.results=list(results);self.calls=[]
    def open(self,req,timeout):
        self.calls.append(req);result=self.results.pop(0)
        if isinstance(result,Exception):raise result
        return result

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'budget.sqlite';budget.initialise(self.db,'1')
    def tearDown(self):self.tmp.cleanup()
    def test_micro_rounds_up(self):self.assertEqual(budget.micro('0.0000001'),1)
    def test_nonfinite_rejected(self):
        for v in ('NaN','Infinity','-1'):
            with self.assertRaises(budget.BudgetError):budget.micro(v)
    def test_owner_ceiling(self):
        with self.assertRaises(budget.BudgetError):budget.initialise(Path(self.tmp.name)/'other','291')
    def test_reinitialisation_cannot_raise_limit(self):
        with self.assertRaises(budget.BudgetError):budget.initialise(self.db,'2')
    def test_reserve_and_settle(self):
        budget.reserve(self.db,'r1','.4');budget.settle(self.db,'r1','.1');self.assertEqual(budget.status(self.db)['available_usd'],'0.900000')
    def test_oversubscription_refused(self):
        budget.reserve(self.db,'r1','.9')
        with self.assertRaises(budget.BudgetError):budget.reserve(self.db,'r2','.2')
    def test_duplicate_id_refused(self):
        budget.reserve(self.db,'same','.1')
        with self.assertRaises(budget.BudgetError):budget.reserve(self.db,'same','.1')
    def test_idempotent_actual(self):
        budget.reserve(self.db,'x','.2');budget.settle(self.db,'x','.1');budget.settle(self.db,'x','.1');self.assertEqual(budget.status(self.db)['available_usd'],'0.900000')
    def test_actual_cannot_be_rewritten(self):
        budget.reserve(self.db,'x','.2');budget.settle(self.db,'x','.1')
        with self.assertRaises(budget.BudgetError):budget.settle(self.db,'x','0')
    def test_upper_bound_reconciliation(self):
        budget.reserve(self.db,'x','.3');budget.settle(self.db,'x','.3','upper-bound');budget.settle(self.db,'x','.01','actual-receipt');self.assertEqual(budget.status(self.db)['available_usd'],'0.990000')
    def test_release_no_charge(self):
        budget.reserve(self.db,'x','.9');budget.release(self.db,'x','confirmed-no-charge');self.assertEqual(budget.status(self.db)['available_usd'],'1.000000')
    def test_cannot_release_settled(self):
        budget.reserve(self.db,'x','.2');budget.settle(self.db,'x','.1')
        with self.assertRaises(budget.BudgetError):budget.release(self.db,'x','confirmed-no-charge')
    def test_overrun_recorded_not_hidden(self):
        budget.reserve(self.db,'x','1');s=budget.settle(self.db,'x','1.2');self.assertTrue(s['overcommitted']);self.assertTrue(s['reservation_overrun'])
        with self.assertRaises(budget.BudgetError):budget.reserve(self.db,'y','.01')
    def test_concurrent_admission(self):
        def work(i):
            try:budget.reserve(self.db,'job'+str(i),'.3');return True
            except budget.BudgetError:return False
        with ThreadPoolExecutor(max_workers=8) as pool:accepted=list(pool.map(work,range(8)))
        self.assertEqual(sum(accepted),3)

class BraveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'budget.sqlite';budget.initialise(self.db,'1');self.env=mock.patch.dict(os.environ,{'BRAVE_SEARCH_API_KEY':'unit-test-placeholder-not-a-real-key'},clear=True);self.env.start()
    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def test_presence_only(self):
        with mock.patch.object(sys,'argv',['brave','--check-secret']),mock.patch('sys.stdout',new_callable=io.StringIO) as out:
            self.assertEqual(brave.main(),0);self.assertNotIn('unit-test-placeholder',out.getvalue());self.assertIn('BRAVE_SEARCH_API_KEY',out.getvalue())
    def test_custom_secret_name(self):
        with mock.patch.dict(os.environ,{'MY_BRAVE_TOKEN':'placeholder'},clear=True):self.assertEqual(brave.select_secret()[0],'MY_BRAVE_TOKEN')
    def test_missing_secret(self):
        with mock.patch.dict(os.environ,{},clear=True):
            with self.assertRaises(brave.SearchError):brave.select_secret()
    def test_ambiguous_custom_names(self):
        with mock.patch.dict(os.environ,{'BRAVE_ONE_KEY':'a','BRAVE_TWO_KEY':'b'},clear=True):
            with self.assertRaises(brave.SearchError):brave.select_secret()
    def test_lowercase_rate_header(self):
        self.assertEqual(brave.wait_seconds({'x-ratelimit-reset':'3, 1000'},1),3)
    def test_rate_header_cannot_echo_secret(self):
        op=Opener(Response(headers={'X-RateLimit-Policy':'unit-test-placeholder-not-a-real-key'}))
        result=brave.search('test',self.db,'.01',opener=op,retries=0)
        self.assertNotIn('unit-test-placeholder',json.dumps(result))
    def test_parameter_limits(self):
        for q,count,offset in [('',10,0),('a'*601,10,0),('x',21,0),('x',10,10)]:
            with self.assertRaises(brave.SearchError):brave.query_params(q,count,offset,None)
    def test_header_and_endpoint(self):
        op=Opener(Response(b'{"web":{"results":[{"title":"ok","url":"https://example.org"}]}}'))
        result=brave.search('test',self.db,'.01',opener=op,retries=0)
        self.assertTrue(op.calls[0].full_url.startswith(brave.ENDPOINT+'?'));self.assertEqual(op.calls[0].get_header('X-subscription-token'),'unit-test-placeholder-not-a-real-key');self.assertEqual(result['web'][0]['title'],'ok');self.assertEqual(budget.status(self.db)['booked_or_settled_usd'],'0.010000')
    def test_secret_in_result_redacted(self):
        op=Opener(Response(json.dumps({'web':{'results':[{'title':'unit-test-placeholder-not-a-real-key'}]}}).encode()))
        result=brave.search('test',self.db,'.01',opener=op,retries=0);self.assertNotIn('unit-test-placeholder',json.dumps(result))
    def test_secret_in_query_refused_before_spend(self):
        op=Opener()
        with self.assertRaises(brave.SearchError):brave.search('unit-test-placeholder-not-a-real-key',self.db,'.01',opener=op)
        self.assertFalse(op.calls);self.assertEqual(budget.status(self.db)['outstanding_usd'],'0.000000')
    def test_redirect_not_followed(self):
        self.assertIsNone(brave.NoRedirect().redirect_request(None,None,302,'',{},'https://example.org'))
        op=Opener(error.HTTPError(brave.ENDPOINT,302,'redirect',{},None))
        with self.assertRaises(brave.SearchError):brave.search('test',self.db,'.01',opener=op,retries=2)
        self.assertEqual(len(op.calls),1)
    def test_auth_error_no_retry_or_body(self):
        op=Opener(error.HTTPError(brave.ENDPOINT,401,'secret-looking-response',{},None))
        with self.assertRaises(brave.SearchError) as exc:brave.search('test',self.db,'.01',opener=op,retries=2)
        self.assertNotIn('secret-looking',str(exc.exception));self.assertEqual(len(op.calls),1)
    def test_429_bounded_retry(self):
        op=Opener(error.HTTPError(brave.ENDPOINT,429,'limit',{'X-RateLimit-Reset':'1'},None),Response())
        with mock.patch.object(brave.time,'sleep') as sleep:brave.search('test',self.db,'.01',opener=op,retries=1);sleep.assert_called_once()
        self.assertEqual(budget.status(self.db)['booked_or_settled_usd'],'0.020000')
    def test_long_quota_no_busy_retry(self):
        op=Opener(error.HTTPError(brave.ENDPOINT,429,'limit',{'X-RateLimit-Remaining':'0, 0','X-RateLimit-Limit':'1, 100'},None))
        with self.assertRaises(brave.SearchError):brave.search('test',self.db,'.01',opener=op,retries=2)
        self.assertEqual(len(op.calls),1)
    def test_oversize_response_booked(self):
        op=Opener(Response(b'x'*(brave.MAX_RESPONSE+1)))
        with self.assertRaises(brave.SearchError):brave.search('test',self.db,'.01',opener=op,retries=0)
        self.assertEqual(budget.status(self.db)['booked_or_settled_usd'],'0.010000')
    def test_budget_refusal_before_network(self):
        op=Opener()
        with self.assertRaises(budget.BudgetError):brave.search('test',self.db,'2',opener=op,retries=0)
        self.assertFalse(op.calls)
    def test_bad_json_booked(self):
        op=Opener(Response(b'not-json'))
        with self.assertRaises(brave.SearchError):brave.search('test',self.db,'.01',opener=op,retries=0)
        self.assertEqual(budget.status(self.db)['booked_or_settled_usd'],'0.010000')

class FetchTests(unittest.TestCase):
    def dns(self):return mock.patch.object(fetcher.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))])
    def test_private_address_refused(self):
        with mock.patch.object(fetcher.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',80))]):
            with self.assertRaises(fetcher.FetchError):fetcher.validate_url('http://example.org')
    def test_url_credentials_refused(self):
        with self.assertRaises(fetcher.FetchError):fetcher.validate_url('https://name:pass@example.org')
    def test_credential_parameter_refused(self):
        with self.assertRaises(fetcher.FetchError):fetcher.validate_url('https://example.org?token=anything')
    def test_public_fetch_hash(self):
        with self.dns():body,meta=fetcher.fetch('https://example.org',opener=Opener(Response(b'public text')))
        self.assertEqual(body,b'public text');self.assertEqual(meta['bytes'],11);self.assertEqual(len(meta['sha256']),64)
    def test_redirect_revalidated(self):
        op=Opener(error.HTTPError('https://example.org',302,'',{'Location':'http://localhost/secret'},None))
        with self.dns(),self.assertRaises(fetcher.FetchError):fetcher.fetch('https://example.org',opener=op)
        self.assertEqual(len(op.calls),1)
    def test_fetch_size_bound(self):
        with self.dns(),self.assertRaises(fetcher.FetchError):fetcher.fetch('https://example.org',max_bytes=2,opener=Opener(Response(b'123')))

class StructureTests(unittest.TestCase):
    def test_pack_valid(self):self.assertTrue(validator.validate()['ok'])
    def test_install_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            first=installer.install(d);second=installer.install(d)
            self.assertEqual(len(first),7);self.assertTrue(all(x['status']=='already-identical' for x in second))
    def test_install_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            installer.install(d);p=Path(d)/'fusionlm-research-method'/'SKILL.md';p.write_text('different user content')
            with self.assertRaises(ValueError):installer.install(d)
            self.assertEqual(p.read_text(),'different user content')
if __name__=='__main__':unittest.main()
