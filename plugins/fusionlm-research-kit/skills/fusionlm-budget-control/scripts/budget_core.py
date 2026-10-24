"""Local transactional budget admission; not a provider-side billing cap."""
import re
import sqlite3
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path

HARD_MAX = 290_000_000
class BudgetError(Exception):
    pass

def micro(value):
    try:
        d = Decimal(str(value))
        if not d.is_finite() or d < 0:
            raise BudgetError('amount must be a finite nonnegative decimal')
        return int((d * 1_000_000).to_integral_value(rounding=ROUND_CEILING))
    except (InvalidOperation, ValueError):
        raise BudgetError('invalid decimal amount') from None

def usd(value):
    return format(Decimal(value) / Decimal(1_000_000), '.6f')

def _identifier(value):
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', value):
        raise BudgetError('use a nonsensitive alphanumeric request id up to 128 characters')

def _connect(db):
    path = Path(db)
    if path.is_symlink():
        raise BudgetError('budget database must not be a symlink')
    c = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    c.row_factory = sqlite3.Row
    return c

def _state(c):
    row = c.execute('SELECT cap FROM metadata WHERE singleton=1').fetchone()
    if row is None:
        raise BudgetError('budget not initialised')
    sums = c.execute("SELECT COALESCE(SUM(CASE WHEN state='reserved' THEN reserved ELSE 0 END),0), COALESCE(SUM(CASE WHEN state='settled' THEN actual ELSE 0 END),0) FROM entries").fetchone()
    outstanding, booked = map(int, sums)
    available = int(row['cap']) - outstanding - booked
    counts = dict((r[0], r[1]) for r in c.execute('SELECT state,COUNT(*) FROM entries GROUP BY state'))
    return {'limit_usd':usd(row['cap']),'booked_or_settled_usd':usd(booked),'outstanding_usd':usd(outstanding),'available_usd':usd(available),'overcommitted':available < 0,'counts':counts,'note':'Local records only; reconcile unwrapped and enclosing-runtime costs separately.'}

def initialise(db, limit='290'):
    cap = micro(limit)
    if cap <= 0 or cap > HARD_MAX:
        raise BudgetError('limit must be positive and at most 290 USD')
    p = Path(db)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = _connect(db)
    try:
        c.execute('BEGIN IMMEDIATE')
        c.execute('CREATE TABLE IF NOT EXISTS metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1), cap INTEGER NOT NULL)')
        c.execute("CREATE TABLE IF NOT EXISTS entries(id TEXT PRIMARY KEY, category TEXT NOT NULL, reserved INTEGER NOT NULL, actual INTEGER, state TEXT NOT NULL, basis TEXT NOT NULL, updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        row = c.execute('SELECT cap FROM metadata WHERE singleton=1').fetchone()
        if row and row['cap'] != cap:
            raise BudgetError('existing budget cannot be reinitialised with a different ceiling')
        if not row:
            c.execute('INSERT INTO metadata VALUES(1,?)',(cap,))
        result = _state(c)
        c.commit()
        p.chmod(0o600)
        return result
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def status(db):
    if not Path(db).is_file():
        raise BudgetError('budget database missing; initialise once')
    c = _connect(db)
    try:
        return _state(c)
    finally:
        c.close()

def reserve(db, request_id, amount, category='research'):
    _identifier(request_id)
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}',category):
        raise BudgetError('invalid category')
    cost = micro(amount)
    if cost <= 0:
        raise BudgetError('reservation must be positive')
    if not Path(db).is_file():
        raise BudgetError('budget database missing')
    c = _connect(db)
    try:
        c.execute('BEGIN IMMEDIATE')
        state = _state(c)
        if c.execute('SELECT 1 FROM entries WHERE id=?',(request_id,)).fetchone():
            raise BudgetError('request id already exists; reconcile it instead of dispatching twice')
        if state['available_usd'].startswith('-') or cost > micro(state['available_usd']):
            raise BudgetError('insufficient unreserved campaign headroom')
        c.execute("INSERT INTO entries(id,category,reserved,state,basis) VALUES(?,?,?,'reserved','pending')",(request_id,category,cost))
        c.commit()
        return status(db)
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def settle(db, request_id, amount, basis='actual-receipt'):
    _identifier(request_id)
    if basis not in ('actual-receipt','upper-bound','estimate'):
        raise BudgetError('invalid settlement basis')
    cost = micro(amount)
    if not Path(db).is_file():
        raise BudgetError('budget database missing')
    c = _connect(db)
    try:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT * FROM entries WHERE id=?',(request_id,)).fetchone()
        if not row or row['state']=='released':
            raise BudgetError('no live reservation or reconcilable booking')
        if row['state']=='settled':
            if row['actual']==cost and row['basis']==basis:
                c.commit()
                return status(db)
            if row['basis']=='actual-receipt' or basis!='actual-receipt':
                raise BudgetError('only a conservative booking may be reconciled to an actual receipt')
        c.execute("UPDATE entries SET actual=?,state='settled',basis=?,updated=CURRENT_TIMESTAMP WHERE id=?",(cost,basis,request_id))
        c.commit()
        result = status(db)
        result['reservation_overrun'] = cost > row['reserved']
        return result
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def release(db, request_id, reason):
    if reason not in ('confirmed-no-charge','cancelled-before-dispatch'):
        raise BudgetError('release needs confirmed-no-charge or cancelled-before-dispatch')
    if not Path(db).is_file():
        raise BudgetError('budget database missing')
    c = _connect(db)
    try:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT state FROM entries WHERE id=?',(request_id,)).fetchone()
        if not row:
            raise BudgetError('unknown request id')
        if row['state']=='settled':
            raise BudgetError('cannot release a settled charge')
        c.execute("UPDATE entries SET state='released',basis=?,updated=CURRENT_TIMESTAMP WHERE id=?",(reason,request_id))
        c.commit()
        return status(db)
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()
