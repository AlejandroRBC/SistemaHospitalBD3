"""
Modulo mediador del nodo LPZ.
Implementa: catalogo de fragmentacion, query distribuido, wrappers y replicacion.
"""
import db
import config


# ── Catalogo de Fragmentacion ─────────────────────────────────────────────────

def resolver_nodo(id_paciente):
    """Consulta el catalogo local para saber en que nodo vive el paciente."""
    row = db.fetchone(
        'SELECT nodo, id_hospital FROM fragment_catalog WHERE id_paciente = %s',
        (id_paciente,)
    )
    return row  # {'nodo': 'LPZ'|'CBBA'|'STCZ', 'id_hospital': ...} o None


def registrar_en_catalogo(id_paciente, nodo, id_hospital):
    db.execute(
        """INSERT INTO fragment_catalog (id_paciente, nodo, id_hospital)
           VALUES (%s, %s, %s)
           ON CONFLICT (id_paciente) DO UPDATE
           SET nodo=EXCLUDED.nodo, id_hospital=EXCLUDED.id_hospital""",
        (id_paciente, nodo, id_hospital)
    )


# ── Busqueda distribuida de paciente ─────────────────────────────────────────

def buscar_paciente_global(termino):
    """
    Busca un paciente por CI o nombre en los 3 nodos.
    Retorna lista de resultados con campo 'nodo' indicando origen.
    """
    resultados = []

    # Fragmento LPZ (PostgreSQL local)
    local = db.fetchall(
        """SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'LPZ' AS nodo
           FROM paciente
           WHERE ci = %s OR (nombre || ' ' || apellido) ILIKE %s""",
        (termino, f'%{termino}%')
    )
    resultados.extend(local)

    # Fragmento CBBA (SQL Server remoto via pyodbc)
    cbba, err_cbba = db.remote_fetchall('CBBA',
        """SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'CBBA' AS nodo
           FROM paciente
           WHERE ci = ? OR (nombre + ' ' + apellido) LIKE ?""",
        (termino, f'%{termino}%')
    )
    if not err_cbba:
        resultados.extend(cbba)

    # Fragmento STCZ (SQL Server remoto via pyodbc)
    stcz, err_stcz = db.remote_fetchall('STCZ',
        """SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'STCZ' AS nodo
           FROM paciente
           WHERE ci = ? OR (nombre + ' ' + apellido) LIKE ?""",
        (termino, f'%{termino}%')
    )
    if not err_stcz:
        resultados.extend(stcz)

    errores = {}
    if err_cbba: errores['CBBA'] = err_cbba
    if err_stcz: errores['STCZ'] = err_stcz

    return resultados, errores


def obtener_paciente_por_id(id_paciente):
    """
    Localiza un paciente en cualquier nodo usando el catalogo de fragmentacion.
    Retorna (datos_paciente, nodo_origen) o (None, None).
    """
    cat = resolver_nodo(id_paciente)
    if not cat:
        return None, None

    nodo = cat['nodo']
    if nodo == 'LPZ':
        p = db.fetchone('SELECT * FROM paciente WHERE id_paciente = %s', (id_paciente,))
        return p, 'LPZ'

    rows, err = db.remote_fetchall(nodo,
        'SELECT * FROM paciente WHERE id_paciente = ?', (id_paciente,)
    )
    return (rows[0] if rows else None), nodo


def obtener_historial_critico(id_paciente):
    """
    Obtiene el fragmento V1 (critico) del historial del paciente.
    Si el nodo origen no esta disponible, usa la replica local.
    """
    cat = resolver_nodo(id_paciente)
    if not cat:
        return None, 'sin_catalogo'

    nodo = cat['nodo']
    if nodo == 'LPZ':
        h = db.fetchone(
            'SELECT * FROM historial_clinico_v1 WHERE id_paciente = %s', (id_paciente,)
        )
        return h, 'LPZ_local'

    # Intentar en nodo remoto
    rows, err = db.remote_fetchall(nodo,
        'SELECT * FROM historial_clinico_v1 WHERE id_paciente = ?', (id_paciente,)
    )
    if rows:
        return rows[0], f'{nodo}_remoto'

    # Fallback: replica critica almacenada localmente
    replica = db.fetchone(
        """SELECT * FROM historial_replica
           WHERE id_paciente = %s AND hospital_origen = %s""",
        (id_paciente, nodo)
    )
    if replica:
        return replica, f'{nodo}_replica_local'

    return None, 'no_disponible'


# ── Replicacion critica ───────────────────────────────────────────────────────

def replicar_critico_a_remotos(id_paciente, origen, tipo_sangre, alergias, enfermedades_cronicas):
    """
    Envía el fragmento critico V1 de un nuevo paciente a los otros 2 nodos.
    Estrategia: replica parcial asincrona.
    """
    for nodo in ['CBBA', 'STCZ']:
        sql = """
            IF EXISTS (SELECT 1 FROM historial_replica WHERE id_paciente = ? AND hospital_origen = ?)
                UPDATE historial_replica
                SET tipo_sangre=?, alergias=?, enfermedades_cronicas=?, fecha_actualizacion=GETDATE()
                WHERE id_paciente=? AND hospital_origen=?
            ELSE
                INSERT INTO historial_replica (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas)
                VALUES (?,?,?,?,?)
        """
        db.remote_execute(nodo, sql, (
            id_paciente, origen,
            tipo_sangre, alergias, enfermedades_cronicas,
            id_paciente, origen,
            id_paciente, origen, tipo_sangre, alergias, enfermedades_cronicas
        ))

    _log('REPLICA_V1', 'LPZ', 'CBBA+STCZ', id_paciente,
         f'Replicacion critica desde {origen}')


def replicar_catalogo_a_remotos(nombre, descripcion, dosis, fabricante):
    """Propaga un nuevo medicamento (catalogo nacional) a CBBA y STCZ."""
    for nodo in ['CBBA', 'STCZ']:
        db.remote_execute(nodo,
            "INSERT INTO medicamento (nombre, descripcion, dosis, fabricante) VALUES (?,?,?,?)",
            (nombre, descripcion, dosis, fabricante)
        )


# ── Logs de operaciones distribuidas ─────────────────────────────────────────

def _log(accion, origen, destino, id_paciente, detalles=''):
    try:
        db.execute(
            """INSERT INTO distributed_logs (accion, nodo_origen, nodo_destino, id_paciente, detalles)
               VALUES (%s,%s,%s,%s,%s)""",
            (accion, origen, destino, id_paciente, detalles)
        )
    except Exception:
        pass  # Logs no deben interrumpir el flujo principal
