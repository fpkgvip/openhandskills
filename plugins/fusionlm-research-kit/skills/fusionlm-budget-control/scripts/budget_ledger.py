#!/usr/bin/env python3
import argparse
import json
import sqlite3
from budget_core import BudgetError, initialise, reserve, settle, release, status

def main():
    p=argparse.ArgumentParser(description='Local shared research-budget ledger; no API calls.')
    sub=p.add_subparsers(dest='action',required=True)
    for action in ('init','status','reserve','settle','release'):
        s=sub.add_parser(action); s.add_argument('--db',required=True)
        if action=='init': s.add_argument('--limit-usd',default='290')
        if action in ('reserve','settle','release'): s.add_argument('--id',required=True)
        if action in ('reserve','settle'): s.add_argument('--usd',required=True)
        if action=='reserve': s.add_argument('--category',default='research')
        if action=='settle': s.add_argument('--basis',choices=['actual-receipt','upper-bound','estimate'],default='actual-receipt')
        if action=='release': s.add_argument('--reason',choices=['confirmed-no-charge','cancelled-before-dispatch'],required=True)
    a=p.parse_args()
    try:
        if a.action=='init': result=initialise(a.db,a.limit_usd)
        elif a.action=='status': result=status(a.db)
        elif a.action=='reserve': result=reserve(a.db,a.id,a.usd,a.category)
        elif a.action=='settle': result=settle(a.db,a.id,a.usd,a.basis)
        else: result=release(a.db,a.id,a.reason)
        print(json.dumps(result,indent=2)); return 0
    except (BudgetError,sqlite3.Error,OSError):
        print(json.dumps({'error':'Budget operation refused; verify initialisation, unique IDs, amounts, available headroom and receipt state. No secret values are logged.'})); return 2
if __name__=='__main__': raise SystemExit(main())
