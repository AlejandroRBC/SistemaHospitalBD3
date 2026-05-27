import pyodbc
from config import SQL_SERVER


def get_connection():
    conn_str = (
        f"DRIVER={SQL_SERVER['driver']};"
        f"SERVER={SQL_SERVER['server']};"
        f"DATABASE={SQL_SERVER['database']};"
        f"UID={SQL_SERVER['username']};"
        f"PWD={SQL_SERVER['password']}"
    )
    return pyodbc.connect(conn_str)


def execute_query(query, params=None, fetchone=False, fetchall=False):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    result = None
    if fetchone:
        result = cur.fetchone()
    elif fetchall:
        result = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return result


def check_connection():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return True
    except Exception:
        return False


def execute_openquery(inner_sql, linked_server=None):
    from config import LPZ_LINKED_SERVER

    ls = linked_server or LPZ_LINKED_SERVER
    escaped = inner_sql.replace("'", "''")
    full_sql = f"SELECT * FROM OPENQUERY({ls}, '{escaped}')"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(full_sql)
    try:
        rows = cur.fetchall()
    except pyodbc.ProgrammingError:
        rows = []
    conn.commit()
    cur.close()
    conn.close()
    return rows


def execute_openquery_insert(table, columns, values, linked_server=None):
    from config import LPZ_LINKED_SERVER

    ls = linked_server or LPZ_LINKED_SERVER
    cols = ", ".join(columns)
    placeholders = ", ".join(["?" for _ in values])
    inner = f"SELECT {cols} FROM {table} WHERE 1=0"
    escaped = inner.replace("'", "''")
    full_sql = f"INSERT OPENQUERY({ls}, '{escaped}') VALUES ({placeholders})"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(full_sql, values)
    conn.commit()
    cur.close()
    conn.close()
