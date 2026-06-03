import pyodbc
import psycopg2
import psycopg2.extras
import config


# ── SQL Server local (LPZ) ────────────────────────────────────────────────────

def _lpz_conn():
    cs = (
        f"DRIVER={{{config.LPZ_DB['driver']}}};"
        f"SERVER={config.LPZ_DB['server']},{config.LPZ_DB['port']};"
        f"DATABASE={config.LPZ_DB['database']};"
        f"UID={config.LPZ_DB['user']};PWD={config.LPZ_DB['password']};"
        f"Connection Timeout=10;"
    )
    return pyodbc.connect(cs)


def fetchall(sql, params=None):
    conn = _lpz_conn()
    cur  = conn.cursor()
    cur.execute(sql, params or [])
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def fetchone(sql, params=None):
    rows = fetchall(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None, returning=False):
    conn = _lpz_conn()
    cur  = conn.cursor()
    cur.execute(sql, params or [])
    result = None
    if returning:
        # @@IDENTITY devuelve el ultimo IDENTITY insertado en esta sesion/conexion
        cur.execute('SELECT @@IDENTITY AS id')
        row = cur.fetchone()
        result = int(row[0]) if row and row[0] is not None else None
    conn.commit()
    cur.close(); conn.close()
    return result


def execute_batch(sql, params=None):
    """Ejecuta SQL batch (ej: SET IDENTITY_INSERT + INSERT) sin recuperar ID."""
    conn = _lpz_conn()
    cur  = conn.cursor()
    cur.execute(sql, params or [])
    conn.commit()
    cur.close(); conn.close()


# ── PostgreSQL remoto (CBBA) via psycopg2 ────────────────────────────────────

def _cbba_conn():
    cfg = dict(config.CBBA_PG)
    cfg['connect_timeout'] = 5   # no esperar mas de 5s si CBBA no responde
    return psycopg2.connect(**cfg)


# ── SQL Server remoto (STCZ) via pyodbc ──────────────────────────────────────

def _stcz_connstr():
    cfg = config.STCZ_SQL
    return (
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={cfg['server']},{cfg['port']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['user']};PWD={cfg['password']};"
        f"Connection Timeout=5;"
    )


def remote_fetchall(nodo, sql, params=None):
    """Ejecuta SELECT en nodo remoto. Retorna (filas, error).
    CBBA usa sintaxis PostgreSQL (%s, ||, ILIKE).
    STCZ usa sintaxis T-SQL (?, +, LIKE).
    """
    try:
        if nodo == 'CBBA':
            conn = _cbba_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params or [])
            rows = [dict(r) for r in cur.fetchall()]
        else:  # STCZ
            conn = pyodbc.connect(_stcz_connstr())
            cur  = conn.cursor()
            cur.execute(sql, params or [])
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows, None
    except Exception as e:
        return [], str(e)


def remote_fetchall_batch(nodo, queries):
    """Ejecuta multiples SELECTs en un nodo remoto con UNA SOLA conexion.
    queries = [(key, sql, params), ...]
    Retorna (dict{key: [filas]}, error_str | None)
    """
    try:
        results = {}
        if nodo == 'CBBA':
            conn = _cbba_conn()
            cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            for key, sql, params in queries:
                cur.execute(sql, params or [])
                results[key] = [dict(r) for r in cur.fetchall()]
        else:  # STCZ
            conn = pyodbc.connect(_stcz_connstr())
            cur  = conn.cursor()
            for key, sql, params in queries:
                cur.execute(sql, params or [])
                cols = [c[0] for c in cur.description]
                results[key] = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close(); conn.close()
        return results, None
    except Exception as e:
        return {key: [] for key, _, _ in queries}, str(e)


def remote_execute(nodo, sql, params=None):
    """Ejecuta INSERT/UPDATE/DELETE en nodo remoto. Retorna (ok, error).
    CBBA usa sintaxis PostgreSQL (%s, ON CONFLICT).
    STCZ usa sintaxis T-SQL (?, IF EXISTS).
    """
    try:
        if nodo == 'CBBA':
            conn = _cbba_conn()
            cur  = conn.cursor()
            cur.execute(sql, params or [])
            conn.commit()
        else:  # STCZ
            conn = pyodbc.connect(_stcz_connstr())
            cur  = conn.cursor()
            cur.execute(sql, params or [])
            conn.commit()
        cur.close(); conn.close()
        return True, None
    except Exception as e:
        return False, str(e)
