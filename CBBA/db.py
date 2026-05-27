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
