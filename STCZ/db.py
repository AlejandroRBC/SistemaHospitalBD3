import pyodbc
import requests
import config


# ── SQL Server local (STCZ) ───────────────────────────────────────────────────

def _conn():
    cs = (
        f"DRIVER={{{config.SQL_DB['driver']}}};"
        f"SERVER={config.SQL_DB['server']},{config.SQL_DB['port']};"
        f"DATABASE={config.SQL_DB['database']};"
        f"UID={config.SQL_DB['user']};PWD={config.SQL_DB['password']};"
        f"Connection Timeout=10;"
    )
    return pyodbc.connect(cs)


def fetchall(sql, params=None):
    conn = _conn()
    cur  = conn.cursor()
    cur.execute(sql, params or [])
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def fetchone(sql, params=None):
    rows = fetchall(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    conn = _conn()
    cur  = conn.cursor()
    cur.execute(sql, params or [])
    try:
        cur.execute('SELECT @@IDENTITY')
        val = cur.fetchone()[0]
    except Exception:
        val = None
    conn.commit()
    cur.close(); conn.close()
    return int(val) if val is not None else None


def execute_batch(sql, params=None):
    """Ejecuta SQL batch (ej: SET IDENTITY_INSERT + INSERT) sin SCOPE_IDENTITY."""
    conn = _conn()
    cur  = conn.cursor()
    cur.execute(sql, params or [])
    conn.commit()
    cur.close(); conn.close()


# ── Consulta directa al SQL Server LPZ via pyodbc ────────────────────────────
# LPZ es ahora SQL Server — conexion directa estandar SQL Server a SQL Server

def _lpz_sql_conn():
    """Conexion directa al SQL Server de LPZ."""
    cs = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={config.LPZ_URL.replace('http://', '').split(':')[0]},1433;"
        f"DATABASE=hospital_lpz;"
        f"UID=sa;PWD=123456;"
        f"Connection Timeout=5;"
    )
    return pyodbc.connect(cs)


def openquery_lpz(tsql):
    """Ejecuta una consulta T-SQL directa en el SQL Server de LPZ via Linked Server.
    La consulta tsql debe usar sintaxis T-SQL (?, +, LIKE, GETDATE()).
    """
    safe = tsql.replace("'", "''")
    sql  = f"SELECT * FROM OPENQUERY(LPZ_LINK, '{safe}')"
    try:
        conn = _conn()
        cur  = conn.cursor()
        cur.execute(sql)
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


def lpz_post(endpoint, payload, timeout=5):
    """POST al nodo LPZ. Retorna (data, error)."""
    try:
        r = requests.post(f"{config.LPZ_URL}{endpoint}", json=payload, timeout=timeout)
        return r.json(), None
    except Exception as e:
        return None, str(e)
