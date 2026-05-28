from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import date, datetime
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
        'pacientes'  : db.fetchone('SELECT COUNT(*) AS n FROM paciente')['n'],
        'consultas'  : db.fetchone('SELECT COUNT(*) AS n FROM consulta')['n'],
        'emergencias': db.fetchone('SELECT COUNT(*) AS n FROM emergencia')['n'],
        'doctores'   : db.fetchone('SELECT COUNT(*) AS n FROM doctor')['n'],
        'replicas'   : db.fetchone('SELECT COUNT(*) AS n FROM historial_replica')['n'],
        'logs'       : db.fetchone('SELECT COUNT(*) AS n FROM distributed_logs')['n'],
    }
    return render_template('index.html', **ctx, stats=stats)


# ── Pacientes ─────────────────────────────────────────────────────────────────

@app.route('/pacientes')
def pacientes():
    rows = db.fetchall('SELECT * FROM paciente ORDER BY apellido, nombre')
    return render_template('pacientes.html', **ctx, pacientes=rows)


@app.route('/paciente/nuevo', methods=['GET', 'POST'])
def nuevo_paciente():
    if request.method == 'POST':
        d = request.form
        pid = db.execute(
            """INSERT INTO paciente (nombre, apellido, ci, fecha_nacimiento, sexo,
               direccion, telefono, tipo_sangre, alergias, id_hospital)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id_paciente""",
            (d['nombre'], d['apellido'], d['ci'], d['fecha_nacimiento'],
             d['sexo'], d['direccion'], d['telefono'], d['tipo_sangre'],
             d['alergias'], config.ID_HOSPITAL),
            returning=True
        )
        db.execute(
            """INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas)
               VALUES (%s,%s,%s,%s)""",
            (pid, d['tipo_sangre'], d['alergias'], d.get('enfermedades_cronicas', ''))
        )
        db.execute(
            """INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones)
               SELECT id_historial, id_paciente, %s, %s, %s
               FROM historial_clinico_v1 WHERE id_paciente = %s""",
            (date.today(), d.get('antecedentes', ''), '', pid)
        )
        mediator.registrar_en_catalogo(pid, 'LPZ', config.ID_HOSPITAL)
        mediator.replicar_critico_a_remotos(
            pid, 'LPZ', d['tipo_sangre'], d['alergias'], d.get('enfermedades_cronicas', '')
        )
        flash('Paciente registrado y datos criticos replicados a CBBA y STCZ.', 'success')
        return redirect(url_for('paciente_detalle', id_paciente=pid))
    return render_template('paciente_form.html', **ctx)


@app.route('/paciente/<int:id_paciente>')
def paciente_detalle(id_paciente):
    p = db.fetchone('SELECT * FROM paciente WHERE id_paciente = %s', (id_paciente,))
    if not p:
        flash('Paciente no encontrado.', 'danger')
        return redirect(url_for('pacientes'))
    hist_v1 = db.fetchone('SELECT * FROM historial_clinico_v1 WHERE id_paciente = %s', (id_paciente,))
    hist_v2 = db.fetchone('SELECT * FROM historial_clinico_v2 WHERE id_paciente = %s', (id_paciente,))
    consultas = db.fetchall(
        """SELECT c.*, d.nombre || ' ' || d.apellido AS medico
           FROM consulta c JOIN doctor d ON c.id_doctor = d.id_doctor
           WHERE c.id_paciente = %s ORDER BY c.fecha DESC""",
        (id_paciente,)
    )
    emergencias = db.fetchall(
        'SELECT * FROM emergencia WHERE id_paciente = %s ORDER BY fecha DESC', (id_paciente,)
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
        """UPDATE historial_clinico_v1
           SET tipo_sangre=%s, alergias=%s, enfermedades_cronicas=%s
           WHERE id_paciente=%s""",
        (d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'], pid)
    )
    db.execute(
        """UPDATE historial_clinico_v2
           SET antecedentes=%s, observaciones=%s WHERE id_paciente=%s""",
        (d['antecedentes'], d['observaciones'], pid)
    )
    mediator.replicar_critico_a_remotos(
        pid, 'LPZ', d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas']
    )
    flash('Historial actualizado y replica sincronizada.', 'success')
    return redirect(url_for('paciente_detalle', id_paciente=pid))


# ── Consultas ─────────────────────────────────────────────────────────────────

@app.route('/consultas')
def consultas():
    rows = db.fetchall(
        """SELECT c.*, p.nombre || ' ' || p.apellido AS paciente,
                  d.nombre || ' ' || d.apellido AS medico
           FROM consulta c
           JOIN paciente p ON c.id_paciente = p.id_paciente
           JOIN doctor   d ON c.id_doctor   = d.id_doctor
           ORDER BY c.fecha DESC, c.hora DESC"""
    )
    return render_template('consultas.html', **ctx, consultas=rows)


@app.route('/consulta/nueva', methods=['GET', 'POST'])
def nueva_consulta():
    if request.method == 'POST':
        d = request.form
        db.execute(
            """INSERT INTO consulta (fecha, hora, motivo, diagnostico, id_paciente, id_doctor, id_hospital)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (d['fecha'], d['hora'], d['motivo'], d['diagnostico'],
             d['id_paciente'], d['id_doctor'], config.ID_HOSPITAL)
        )
        flash('Consulta registrada correctamente.', 'success')
        return redirect(url_for('consultas'))
    pacientes_list = db.fetchall('SELECT id_paciente, nombre, apellido FROM paciente ORDER BY apellido')
    doctores_list  = db.fetchall('SELECT id_doctor, nombre, apellido, especialidad FROM doctor ORDER BY apellido')
    return render_template('consulta_form.html', **ctx,
                           pacientes=pacientes_list, doctores=doctores_list)


# ── Emergencias ───────────────────────────────────────────────────────────────

@app.route('/emergencias')
def emergencias():
    rows = db.fetchall(
        """SELECT e.*, p.nombre || ' ' || p.apellido AS paciente,
                  h.nombre AS hospital_nombre
           FROM emergencia e
           JOIN paciente p ON e.id_paciente = p.id_paciente
           JOIN hospital  h ON e.id_hospital  = h.id_hospital
           ORDER BY e.fecha DESC, e.hora DESC"""
    )
    return render_template('emergencias.html', **ctx, emergencias=rows)


@app.route('/emergencia/nueva', methods=['GET', 'POST'])
def nueva_emergencia():
    if request.method == 'POST':
        d = request.form
        db.execute(
            """INSERT INTO emergencia (fecha, hora, tipo_emergencia, estado_paciente, observaciones, id_paciente, id_hospital)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (d['fecha'], d['hora'], d['tipo_emergencia'], d['estado_paciente'],
             d['observaciones'], d['id_paciente'], config.ID_HOSPITAL)
        )
        flash('Emergencia registrada.', 'success')
        return redirect(url_for('emergencias'))
    pacientes_list = db.fetchall('SELECT id_paciente, nombre, apellido FROM paciente ORDER BY apellido')
    return render_template('emergencia_form.html', **ctx, pacientes=pacientes_list)


# ── Transferencias ────────────────────────────────────────────────────────────

@app.route('/transferencias')
def transferencias():
    rows = db.fetchall(
        """SELECT t.*, p.nombre || ' ' || p.apellido AS paciente,
                  h1.nombre AS origen, h2.nombre AS destino
           FROM transferencias_hospitalarias t
           JOIN paciente p  ON t.id_paciente         = p.id_paciente
           JOIN hospital h1 ON t.id_hospital_origen  = h1.id_hospital
           JOIN hospital h2 ON t.id_hospital_destino = h2.id_hospital
           ORDER BY t.fecha_transferencia DESC"""
    )
    return render_template('transferencias.html', **ctx, transferencias=rows)


@app.route('/transferencia/nueva', methods=['GET', 'POST'])
def nueva_transferencia():
    if request.method == 'POST':
        d = request.form
        db.execute(
            """INSERT INTO transferencias_hospitalarias
               (fecha_transferencia, motivo, estado, id_paciente, id_hospital_origen, id_hospital_destino)
               VALUES (%s,%s,'Pendiente',%s,%s,%s)""",
            (d['fecha_transferencia'], d['motivo'], d['id_paciente'],
             config.ID_HOSPITAL, d['id_hospital_destino'])
        )
        flash('Transferencia registrada.', 'success')
        return redirect(url_for('transferencias'))
    pacientes_list = db.fetchall('SELECT id_paciente, nombre, apellido FROM paciente ORDER BY apellido')
    hospitales_list = db.fetchall(
        'SELECT id_hospital, nombre FROM hospital WHERE id_hospital != %s', (config.ID_HOSPITAL,)
    )
    return render_template('transferencia_form.html', **ctx,
                           pacientes=pacientes_list, hospitales=hospitales_list)


# ── Hospitales (catálogo de la red) ───────────────────────────────────────────

@app.route('/hospitales')
def hospitales():
    rows = db.fetchall('SELECT * FROM hospital ORDER BY id_hospital')
    return render_template('hospitales.html', **ctx, hospitales=rows)


# ── Medicamentos ──────────────────────────────────────────────────────────────

@app.route('/medicamentos')
def medicamentos():
    rows = db.fetchall('SELECT * FROM medicamento ORDER BY nombre')
    return render_template('medicamentos.html', **ctx, medicamentos=rows)


@app.route('/medicamento/nuevo', methods=['POST'])
def nuevo_medicamento():
    d = request.form
    db.execute(
        'INSERT INTO medicamento (nombre, descripcion, dosis, fabricante) VALUES (%s,%s,%s,%s)',
        (d['nombre'], d['descripcion'], d['dosis'], d['fabricante'])
    )
    mediator.replicar_catalogo_a_remotos(d['nombre'], d['descripcion'], d['dosis'], d['fabricante'])
    flash('Medicamento agregado y replicado en CBBA y STCZ.', 'success')
    return redirect(url_for('medicamentos'))


# ── Busqueda Nacional (funcion mediadora) ─────────────────────────────────────

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
    """Obtiene datos criticos de un paciente de cualquier nodo para emergencias."""
    h, fuente = mediator.obtener_historial_critico(id_paciente)
    p, nodo   = mediator.obtener_paciente_por_id(id_paciente)
    return render_template('emergencia_cruzada.html', **ctx,
                           historial=h, paciente=p, fuente=fuente, nodo=nodo)


# ── API endpoints (para que CBBA y STCZ consulten al mediador) ───────────────

@app.route('/api/paciente/<int:id_paciente>')
def api_paciente(id_paciente):
    p, nodo = mediator.obtener_paciente_por_id(id_paciente)
    if p:
        return jsonify({'success': True, 'data': p, 'nodo': nodo})
    return jsonify({'success': False, 'error': 'Paciente no encontrado'}), 404


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


@app.route('/api/replica', methods=['POST'])
def api_replica():
    """Recibe una replica critica enviada por CBBA o STCZ."""
    d = request.get_json()
    db.execute(
        """INSERT INTO historial_replica
           (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas)
           VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (id_paciente, hospital_origen) DO UPDATE
           SET tipo_sangre=EXCLUDED.tipo_sangre,
               alergias=EXCLUDED.alergias,
               enfermedades_cronicas=EXCLUDED.enfermedades_cronicas,
               fecha_actualizacion=NOW()""",
        (d['id_paciente'], d['hospital_origen'], d['tipo_sangre'],
         d['alergias'], d['enfermedades_cronicas'])
    )
    mediator.registrar_en_catalogo(d['id_paciente'], d['hospital_origen'],
                                   d.get('id_hospital', 0))
    return jsonify({'success': True})


@app.route('/api/catalogo/registro', methods=['POST'])
def api_catalogo_registro():
    """Registra un nuevo paciente en el catalogo de fragmentacion."""
    d = request.get_json()
    mediator.registrar_en_catalogo(d['id_paciente'], d['nodo'], d['id_hospital'])
    return jsonify({'success': True})


@app.route('/api/estado_nodos')
def api_estado_nodos():
    import requests as req
    nodos = {}
    for key, url, nombre in [
        ('cbba', config.CBBA_URL, 'Cochabamba (CBBA)'),
        ('stcz', config.STCZ_URL, 'Santa Cruz (STCZ)'),
    ]:
        try:
            r = req.get(url + '/api/health', timeout=2)
            nodos[key] = {'nombre': nombre, 'conectado': r.status_code == 200}
        except Exception:
            nodos[key] = {'nombre': nombre, 'conectado': False}
    return jsonify(nodos)


@app.route('/api/health')
def api_health():
    return jsonify({
        'nodo'     : 'LPZ',
        'estado'   : 'activo',
        'rol'      : 'mediador',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/logs')
def logs():
    rows = db.fetchall('SELECT * FROM distributed_logs ORDER BY timestamp DESC LIMIT 100')
    return render_template('logs.html', **ctx, logs=rows)


if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=True)
