import psycopg2
from config import POSTGRES


def get_connection():
    return psycopg2.connect(
        host=POSTGRES["host"],
        database=POSTGRES["database"],
        user=POSTGRES["user"],
        password=POSTGRES["password"]
    )


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
