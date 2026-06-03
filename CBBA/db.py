import psycopg2
import psycopg2.extras
import pyodbc
import requests
import config


# ── PostgreSQL local (CBBA) ───────────────────────────────────────────────────

def _conn():
    return psycopg2.connect(**config.PG_DB)


def fetchall(sql, params=None):
    conn = _conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or [])
        rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def fetchone(sql, params=None):
    rows = fetchall(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None, returning=False):
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or [])
        result = cur.fetchone()[0] if returning and cur.description else None
    conn.commit(); conn.close()
    return result


# ── Consulta directa al SQL Server LPZ via pyodbc ────────────────────────────

def _lpz_sql_conn():
    cfg = config.LPZ_SQL
    cs = (
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={cfg['server']},{cfg['port']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['user']};PWD={cfg['password']};"
        f"Connection Timeout=5;"
    )
    return pyodbc.connect(cs)


def openquery_lpz(tsql):
    """Ejecuta una consulta T-SQL directa en el SQL Server de LPZ via pyodbc."""
    try:
        conn = _lpz_sql_conn()
        cur  = conn.cursor()
        cur.execute(tsql)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows, None
    except Exception as e:
        return [], str(e)


# ── Consultas distribuidas al nodo mediador LPZ via HTTP ─────────────────────

def lpz_get(endpoint, params=None):
    """GET al nodo LPZ. Retorna (data, error)."""
    try:
        r = requests.get(f"{config.LPZ_URL}{endpoint}", params=params, timeout=5)
        return r.json(), None
    except Exception as e:
        return None, str(e)


def lpz_post(endpoint, payload):
    """POST al nodo LPZ. Retorna (data, error)."""
    try:
        r = requests.post(f"{config.LPZ_URL}{endpoint}", json=payload, timeout=5)
        return r.json(), None
    except Exception as e:
        return None, str(e)
