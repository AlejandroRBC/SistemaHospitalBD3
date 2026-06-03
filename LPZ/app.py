from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import db, mediator, config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

ctx = {
    'hospital': config.HOSPITAL_NOMBRE,
    'nodo'    : config.NODO,
    'color_p' : config.COLOR_PRIMARY,
    'color_s' : config.COLOR_SECONDARY,
    'color_bg': config.COLOR_BG,
}

# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    stats = {
        'pacientes'  : db.fetchone('SELECT COUNT(*) AS n FROM frag_paciente_lpz')['n'],
        'consultas'  : db.fetchone('SELECT COUNT(*) AS n FROM frag_consulta_lpz')['n'],
        'emergencias': db.fetchone('SELECT COUNT(*) AS n FROM frag_emergencia_lpz')['n'],
        'doctores'   : db.fetchone('SELECT COUNT(*) AS n FROM frag_doctor_lpz')['n'],
        'replicas'   : db.fetchone('SELECT COUNT(*) AS n FROM historial_replica')['n'],
        'logs'       : db.fetchone('SELECT COUNT(*) AS n FROM distributed_logs')['n'],
    }
    return render_template('index.html', **ctx, stats=stats)

# ── Pacientes ─────────────────────────────────────────────────────────────────

@app.route('/pacientes')
def pacientes():
    rows = db.fetchall('SELECT * FROM frag_paciente_lpz ORDER BY apellido, nombre')
    return render_template('pacientes.html', **ctx, pacientes=rows)

@app.route('/paciente/nuevo', methods=['GET', 'POST'])
def nuevo_paciente():
    if request.method == 'POST':
        d = request.form
        db.execute(
            """INSERT INTO frag_paciente_lpz
               (nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (d['nombre'], d['apellido'], d['ci'], d['fecha_nacimiento'],
             d['sexo'], d['direccion'], d['telefono'], d['tipo_sangre'],
             d['alergias'], config.ID_HOSPITAL)
        )
        pid = db.fetchone('SELECT @@IDENTITY AS id')['id']
        db.execute(
            "INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas) VALUES (?,?,?,?)",
            (pid, d['tipo_sangre'], d['alergias'], d.get('enfermedades_cronicas', ''))
        )
        db.execute(
            """INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones)
               SELECT id_historial, id_paciente, ?, ?, ?
               FROM historial_clinico_v1 WHERE id_paciente = ?""",
            (date.today(), d.get('antecedentes', ''), '', pid)
        )
        mediator.registrar_en_catalogo(pid, 'LPZ', config.ID_HOSPITAL)
        mediator.replicar_critico_a_remotos(pid, 'LPZ', d['tipo_sangre'], d['alergias'], d.get('enfermedades_cronicas', ''))
        flash('Paciente registrado y datos criticos replicados a CBBA y STCZ.', 'success')
        return redirect(url_for('paciente_detalle', id_paciente=pid))
    return render_template('paciente_form.html', **ctx)

@app.route('/paciente/<int:id_paciente>')
def paciente_detalle(id_paciente):
    p = db.fetchone('SELECT * FROM frag_paciente_lpz WHERE id_paciente = ?', (id_paciente,))
    if not p:
        flash('Paciente no encontrado.', 'danger')
        return redirect(url_for('pacientes'))
    hist_v1   = db.fetchone('SELECT * FROM historial_clinico_v1 WHERE id_paciente = ?', (id_paciente,))
    hist_v2   = db.fetchone('SELECT * FROM historial_clinico_v2 WHERE id_paciente = ?', (id_paciente,))
    consultas = db.fetchall(
        """SELECT c.*, d.nombre + ' ' + d.apellido AS medico
           FROM frag_consulta_lpz c
           JOIN frag_doctor_lpz d ON c.id_doctor = d.id_doctor
           WHERE c.id_paciente = ? ORDER BY c.fecha DESC""",
        (id_paciente,)
    )
    emergencias = db.fetchall(
        'SELECT * FROM frag_emergencia_lpz WHERE id_paciente = ? ORDER BY fecha DESC',
        (id_paciente,)
    )
    return render_template('paciente_detalle.html', **ctx,
                           paciente=p, hist_v1=hist_v1, hist_v2=hist_v2,
                           consultas=consultas, emergencias=emergencias)

# ── Historial ─────────────────────────────────────────────────────────────────

@app.route('/historial/actualizar', methods=['POST'])
def actualizar_historial():
    d   = request.form
    pid = int(d['id_paciente'])
    db.execute(
        "UPDATE historial_clinico_v1 SET tipo_sangre=?, alergias=?, enfermedades_cronicas=? WHERE id_paciente=?",
        (d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'], pid)
    )
    db.execute(
        "UPDATE historial_clinico_v2 SET antecedentes=?, observaciones=? WHERE id_paciente=?",
        (d['antecedentes'], d['observaciones'], pid)
    )
    mediator.replicar_critico_a_remotos(pid, 'LPZ', d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'])
    flash('Historial actualizado y replica sincronizada.', 'success')
    return redirect(url_for('paciente_detalle', id_paciente=pid))

# ── Consultas ─────────────────────────────────────────────────────────────────

@app.route('/consultas')
def consultas():
    rows = db.fetchall(
        """SELECT c.*, p.nombre + ' ' + p.apellido AS paciente,
                  d.nombre + ' ' + d.apellido AS medico
           FROM frag_consulta_lpz c
           JOIN frag_paciente_lpz p ON c.id_paciente = p.id_paciente
           JOIN frag_doctor_lpz   d ON c.id_doctor   = d.id_doctor
           ORDER BY c.fecha DESC, c.hora DESC"""
    )
    return render_template('consultas.html', **ctx, consultas=rows)

@app.route('/consulta/nueva', methods=['GET', 'POST'])
def nueva_consulta():
    if request.method == 'POST':
        d = request.form
        db.execute(
            "INSERT INTO frag_consulta_lpz (fecha, hora, motivo, diagnostico, id_paciente, id_doctor, id_hospital) VALUES (?,?,?,?,?,?,?)",
            (d['fecha'], d['hora'], d['motivo'], d['diagnostico'],
             d['id_paciente'], d['id_doctor'], config.ID_HOSPITAL)
        )
        flash('Consulta registrada correctamente.', 'success')
        return redirect(url_for('consultas'))
    pacientes_list = db.fetchall('SELECT id_paciente, nombre, apellido FROM frag_paciente_lpz ORDER BY apellido')
    doctores_list  = db.fetchall('SELECT id_doctor, nombre, apellido, especialidad FROM frag_doctor_lpz ORDER BY apellido')
    return render_template('consulta_form.html', **ctx, pacientes=pacientes_list, doctores=doctores_list)

# ── Emergencias ───────────────────────────────────────────────────────────────

@app.route('/emergencias')
def emergencias():
    rows = db.fetchall(
        """SELECT e.*, p.nombre + ' ' + p.apellido AS paciente,
                  h.nombre AS hospital_nombre
           FROM frag_emergencia_lpz e
           JOIN frag_paciente_lpz p ON e.id_paciente = p.id_paciente
           JOIN hospital           h ON e.id_hospital  = h.id_hospital
           ORDER BY e.fecha DESC, e.hora DESC"""
    )
    return render_template('emergencias.html', **ctx, emergencias=rows)

@app.route('/emergencia/nueva', methods=['GET', 'POST'])
def nueva_emergencia():
    if request.method == 'POST':
        d = request.form
        db.execute(
            "INSERT INTO frag_emergencia_lpz (fecha, hora, tipo_emergencia, estado_paciente, observaciones, id_paciente, id_hospital) VALUES (?,?,?,?,?,?,?)",
            (d['fecha'], d['hora'], d['tipo_emergencia'], d['estado_paciente'],
             d['observaciones'], d['id_paciente'], config.ID_HOSPITAL)
        )
        flash('Emergencia registrada.', 'success')
        return redirect(url_for('emergencias'))
    pacientes_list = db.fetchall('SELECT id_paciente, nombre, apellido FROM frag_paciente_lpz ORDER BY apellido')
    return render_template('emergencia_form.html', **ctx, pacientes=pacientes_list)

# ── Transferencias ────────────────────────────────────────────────────────────

@app.route('/transferencias')
def transferencias():
    rows = db.fetchall(
        """SELECT t.*, p.nombre + ' ' + p.apellido AS paciente,
                  h1.nombre AS origen, h2.nombre AS destino
           FROM frag_transferencia_lpz t
           JOIN frag_paciente_lpz p  ON t.id_paciente         = p.id_paciente
           JOIN hospital           h1 ON t.id_hospital_origen  = h1.id_hospital
           JOIN hospital           h2 ON t.id_hospital_destino = h2.id_hospital
           ORDER BY t.fecha_transferencia DESC"""
    )
    return render_template('transferencias.html', **ctx, transferencias=rows)

@app.route('/transferencia/nueva', methods=['GET', 'POST'])
def nueva_transferencia():
    if request.method == 'POST':
        d = request.form
        id_transferencia = db.execute(
            "INSERT INTO frag_transferencia_lpz (fecha_transferencia, motivo, estado, id_paciente, id_hospital_origen, id_hospital_destino) VALUES (?,?,'Pendiente',?,?,?)",
            (d['fecha_transferencia'], d['motivo'], d['id_paciente'],
             config.ID_HOSPITAL, d['id_hospital_destino']),
            returning=True
        )
        exito, msg = mediator.transferir_paciente(int(d['id_paciente']), id_transferencia, int(d['id_hospital_destino']))
        flash(msg, 'success' if exito else 'warning')
        return redirect(url_for('transferencias'))
    pacientes_list  = db.fetchall('SELECT id_paciente, nombre, apellido FROM frag_paciente_lpz ORDER BY apellido')
    hospitales_list = db.fetchall('SELECT id_hospital, nombre FROM hospital WHERE id_hospital != ?', (config.ID_HOSPITAL,))
    return render_template('transferencia_form.html', **ctx,
                           pacientes=pacientes_list, hospitales=hospitales_list)

# ── Hospitales / Medicamentos ─────────────────────────────────────────────────

@app.route('/hospitales')
def hospitales():
    return render_template('hospitales.html', **ctx,
                           hospitales=db.fetchall('SELECT * FROM hospital ORDER BY id_hospital'))

@app.route('/medicamentos')
def medicamentos():
    return render_template('medicamentos.html', **ctx,
                           medicamentos=db.fetchall('SELECT * FROM medicamento ORDER BY nombre'))

@app.route('/medicamento/nuevo', methods=['POST'])
def nuevo_medicamento():
    d = request.form
    db.execute('INSERT INTO medicamento (nombre, descripcion, dosis, fabricante) VALUES (?,?,?,?)',
               (d['nombre'], d['descripcion'], d['dosis'], d['fabricante']))
    mediator.replicar_catalogo_a_remotos(d['nombre'], d['descripcion'], d['dosis'], d['fabricante'])
    flash('Medicamento agregado y replicado en CBBA y STCZ.', 'success')
    return redirect(url_for('medicamentos'))

# ── Búsqueda Nacional ─────────────────────────────────────────────────────────

@app.route('/buscar_nacional')
def buscar_nacional():
    q = request.args.get('q', '').strip()
    resultados, errores = [], {}
    if q:
        resultados, errores = mediator.buscar_paciente_global(q)
    return render_template('busqueda_nacional.html', **ctx,
                           resultados=resultados, errores=errores, q=q)

@app.route('/emergencia_cruzada/<int:id_paciente>')
def emergencia_cruzada(id_paciente):
    h, fuente = mediator.obtener_historial_critico(id_paciente)
    p, nodo   = mediator.obtener_paciente_por_id(id_paciente)
    ctx_no_nodo = {k: v for k, v in ctx.items() if k != 'nodo'}
    return render_template('emergencia_cruzada.html', **ctx_no_nodo,
                           historial=h, paciente=p, fuente=fuente, nodo=nodo)

# ── Recolección de datos  (reconstrucción UNION ALL de los 3 fragmentos) ──────
# Optimización: 1 conexión por nodo remoto + los 3 nodos en paralelo.
# Antes: 12+ conexiones secuenciales (~20-30s). Ahora: ~3-6s.

def _fetch_lpz_datos():
    return {
        'pacientes'     : db.fetchall('SELECT * FROM frag_paciente_lpz ORDER BY id_paciente'),
        'doctores'      : db.fetchall('SELECT * FROM frag_doctor_lpz ORDER BY apellido'),
        'consultas'     : db.fetchall('SELECT * FROM frag_consulta_lpz ORDER BY fecha DESC'),
        'emergencias'   : db.fetchall('SELECT * FROM frag_emergencia_lpz ORDER BY fecha DESC'),
        'transferencias': db.fetchall('SELECT * FROM frag_transferencia_lpz ORDER BY fecha_transferencia DESC'),
        'historial_v1'  : db.fetchall('SELECT * FROM historial_clinico_v1'),
    }

def _fetch_cbba_datos():
    # Una sola conexion PostgreSQL para todas las queries CBBA
    return db.remote_fetchall_batch('CBBA', [
        ('pacientes',      'SELECT * FROM frag_paciente_cbba ORDER BY id_paciente', []),
        ('doctores',       'SELECT * FROM frag_doctor_cbba ORDER BY apellido', []),
        ('consultas',      'SELECT * FROM frag_consulta_cbba ORDER BY fecha DESC', []),
        ('emergencias',    'SELECT * FROM frag_emergencia_cbba ORDER BY fecha DESC', []),
        ('transferencias', 'SELECT * FROM frag_transferencia_cbba ORDER BY fecha_transferencia DESC', []),
        ('historial_v1',   'SELECT * FROM historial_clinico_v1', []),
    ])

def _fetch_stcz_datos():
    # Una sola conexion SQL Server para todas las queries STCZ
    return db.remote_fetchall_batch('STCZ', [
        ('pacientes',      'SELECT * FROM frag_paciente_stcz ORDER BY id_paciente', []),
        ('doctores',       'SELECT * FROM frag_doctor_stcz ORDER BY apellido', []),
        ('consultas',      'SELECT * FROM frag_consulta_stcz ORDER BY fecha DESC', []),
        ('emergencias',    'SELECT * FROM frag_emergencia_stcz ORDER BY fecha DESC', []),
        ('transferencias', 'SELECT * FROM frag_transferencia_stcz ORDER BY fecha_transferencia DESC', []),
        ('historial_v1',   'SELECT * FROM historial_clinico_v1', []),
    ])

@app.route('/recoleccion_datos')
def recoleccion_datos():
    datos, errores = {}, {}

    # Los 3 nodos se consultan en PARALELO (ThreadPoolExecutor)
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_lpz  = ex.submit(_fetch_lpz_datos)
        f_cbba = ex.submit(_fetch_cbba_datos)
        f_stcz = ex.submit(_fetch_stcz_datos)

        # LPZ local — no retorna (errr, data) tuple
        try:
            datos['lpz'] = f_lpz.result(timeout=8)
        except FutureTimeout:
            errores['LPZ'] = 'Timeout al consultar base local LPZ.'; datos['lpz'] = {}
        except Exception as e:
            errores['LPZ'] = str(e); datos['lpz'] = {}

        # CBBA remoto — retorna (dict, error)
        try:
            d_cbba, e_cbba = f_cbba.result(timeout=8)
            datos['cbba'] = d_cbba
            if e_cbba: errores['CBBA'] = e_cbba
        except FutureTimeout:
            errores['CBBA'] = 'Timeout: CBBA no respondio en 8s.'; datos['cbba'] = {}
        except Exception as e:
            errores['CBBA'] = str(e); datos['cbba'] = {}

        # STCZ remoto — retorna (dict, error)
        try:
            d_stcz, e_stcz = f_stcz.result(timeout=8)
            datos['stcz'] = d_stcz
            if e_stcz: errores['STCZ'] = e_stcz
        except FutureTimeout:
            errores['STCZ'] = 'Timeout: STCZ no respondio en 8s.'; datos['stcz'] = {}
        except Exception as e:
            errores['STCZ'] = str(e); datos['stcz'] = {}

    return render_template('recoleccion_datos.html', **ctx, datos=datos, errores=errores)

# ── API REST ──────────────────────────────────────────────────────────────────

@app.route('/api/paciente/<int:id_paciente>')
def api_paciente(id_paciente):
    p, nodo = mediator.obtener_paciente_por_id(id_paciente)
    if p:
        return jsonify({'success': True, 'data': p, 'nodo': nodo})
    return jsonify({'success': False, 'error': 'Paciente no encontrado'}), 404

@app.route('/api/transferir', methods=['POST'])
def api_transferir_lpz():
    """Recibe paciente transferido desde CBBA o STCZ → LPZ."""
    d = request.get_json()
    try:
        db.execute_batch(
            "SET IDENTITY_INSERT frag_paciente_lpz ON; "
            "INSERT INTO frag_paciente_lpz (id_paciente, nombre, apellido, ci, fecha_nacimiento, sexo, "
            "direccion, telefono, tipo_sangre, alergias, id_hospital) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?); "
            "SET IDENTITY_INSERT frag_paciente_lpz OFF;",
            (d['id_paciente'], d['nombre'], d['apellido'], d['ci'],
             d['fecha_nacimiento'], d['sexo'], d['direccion'], d['telefono'],
             d['tipo_sangre'], d['alergias'], config.ID_HOSPITAL)
        )
        db.execute(
            "INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas) VALUES (?,?,?,?)",
            (d['id_paciente'], d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'])
        )
        hid = db.fetchone('SELECT id_historial FROM historial_clinico_v1 WHERE id_paciente = ?', (d['id_paciente'],))
        if hid:
            db.execute(
                "INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones) VALUES (?,?,CAST(GETDATE() AS DATE),?,?)",
                (hid['id_historial'], d['id_paciente'], d.get('antecedentes', ''), d.get('observaciones', ''))
            )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    mediator.registrar_en_catalogo(d['id_paciente'], 'LPZ', config.ID_HOSPITAL)
    return jsonify({'success': True, 'nodo': 'LPZ'})

@app.route('/api/buscar')
def api_buscar():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'success': False, 'error': 'Termino vacio'}), 400
    resultados, errores = mediator.buscar_paciente_global(q)
    return jsonify({'success': True, 'data': resultados, 'errores': errores})

@app.route('/api/historial_critico/<int:id_paciente>')
def api_historial_critico(id_paciente):
    h, fuente = mediator.obtener_historial_critico(id_paciente)
    if h:
        return jsonify({'success': True, 'data': h, 'fuente': fuente})
    return jsonify({'success': False, 'error': 'Historial no disponible'}), 404

@app.route('/api/transferir_desde', methods=['POST'])
def api_transferir_desde():
    d = request.get_json()
    exito, msg = mediator.transferir_paciente_desde_remoto(
        d['nodo_origen'], int(d['id_paciente']),
        int(d['id_transferencia']), int(d['id_hospital_destino'])
    )
    if exito:
        return jsonify({'success': True, 'msg': msg})
    return jsonify({'success': False, 'error': msg}), 500

@app.route('/api/replica', methods=['POST'])
def api_replica():
    d = request.get_json()
    db.execute(
        """IF EXISTS (SELECT 1 FROM historial_replica WHERE id_paciente=? AND hospital_origen=?)
               UPDATE historial_replica
               SET tipo_sangre=?, alergias=?, enfermedades_cronicas=?, fecha_actualizacion=GETDATE()
               WHERE id_paciente=? AND hospital_origen=?
           ELSE
               INSERT INTO historial_replica (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas)
               VALUES (?,?,?,?,?)""",
        (d['id_paciente'], d['hospital_origen'],
         d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'],
         d['id_paciente'], d['hospital_origen'],
         d['id_paciente'], d['hospital_origen'], d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'])
    )
    mediator.registrar_en_catalogo(d['id_paciente'], d['hospital_origen'], d.get('id_hospital', 0))
    return jsonify({'success': True})

@app.route('/api/catalogo/registro', methods=['POST'])
def api_catalogo_registro():
    d = request.get_json()
    mediator.registrar_en_catalogo(d['id_paciente'], d['nodo'], d['id_hospital'])
    return jsonify({'success': True})

@app.route('/api/estado_nodos')
def api_estado_nodos():
    import requests as req
    nodos = {}
    for key, url, nombre in [('cbba', config.CBBA_URL, 'Cochabamba (CBBA)'),
                               ('stcz', config.STCZ_URL, 'Santa Cruz (STCZ)')]:
        try:
            r = req.get(url + '/api/health', timeout=2)
            nodos[key] = {'nombre': nombre, 'conectado': r.status_code == 200}
        except Exception:
            nodos[key] = {'nombre': nombre, 'conectado': False}
    return jsonify(nodos)

@app.route('/api/health')
def api_health():
    return jsonify({'nodo': 'LPZ', 'estado': 'activo', 'rol': 'mediador',
                    'timestamp': datetime.now().isoformat()})

@app.route('/logs')
def logs():
    rows = db.fetchall('SELECT TOP 100 * FROM distributed_logs ORDER BY timestamp DESC')
    return render_template('logs.html', **ctx, logs=rows)

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=True)
