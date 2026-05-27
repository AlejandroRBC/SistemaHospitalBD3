import psycopg2
import psycopg2.extras
import pyodbc
import config


# ── PostgreSQL local (LPZ) ────────────────────────────────────────────────────

def _lpz_conn():
    return psycopg2.connect(**config.LPZ_DB)


def fetchall(sql, params=None):
    with _lpz_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            return [dict(r) for r in cur.fetchall()]


def fetchone(sql, params=None):
    with _lpz_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            row = cur.fetchone()
            return dict(row) if row else None


def execute(sql, params=None, returning=False):
    with _lpz_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            result = cur.fetchone()[0] if returning and cur.description else None
            conn.commit()
            return result


# ── SQL Server remoto (CBBA / STCZ) via pyodbc ───────────────────────────────

def _remote_connstr(cfg):
    return (
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={cfg['server']},{cfg['port']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['user']};PWD={cfg['password']};"
        f"Connection Timeout=5;"
    )


def _remote_conn(nodo):
    cfg = config.CBBA_SQL if nodo == 'CBBA' else config.STCZ_SQL
    return pyodbc.connect(_remote_connstr(cfg))


def remote_fetchall(nodo, sql, params=None):
    """Ejecuta SELECT en nodo remoto. Retorna (filas, error)."""
    try:
        conn = _remote_conn(nodo)
        cur  = conn.cursor()
        cur.execute(sql, params or [])
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows, None
    except Exception as e:
        return [], str(e)


def remote_execute(nodo, sql, params=None):
    """Ejecuta INSERT/UPDATE/DELETE en nodo remoto. Retorna (ok, error)."""
    try:
        conn = _remote_conn(nodo)
        cur  = conn.cursor()
        cur.execute(sql, params or [])
        conn.commit()
        cur.close(); conn.close()
        return True, None
    except Exception as e:
        return False, str(e)
