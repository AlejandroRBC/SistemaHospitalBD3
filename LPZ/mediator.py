"""
Modulo mediador LPZ.
Cada nodo tiene sus propios fragmentos:
  LPZ  local  → frag_paciente_lpz,  historial_clinico_v1/v2 (T-SQL ?)
  CBBA remoto → frag_paciente_cbba, historial_clinico_v1/v2 (PostgreSQL %s)
  STCZ remoto → frag_paciente_stcz, historial_clinico_v1/v2 (T-SQL ?)
"""
import db, config


# ── Catalogo de Fragmentacion ─────────────────────────────────────────────────

def resolver_nodo(id_paciente):
    return db.fetchone(
        'SELECT nodo, id_hospital FROM fragment_catalog WHERE id_paciente = ?',
        (id_paciente,)
    )

def registrar_en_catalogo(id_paciente, nodo, id_hospital):
    db.execute(
        """IF EXISTS (SELECT 1 FROM fragment_catalog WHERE id_paciente = ?)
               UPDATE fragment_catalog SET nodo = ?, id_hospital = ? WHERE id_paciente = ?
           ELSE
               INSERT INTO fragment_catalog (id_paciente, nodo, id_hospital) VALUES (?,?,?)""",
        (id_paciente, nodo, id_hospital, id_paciente, id_paciente, nodo, id_hospital)
    )


# ── Búsqueda distribuida ──────────────────────────────────────────────────────

def buscar_paciente_global(termino):
    resultados = []

    # LPZ: T-SQL, fragmento frag_paciente_lpz
    local = db.fetchall(
        """SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'LPZ' AS nodo
           FROM frag_paciente_lpz
           WHERE ci = ? OR (nombre + ' ' + apellido) LIKE ?""",
        (termino, f'%{termino}%')
    )
    resultados.extend(local)

    # CBBA: PostgreSQL %s, fragmento frag_paciente_cbba
    cbba, err_cbba = db.remote_fetchall('CBBA',
        """SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'CBBA' AS nodo
           FROM frag_paciente_cbba
           WHERE ci = %s OR (nombre || ' ' || apellido) ILIKE %s""",
        (termino, f'%{termino}%')
    )
    if not err_cbba:
        resultados.extend(cbba)

    # STCZ: T-SQL ?, fragmento frag_paciente_stcz
    stcz, err_stcz = db.remote_fetchall('STCZ',
        """SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'STCZ' AS nodo
           FROM frag_paciente_stcz
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
    cat = resolver_nodo(id_paciente)
    if cat:
        nodo = cat['nodo']
        if nodo == 'LPZ':
            p = db.fetchone('SELECT * FROM frag_paciente_lpz WHERE id_paciente = ?', (id_paciente,))
            return p, 'LPZ'
        sql = ('SELECT * FROM frag_paciente_cbba WHERE id_paciente = %s'
               if nodo == 'CBBA'
               else 'SELECT * FROM frag_paciente_stcz WHERE id_paciente = ?')
        rows, _ = db.remote_fetchall(nodo, sql, (id_paciente,))
        if rows:
            return rows[0], nodo

    # Fallback: buscar en los 3 fragmentos
    p = db.fetchone('SELECT * FROM frag_paciente_lpz WHERE id_paciente = ?', (id_paciente,))
    if p: return p, 'LPZ'
    rows, _ = db.remote_fetchall('CBBA', 'SELECT * FROM frag_paciente_cbba WHERE id_paciente = %s', (id_paciente,))
    if rows: return rows[0], 'CBBA'
    rows, _ = db.remote_fetchall('STCZ', 'SELECT * FROM frag_paciente_stcz WHERE id_paciente = ?', (id_paciente,))
    if rows: return rows[0], 'STCZ'
    return None, None


def obtener_historial_critico(id_paciente):
    cat = resolver_nodo(id_paciente)
    nodos = ['LPZ', 'CBBA', 'STCZ'] if not cat else [cat['nodo']]

    for nodo in nodos:
        if nodo == 'LPZ':
            h = db.fetchone('SELECT * FROM historial_clinico_v1 WHERE id_paciente = ?', (id_paciente,))
            if h: return h, 'LPZ_local'
        elif nodo == 'CBBA':
            rows, _ = db.remote_fetchall('CBBA', 'SELECT * FROM historial_clinico_v1 WHERE id_paciente = %s', (id_paciente,))
            if rows: return rows[0], 'CBBA_remoto'
        else:
            rows, _ = db.remote_fetchall('STCZ', 'SELECT * FROM historial_clinico_v1 WHERE id_paciente = ?', (id_paciente,))
            if rows: return rows[0], 'STCZ_remoto'

    # Fallback: replica critica en historial_replica
    nodo_origen = cat['nodo'] if cat else None
    if nodo_origen:
        replica = db.fetchone(
            'SELECT * FROM historial_replica WHERE id_paciente = ? AND hospital_origen = ?',
            (id_paciente, nodo_origen)
        )
        if replica: return replica, f'{nodo_origen}_replica_local'
    return None, 'no_disponible'


# ── Transferencias ────────────────────────────────────────────────────────────

def transferir_paciente(id_paciente, id_transferencia, id_hospital_destino):
    import requests as req
    MAPA = {1: ('LPZ', config.LPZ_URL), 2: ('CBBA', config.CBBA_URL), 3: ('STCZ', config.STCZ_URL)}
    if id_hospital_destino not in MAPA:
        return False, f'Hospital {id_hospital_destino} no reconocido.'
    nodo_destino, url_destino = MAPA[id_hospital_destino]

    paciente = db.fetchone('SELECT * FROM frag_paciente_lpz WHERE id_paciente = ?', (id_paciente,))
    if not paciente:
        return False, f'Paciente {id_paciente} no encontrado en frag_paciente_lpz.'
    hist_v1 = db.fetchone('SELECT * FROM historial_clinico_v1 WHERE id_paciente = ?', (id_paciente,))
    hist_v2 = db.fetchone('SELECT * FROM historial_clinico_v2 WHERE id_paciente = ?', (id_paciente,))

    payload = {
        'id_paciente'          : paciente['id_paciente'],
        'nombre'               : paciente['nombre'],
        'apellido'             : paciente['apellido'],
        'ci'                   : paciente['ci'],
        'fecha_nacimiento'     : str(paciente['fecha_nacimiento']) if paciente.get('fecha_nacimiento') else None,
        'sexo'                 : paciente['sexo'],
        'direccion'            : paciente.get('direccion') or '',
        'telefono'             : paciente.get('telefono') or '',
        'tipo_sangre'          : paciente.get('tipo_sangre') or '',
        'alergias'             : paciente.get('alergias') or '',
        'enfermedades_cronicas': hist_v1['enfermedades_cronicas'] if hist_v1 else '',
        'antecedentes'         : hist_v2['antecedentes'] if hist_v2 else '',
        'observaciones'        : hist_v2['observaciones'] if hist_v2 else '',
    }

    try:
        r = req.post(f'{url_destino}/api/transferir', json=payload, timeout=10)
        if r.status_code != 200 or not r.json().get('success'):
            return False, f'Nodo {nodo_destino} rechazo la transferencia.'
    except Exception as e:
        return False, f'Error al conectar con {nodo_destino}: {e}'

    registrar_en_catalogo(id_paciente, nodo_destino, id_hospital_destino)
    db.execute('UPDATE frag_transferencia_lpz SET estado = ? WHERE id_transferencia = ?',
               ('Completada', id_transferencia))
    _log('TRANSFERENCIA', 'LPZ', nodo_destino, id_paciente,
         f'Paciente transferido a {nodo_destino}')

    otros = [n for n in ['CBBA', 'STCZ'] if n != nodo_destino]
    for otro in otros:
        _replicar_a_nodo(otro, id_paciente, nodo_destino,
                         payload['tipo_sangre'], payload['alergias'], payload['enfermedades_cronicas'])
    return True, f'Paciente transferido a {nodo_destino} exitosamente.'


def transferir_paciente_desde_remoto(nodo_origen, id_paciente, id_transferencia, id_hospital_destino):
    import requests as req
    MAPA = {1: ('LPZ', config.LPZ_URL), 2: ('CBBA', config.CBBA_URL), 3: ('STCZ', config.STCZ_URL)}
    if id_hospital_destino not in MAPA:
        return False, f'Hospital {id_hospital_destino} no reconocido.'
    nodo_destino, url_destino = MAPA[id_hospital_destino]

    # Obtener datos del fragmento remoto
    if nodo_origen == 'CBBA':
        rows_p, err_p = db.remote_fetchall('CBBA', 'SELECT * FROM frag_paciente_cbba WHERE id_paciente = %s', (id_paciente,))
        rows_v1, _   = db.remote_fetchall('CBBA', 'SELECT * FROM historial_clinico_v1 WHERE id_paciente = %s', (id_paciente,))
        rows_v2, _   = db.remote_fetchall('CBBA', 'SELECT * FROM historial_clinico_v2 WHERE id_paciente = %s', (id_paciente,))
    else:  # STCZ
        rows_p, err_p = db.remote_fetchall('STCZ', 'SELECT * FROM frag_paciente_stcz WHERE id_paciente = ?', (id_paciente,))
        rows_v1, _   = db.remote_fetchall('STCZ', 'SELECT * FROM historial_clinico_v1 WHERE id_paciente = ?', (id_paciente,))
        rows_v2, _   = db.remote_fetchall('STCZ', 'SELECT * FROM historial_clinico_v2 WHERE id_paciente = ?', (id_paciente,))

    if err_p or not rows_p:
        return False, f'Paciente {id_paciente} no encontrado en {nodo_origen}: {err_p}'

    paciente = rows_p[0]
    hist_v1  = rows_v1[0] if rows_v1 else None
    hist_v2  = rows_v2[0] if rows_v2 else None
    payload  = {
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

    if nodo_destino == 'LPZ':
        try:
            db.execute_batch(
                "SET IDENTITY_INSERT frag_paciente_lpz ON; "
                "INSERT INTO frag_paciente_lpz (id_paciente, nombre, apellido, ci, fecha_nacimiento, sexo, "
                "direccion, telefono, tipo_sangre, alergias, id_hospital) VALUES (?,?,?,?,?,?,?,?,?,?,?); "
                "SET IDENTITY_INSERT frag_paciente_lpz OFF;",
                (id_paciente, payload['nombre'], payload['apellido'], payload['ci'],
                 payload['fecha_nacimiento'], payload['sexo'], payload['direccion'],
                 payload['telefono'], payload['tipo_sangre'], payload['alergias'], config.ID_HOSPITAL)
            )
            db.execute(
                "INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas) VALUES (?,?,?,?)",
                (id_paciente, payload['tipo_sangre'], payload['alergias'], payload['enfermedades_cronicas'])
            )
            hid = db.fetchone('SELECT id_historial FROM historial_clinico_v1 WHERE id_paciente = ?', (id_paciente,))
            if hid:
                db.execute(
                    "INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones) VALUES (?,?,CAST(GETDATE() AS DATE),?,?)",
                    (hid['id_historial'], id_paciente, payload['antecedentes'], payload['observaciones'])
                )
        except Exception as e:
            return False, f'Error al insertar en frag_paciente_lpz: {e}'
    else:
        try:
            r = req.post(f'{url_destino}/api/transferir', json=payload, timeout=10)
            if r.status_code != 200 or not r.json().get('success'):
                return False, f'Nodo {nodo_destino} rechazo la transferencia.'
        except Exception as e:
            return False, f'Error al conectar con {nodo_destino}: {e}'

    registrar_en_catalogo(id_paciente, nodo_destino, id_hospital_destino)

    # Actualizar estado en el fragmento del nodo origen
    if nodo_origen == 'CBBA':
        db.remote_execute('CBBA',
            'UPDATE frag_transferencia_cbba SET estado = %s WHERE id_transferencia = %s',
            ('Completada', id_transferencia))
    else:
        db.remote_execute('STCZ',
            'UPDATE frag_transferencia_stcz SET estado = ? WHERE id_transferencia = ?',
            ('Completada', id_transferencia))

    _log('TRANSFERENCIA', nodo_origen, nodo_destino, id_paciente,
         f'Transferido desde {nodo_origen} a {nodo_destino}')

    otros = [n for n in ['CBBA', 'STCZ'] if n not in (nodo_destino, nodo_origen)]
    for otro in otros:
        _replicar_a_nodo(otro, id_paciente, nodo_destino,
                         payload['tipo_sangre'], payload['alergias'], payload['enfermedades_cronicas'])
    return True, f'Paciente transferido desde {nodo_origen} a {nodo_destino} exitosamente.'


# ── Replicación critica ───────────────────────────────────────────────────────

def _replicar_a_nodo(nodo, id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas):
    if nodo == 'CBBA':
        db.remote_execute('CBBA', """
            INSERT INTO historial_replica (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (id_paciente, hospital_origen) DO UPDATE
            SET tipo_sangre=EXCLUDED.tipo_sangre, alergias=EXCLUDED.alergias,
                enfermedades_cronicas=EXCLUDED.enfermedades_cronicas, fecha_actualizacion=NOW()
        """, (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas))
    else:  # STCZ
        db.remote_execute('STCZ', """
            IF EXISTS (SELECT 1 FROM historial_replica WHERE id_paciente=? AND hospital_origen=?)
                UPDATE historial_replica
                SET tipo_sangre=?, alergias=?, enfermedades_cronicas=?, fecha_actualizacion=GETDATE()
                WHERE id_paciente=? AND hospital_origen=?
            ELSE
                INSERT INTO historial_replica (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas)
                VALUES (?,?,?,?,?)
        """, (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas,
              id_paciente, hospital_origen,
              id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas))


def replicar_critico_a_remotos(id_paciente, origen, tipo_sangre, alergias, enfermedades_cronicas):
    for nodo in ['CBBA', 'STCZ']:
        _replicar_a_nodo(nodo, id_paciente, origen, tipo_sangre, alergias, enfermedades_cronicas)
    _log('REPLICA_V1', 'LPZ', 'CBBA+STCZ', id_paciente, f'Replicacion critica desde {origen}')


def replicar_catalogo_a_remotos(nombre, descripcion, dosis, fabricante):
    db.remote_execute('CBBA', "INSERT INTO medicamento (nombre, descripcion, dosis, fabricante) VALUES (%s,%s,%s,%s)",
                      (nombre, descripcion, dosis, fabricante))
    db.remote_execute('STCZ', "INSERT INTO medicamento (nombre, descripcion, dosis, fabricante) VALUES (?,?,?,?)",
                      (nombre, descripcion, dosis, fabricante))


# ── Log ───────────────────────────────────────────────────────────────────────

def _log(accion, origen, destino, id_paciente, detalles=''):
    try:
        db.execute(
            "INSERT INTO distributed_logs (accion, nodo_origen, nodo_destino, id_paciente, detalles) VALUES (?,?,?,?,?)",
            (accion, origen, destino, id_paciente, detalles)
        )
    except Exception:
        pass
