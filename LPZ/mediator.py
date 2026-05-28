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
    Si no hay entrada en el catalogo, busca en los 3 nodos como fallback.
    Retorna (datos_paciente, nodo_origen) o (None, None).
    """
    cat = resolver_nodo(id_paciente)
    if cat:
        nodo = cat['nodo']
        if nodo == 'LPZ':
            p = db.fetchone('SELECT * FROM paciente WHERE id_paciente = %s', (id_paciente,))
            return p, 'LPZ'
        rows, err = db.remote_fetchall(nodo,
            'SELECT * FROM paciente WHERE id_paciente = ?', (id_paciente,)
        )
        if rows:
            return rows[0], nodo

    # Fallback: buscar en LPZ directo
    p = db.fetchone('SELECT * FROM paciente WHERE id_paciente = %s', (id_paciente,))
    if p:
        return p, 'LPZ'

    # Fallback: buscar en CBBA y STCZ
    for nodo in ['CBBA', 'STCZ']:
        rows, err = db.remote_fetchall(nodo,
            'SELECT * FROM paciente WHERE id_paciente = ?', (id_paciente,)
        )
        if rows:
            return rows[0], nodo

    return None, None


def obtener_historial_critico(id_paciente):
    """
    Obtiene el fragmento V1 (critico) del historial del paciente.
    Si el nodo origen no esta disponible, usa la replica local.
    Si no hay entrada en el catalogo, busca en los 3 nodos como fallback.
    """
    cat = resolver_nodo(id_paciente)
    nodos_a_intentar = ['LPZ', 'CBBA', 'STCZ'] if not cat else [cat['nodo']]

    for nodo in nodos_a_intentar:
        if nodo == 'LPZ':
            h = db.fetchone(
                'SELECT * FROM historial_clinico_v1 WHERE id_paciente = %s', (id_paciente,)
            )
            if h:
                return h, 'LPZ_local'
        else:
            rows, err = db.remote_fetchall(nodo,
                'SELECT * FROM historial_clinico_v1 WHERE id_paciente = ?', (id_paciente,)
            )
            if rows:
                return rows[0], f'{nodo}_remoto'

    # Fallback: replica critica almacenada localmente
    nodo_origen = cat['nodo'] if cat else None
    if nodo_origen:
        replica = db.fetchone(
            """SELECT * FROM historial_replica
               WHERE id_paciente = %s AND hospital_origen = %s""",
            (id_paciente, nodo_origen)
        )
        if replica:
            return replica, f'{nodo_origen}_replica_local'

    return None, 'no_disponible'


# ── Transferencia hospitalaria ─────────────────────────────────────────────────

def transferir_paciente(id_paciente, id_transferencia, id_hospital_destino):
    """
    Transfiere un paciente desde LPZ a otro nodo:
      1. Obtiene datos del paciente e historial desde LPZ
      2. Llama a la API del hospital destino para crear/recibir al paciente
      3. Actualiza el fragment_catalog con el nuevo nodo
      4. Cambia el estado de la transferencia a 'Completada'
      5. Registra en el log distribuido
    Retorna (exito: bool, mensaje: str).
    """
    import requests as req

    # Mapa: id_hospital -> (nodo, url)
    MAPA = {
        1: ('LPZ',  config.LPZ_URL),
        2: ('CBBA', config.CBBA_URL),
        3: ('STCZ', config.STCZ_URL),
    }

    if id_hospital_destino not in MAPA:
        return False, f'Hospital destino {id_hospital_destino} no reconocido.'

    nodo_destino, url_destino = MAPA[id_hospital_destino]

    # 1. Obtener datos del paciente e historial desde LPZ
    paciente = db.fetchone(
        'SELECT * FROM paciente WHERE id_paciente = %s', (id_paciente,)
    )
    if not paciente:
        return False, f'Paciente ID {id_paciente} no encontrado en LPZ.'

    hist_v1 = db.fetchone(
        'SELECT * FROM historial_clinico_v1 WHERE id_paciente = %s', (id_paciente,)
    )
    hist_v2 = db.fetchone(
        'SELECT * FROM historial_clinico_v2 WHERE id_paciente = %s', (id_paciente,)
    )

    payload = {
        'id_paciente'          : paciente['id_paciente'],
        'nombre'               : paciente['nombre'],
        'apellido'             : paciente['apellido'],
        'ci'                   : paciente['ci'],
        'fecha_nacimiento'     : str(paciente['fecha_nacimiento']) if paciente.get('fecha_nacimiento') else None,
        'sexo'                 : paciente['sexo'],
        'direccion'            : paciente['direccion'] or '',
        'telefono'             : paciente['telefono'] or '',
        'tipo_sangre'          : paciente['tipo_sangre'] or '',
        'alergias'             : paciente['alergias'] or '',
        'enfermedades_cronicas': hist_v1['enfermedades_cronicas'] if hist_v1 else '',
        'antecedentes'         : hist_v2['antecedentes'] if hist_v2 else '',
        'observaciones'        : hist_v2['observaciones'] if hist_v2 else '',
    }

    # 2. Llamar a la API del destino
    try:
        r = req.post(f'{url_destino}/api/transferir', json=payload, timeout=10)
        if r.status_code != 200:
            return False, f'Nodo {nodo_destino} respondio HTTP {r.status_code}'
        resp = r.json()
        if not resp.get('success'):
            return False, f'Nodo {nodo_destino} rechazo la transferencia: {resp}'
    except Exception as e:
        return False, f'Error al conectar con {nodo_destino}: {e}'

    # 3. Actualizar fragment_catalog en LPZ
    registrar_en_catalogo(id_paciente, nodo_destino, id_hospital_destino)

    # 4. Cambiar estado de la transferencia a Completada
    db.execute(
        'UPDATE transferencias_hospitalarias SET estado = %s WHERE id_transferencia = %s',
        ('Completada', id_transferencia)
    )

    # 5. Log
    _log('TRANSFERENCIA', 'LPZ', nodo_destino, id_paciente,
         f'Paciente transferido a {nodo_destino} (hospital {id_hospital_destino})')

    # 6. Replicar datos criticos desde LPZ a STCZ si destino es CBBA (y viceversa)
    #    para que el tercer nodo tenga la replica actualizada del paciente
    otros_nodos = [n for n in ['CBBA', 'STCZ'] if n != nodo_destino]
    for otro in otros_nodos:
        db.remote_execute(otro, """
            IF EXISTS (SELECT 1 FROM historial_replica WHERE id_paciente = ? AND hospital_origen = ?)
                UPDATE historial_replica
                SET tipo_sangre=?, alergias=?, enfermedades_cronicas=?, fecha_actualizacion=GETDATE()
                WHERE id_paciente=? AND hospital_origen=?
            ELSE
                INSERT INTO historial_replica (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas)
                VALUES (?,?,?,?,?)
        """, (
            id_paciente, nodo_destino,
            payload['tipo_sangre'], payload['alergias'], payload['enfermedades_cronicas'],
            id_paciente, nodo_destino,
            id_paciente, nodo_destino, payload['tipo_sangre'], payload['alergias'], payload['enfermedades_cronicas']
        ))

    return True, f'Paciente transferido a {nodo_destino} exitosamente.'


def transferir_paciente_desde_remoto(nodo_origen, id_paciente, id_transferencia, id_hospital_destino):
    """
    Transfiere un paciente desde CBBA o STCZ (remoto) hacia otro nodo.
    LPZ como mediador orquesta toda la operacion:
      1. Obtiene datos del paciente e historial desde el nodo origen (via pyodbc)
      2. Llama a la API del hospital destino para crear/recibir al paciente
      3. Actualiza el fragment_catalog con el nuevo nodo
      4. Cambia el estado de la transferencia a 'Completada' en el nodo origen
      5. Registra en el log distribuido
    Retorna (exito: bool, mensaje: str).
    """
    import requests as req

    MAPA = {
        1: ('LPZ',  config.LPZ_URL),
        2: ('CBBA', config.CBBA_URL),
        3: ('STCZ', config.STCZ_URL),
    }

    if id_hospital_destino not in MAPA:
        return False, f'Hospital destino {id_hospital_destino} no reconocido.'

    nodo_destino, url_destino = MAPA[id_hospital_destino]

    # 1. Obtener datos del paciente desde el nodo origen
    rows_p, err_p = db.remote_fetchall(nodo_origen,
        'SELECT * FROM paciente WHERE id_paciente = ?', (id_paciente,)
    )
    if err_p or not rows_p:
        return False, f'Paciente ID {id_paciente} no encontrado en {nodo_origen}: {err_p}'
    paciente = rows_p[0]

    rows_v1, _ = db.remote_fetchall(nodo_origen,
        'SELECT * FROM historial_clinico_v1 WHERE id_paciente = ?', (id_paciente,)
    )
    rows_v2, _ = db.remote_fetchall(nodo_origen,
        'SELECT * FROM historial_clinico_v2 WHERE id_paciente = ?', (id_paciente,)
    )
    hist_v1 = rows_v1[0] if rows_v1 else None
    hist_v2 = rows_v2[0] if rows_v2 else None

    payload = {
        'id_paciente'          : paciente['id_paciente'],
        'nombre'               : paciente['nombre'],
        'apellido'             : paciente['apellido'],
        'ci'                   : paciente['ci'],
        'fecha_nacimiento'     : str(paciente.get('fecha_nacimiento') or ''),
        'sexo'                 : paciente['sexo'],
        'direccion'            : paciente.get('direccion') or '',
        'telefono'             : paciente.get('telefono') or '',
        'tipo_sangre'          : paciente.get('tipo_sangre') or '',
        'alergias'             : paciente.get('alergias') or '',
        'enfermedades_cronicas': hist_v1['enfermedades_cronicas'] if hist_v1 else '',
        'antecedentes'         : hist_v2['antecedentes'] if hist_v2 else '',
        'observaciones'        : hist_v2['observaciones'] if hist_v2 else '',
    }

    # 2. Insertar en el nodo destino
    if nodo_destino == 'LPZ':
        # Insercion directa en PostgreSQL local (evita HTTP a si mismo)
        try:
            db.execute(
                """INSERT INTO paciente (id_paciente, nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (id_paciente, payload['nombre'], payload['apellido'], payload['ci'],
                 payload['fecha_nacimiento'], payload['sexo'], payload['direccion'],
                 payload['telefono'], payload['tipo_sangre'], payload['alergias'], config.ID_HOSPITAL)
            )
            db.execute(
                """INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas)
                   VALUES (%s,%s,%s,%s)""",
                (id_paciente, payload['tipo_sangre'], payload['alergias'], payload['enfermedades_cronicas'])
            )
            hid = db.fetchone('SELECT id_historial FROM historial_clinico_v1 WHERE id_paciente = %s', (id_paciente,))
            if hid:
                db.execute(
                    """INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones)
                       VALUES (%s,%s,CURRENT_DATE,%s,%s)""",
                    (hid['id_historial'], id_paciente, payload['antecedentes'], payload['observaciones'])
                )
        except Exception as e:
            return False, f'Error al insertar paciente en LPZ: {e}'
    else:
        # Llamar a la API del destino remoto
        try:
            r = req.post(f'{url_destino}/api/transferir', json=payload, timeout=10)
            if r.status_code != 200:
                return False, f'Nodo {nodo_destino} respondio HTTP {r.status_code}'
            resp = r.json()
            if not resp.get('success'):
                return False, f'Nodo {nodo_destino} rechazo la transferencia: {resp}'
        except Exception as e:
            return False, f'Error al conectar con {nodo_destino}: {e}'

    # 3. Actualizar fragment_catalog en LPZ
    registrar_en_catalogo(id_paciente, nodo_destino, id_hospital_destino)

    # 4. Cambiar estado en el nodo origen via pyodbc
    db.remote_execute(nodo_origen,
        'UPDATE transferencias_hospitalarias SET estado = ? WHERE id_transferencia = ?',
        ('Completada', id_transferencia)
    )

    # 5. Log
    _log('TRANSFERENCIA', nodo_origen, nodo_destino, id_paciente,
         f'Paciente transferido desde {nodo_origen} a {nodo_destino}')

    # 6. Replicar datos criticos al tercer nodo (el que no es origen ni destino)
    otros_nodos = [n for n in ['CBBA', 'STCZ'] if n not in (nodo_destino, nodo_origen)]
    for otro in otros_nodos:
        db.remote_execute(otro, """
            IF EXISTS (SELECT 1 FROM historial_replica WHERE id_paciente = ? AND hospital_origen = ?)
                UPDATE historial_replica
                SET tipo_sangre=?, alergias=?, enfermedades_cronicas=?, fecha_actualizacion=GETDATE()
                WHERE id_paciente=? AND hospital_origen=?
            ELSE
                INSERT INTO historial_replica (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas)
                VALUES (?,?,?,?,?)
        """, (
            id_paciente, nodo_destino,
            payload['tipo_sangre'], payload['alergias'], payload['enfermedades_cronicas'],
            id_paciente, nodo_destino,
            id_paciente, nodo_destino, payload['tipo_sangre'], payload['alergias'], payload['enfermedades_cronicas']
        ))

    return True, f'Paciente transferido desde {nodo_origen} a {nodo_destino} exitosamente.'


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
