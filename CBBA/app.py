from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import db, config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

ctx = {
    'hospital': config.HOSPITAL_NOMBRE,
    'nodo'    : config.NODO,
    'color_p' : config.COLOR_PRIMARY,
    'color_s' : config.COLOR_SECONDARY,
    'color_bg': config.COLOR_BG,
}


def _notificar_lpz_replica(id_paciente, tipo_sangre, alergias, enfermedades_cronicas):
    db.lpz_post('/api/replica', {
        'id_paciente': id_paciente, 'hospital_origen': 'CBBA',
        'id_hospital': config.ID_HOSPITAL, 'tipo_sangre': tipo_sangre,
        'alergias': alergias, 'enfermedades_cronicas': enfermedades_cronicas
    })

def _registrar_en_catalogo_lpz(id_paciente):
    db.lpz_post('/api/catalogo/registro', {
        'id_paciente': id_paciente, 'nodo': 'CBBA', 'id_hospital': config.ID_HOSPITAL
    })


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    stats = {
        'pacientes'  : (db.fetchone('SELECT COUNT(*) AS n FROM frag_paciente_cbba')  or {}).get('n', 0),
        'consultas'  : (db.fetchone('SELECT COUNT(*) AS n FROM frag_consulta_cbba')  or {}).get('n', 0),
        'emergencias': (db.fetchone('SELECT COUNT(*) AS n FROM frag_emergencia_cbba') or {}).get('n', 0),
        'doctores'   : (db.fetchone('SELECT COUNT(*) AS n FROM frag_doctor_cbba')    or {}).get('n', 0),
        'replicas'   : (db.fetchone('SELECT COUNT(*) AS n FROM historial_replica')   or {}).get('n', 0),
    }
    return render_template('index.html', **ctx, stats=stats)

# ── Pacientes ─────────────────────────────────────────────────────────────────

@app.route('/pacientes')
def pacientes():
    rows = db.fetchall('SELECT * FROM frag_paciente_cbba ORDER BY apellido, nombre')
    return render_template('pacientes.html', **ctx, pacientes=rows)

@app.route('/paciente/nuevo', methods=['GET', 'POST'])
def nuevo_paciente():
    if request.method == 'POST':
        d = request.form
        pid = db.execute(
            """INSERT INTO frag_paciente_cbba
               (nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id_paciente""",
            (d['nombre'], d['apellido'], d['ci'], d['fecha_nacimiento'],
             d['sexo'], d['direccion'], d['telefono'], d['tipo_sangre'],
             d['alergias'], config.ID_HOSPITAL),
            returning=True
        )
        db.execute(
            'INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas) VALUES (%s,%s,%s,%s)',
            (pid, d['tipo_sangre'], d['alergias'], d.get('enfermedades_cronicas', ''))
        )
        hid = db.fetchone('SELECT id_historial FROM historial_clinico_v1 WHERE id_paciente = %s', (pid,))
        if hid:
            db.execute(
                'INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones) VALUES (%s,%s,CURRENT_DATE,%s,%s)',
                (hid['id_historial'], pid, d.get('antecedentes', ''), '')
            )
        _registrar_en_catalogo_lpz(pid)
        _notificar_lpz_replica(pid, d['tipo_sangre'], d['alergias'], d.get('enfermedades_cronicas', ''))
        flash('Paciente registrado. Datos criticos enviados al mediador LPZ.', 'success')
        return redirect(url_for('paciente_detalle', id_paciente=pid))
    return render_template('paciente_form.html', **ctx)

@app.route('/paciente/<int:id_paciente>')
def paciente_detalle(id_paciente):
    p = db.fetchone('SELECT * FROM frag_paciente_cbba WHERE id_paciente = %s', (id_paciente,))
    if not p:
        flash('Paciente no encontrado en este nodo.', 'warning')
        return redirect(url_for('pacientes'))
    hist_v1   = db.fetchone('SELECT * FROM historial_clinico_v1 WHERE id_paciente = %s', (id_paciente,))
    hist_v2   = db.fetchone('SELECT * FROM historial_clinico_v2 WHERE id_paciente = %s', (id_paciente,))
    consultas = db.fetchall(
        "SELECT c.*, d.nombre || ' ' || d.apellido AS medico FROM frag_consulta_cbba c JOIN frag_doctor_cbba d ON c.id_doctor = d.id_doctor WHERE c.id_paciente = %s ORDER BY c.fecha DESC",
        (id_paciente,)
    )
    emergencias = db.fetchall(
        'SELECT * FROM frag_emergencia_cbba WHERE id_paciente = %s ORDER BY fecha DESC',
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
    db.execute('UPDATE historial_clinico_v1 SET tipo_sangre=%s, alergias=%s, enfermedades_cronicas=%s WHERE id_paciente=%s',
               (d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'], pid))
    db.execute('UPDATE historial_clinico_v2 SET antecedentes=%s, observaciones=%s WHERE id_paciente=%s',
               (d['antecedentes'], d['observaciones'], pid))
    _notificar_lpz_replica(pid, d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'])
    flash('Historial actualizado y replica enviada a LPZ.', 'success')
    return redirect(url_for('paciente_detalle', id_paciente=pid))

# ── Consultas ─────────────────────────────────────────────────────────────────

@app.route('/consultas')
def consultas():
    rows = db.fetchall(
        """SELECT c.*, p.nombre || ' ' || p.apellido AS paciente,
                  d.nombre || ' ' || d.apellido AS medico
           FROM frag_consulta_cbba c
           JOIN frag_paciente_cbba p ON c.id_paciente = p.id_paciente
           JOIN frag_doctor_cbba   d ON c.id_doctor   = d.id_doctor
           ORDER BY c.fecha DESC"""
    )
    return render_template('consultas.html', **ctx, consultas=rows)

@app.route('/consulta/nueva', methods=['GET', 'POST'])
def nueva_consulta():
    if request.method == 'POST':
        d = request.form
        db.execute(
            'INSERT INTO frag_consulta_cbba (fecha, hora, motivo, diagnostico, id_paciente, id_doctor, id_hospital) VALUES (%s,%s,%s,%s,%s,%s,%s)',
            (d['fecha'], d['hora'], d['motivo'], d['diagnostico'], d['id_paciente'], d['id_doctor'], config.ID_HOSPITAL)
        )
        flash('Consulta registrada.', 'success')
        return redirect(url_for('consultas'))
    pacientes_list = db.fetchall('SELECT id_paciente, nombre, apellido FROM frag_paciente_cbba ORDER BY apellido')
    doctores_list  = db.fetchall('SELECT id_doctor, nombre, apellido, especialidad FROM frag_doctor_cbba ORDER BY apellido')
    return render_template('consulta_form.html', **ctx, pacientes=pacientes_list, doctores=doctores_list)

# ── Emergencias ───────────────────────────────────────────────────────────────

@app.route('/emergencias')
def emergencias():
    rows = db.fetchall(
        "SELECT e.*, p.nombre || ' ' || p.apellido AS paciente FROM frag_emergencia_cbba e JOIN frag_paciente_cbba p ON e.id_paciente = p.id_paciente ORDER BY e.fecha DESC"
    )
    return render_template('emergencias.html', **ctx, emergencias=rows)

@app.route('/emergencia/nueva', methods=['GET', 'POST'])
def nueva_emergencia():
    if request.method == 'POST':
        d = request.form
        db.execute(
            'INSERT INTO frag_emergencia_cbba (fecha, hora, tipo_emergencia, estado_paciente, observaciones, id_paciente, id_hospital) VALUES (%s,%s,%s,%s,%s,%s,%s)',
            (d['fecha'], d['hora'], d['tipo_emergencia'], d['estado_paciente'], d['observaciones'], d['id_paciente'], config.ID_HOSPITAL)
        )
        flash('Emergencia registrada.', 'success')
        return redirect(url_for('emergencias'))
    pacientes_list = db.fetchall('SELECT id_paciente, nombre, apellido FROM frag_paciente_cbba ORDER BY apellido')
    return render_template('emergencia_form.html', **ctx, pacientes=pacientes_list)

# ── Transferencias ────────────────────────────────────────────────────────────

@app.route('/transferencias')
def transferencias():
    rows = db.fetchall(
        """SELECT t.*, p.nombre || ' ' || p.apellido AS paciente,
                  h1.nombre AS origen, h2.nombre AS destino
           FROM frag_transferencia_cbba t
           JOIN frag_paciente_cbba p ON t.id_paciente         = p.id_paciente
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
            "INSERT INTO frag_transferencia_cbba (fecha_transferencia, motivo, estado, id_paciente, id_hospital_origen, id_hospital_destino) VALUES (%s,%s,'Pendiente',%s,%s,%s) RETURNING id_transferencia",
            (d['fecha_transferencia'], d['motivo'], d['id_paciente'], config.ID_HOSPITAL, d['id_hospital_destino']),
            returning=True
        )
        if id_transferencia is None:
            flash('Error al registrar transferencia local.', 'danger')
            return redirect(url_for('transferencias'))
        data, err = db.lpz_post('/api/transferir_desde', {
            'nodo_origen': 'CBBA', 'id_paciente': int(d['id_paciente']),
            'id_transferencia': int(id_transferencia), 'id_hospital_destino': int(d['id_hospital_destino']),
        })
        if data and data.get('success'):
            flash(data['msg'], 'success')
        else:
            flash(f'Transferencia registrada, pero {(data or {}).get("error", str(err))}', 'warning')
        return redirect(url_for('transferencias'))
    pacientes_list  = db.fetchall('SELECT id_paciente, nombre, apellido FROM frag_paciente_cbba ORDER BY apellido')
    hospitales_list = db.fetchall('SELECT id_hospital, nombre FROM hospital WHERE id_hospital != %s', (config.ID_HOSPITAL,))
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

# ── Búsqueda Nacional ─────────────────────────────────────────────────────────

@app.route('/buscar_nacional')
def buscar_nacional():
    q = request.args.get('q', '').strip()
    resultados, error, metodo = [], None, None
    if q:
        rows_ls, err_ls = db.openquery_lpz(
            f"SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'LPZ' AS nodo "
            f"FROM frag_paciente_lpz WHERE ci = '{q}' OR (nombre + ' ' + apellido) LIKE '%{q}%'"
        )
        if not err_ls:
            resultados, metodo = rows_ls, 'DirectSQL'
        else:
            data, err_http = db.lpz_get('/api/buscar', {'q': q})
            if data and data.get('success'):
                resultados, metodo = data['data'], 'HTTP_API'
            else:
                error = f'DirectSQL: {err_ls} | HTTP: {err_http}'
    return render_template('busqueda_nacional.html', **ctx,
                           resultados=resultados, error=error, q=q, metodo=metodo)

@app.route('/emergencia_cruzada/<int:id_paciente>')
def emergencia_cruzada(id_paciente):
    replica = db.fetchone('SELECT * FROM historial_replica WHERE id_paciente = %s', (id_paciente,))
    h, fuente = replica, ('replica_local' if replica else None)
    if not h:
        data, _ = db.lpz_get(f'/api/historial_critico/{id_paciente}')
        if data and data.get('success'):
            h, fuente = data['data'], 'LPZ_remoto'
    return render_template('emergencia_cruzada.html', **ctx,
                           historial=h, fuente=fuente, id_paciente=id_paciente)

# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route('/api/transferir', methods=['POST'])
def api_transferir():
    """Recibe paciente transferido hacia CBBA."""
    d = request.get_json()
    try:
        db.execute(
            "INSERT INTO frag_paciente_cbba (id_paciente, nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (d['id_paciente'], d['nombre'], d['apellido'], d['ci'], d['fecha_nacimiento'],
             d['sexo'], d['direccion'], d['telefono'], d['tipo_sangre'], d['alergias'], config.ID_HOSPITAL)
        )
        db.execute(
            "INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas) VALUES (%s,%s,%s,%s)",
            (d['id_paciente'], d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'])
        )
        hid = db.fetchone('SELECT id_historial FROM historial_clinico_v1 WHERE id_paciente = %s', (d['id_paciente'],))
        if hid:
            db.execute(
                "INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones) VALUES (%s,%s,CURRENT_DATE,%s,%s)",
                (hid['id_historial'], d['id_paciente'], d.get('antecedentes', ''), d.get('observaciones', ''))
            )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    _notificar_lpz_replica(d['id_paciente'], d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'])
    _registrar_en_catalogo_lpz(d['id_paciente'])
    return jsonify({'success': True, 'nodo': 'CBBA'})

@app.route('/api/paciente/<int:id_paciente>')
def api_paciente(id_paciente):
    p = db.fetchone('SELECT * FROM frag_paciente_cbba WHERE id_paciente = %s', (id_paciente,))
    if p: return jsonify({'success': True, 'data': p, 'nodo': 'CBBA'})
    return jsonify({'success': False, 'error': 'No encontrado'}), 404

@app.route('/api/replica', methods=['POST'])
def api_replica():
    d = request.get_json()
    existing = db.fetchone('SELECT id_replica FROM historial_replica WHERE id_paciente=%s AND hospital_origen=%s',
                           (d['id_paciente'], d['hospital_origen']))
    if existing:
        db.execute('UPDATE historial_replica SET tipo_sangre=%s, alergias=%s, enfermedades_cronicas=%s, fecha_actualizacion=NOW() WHERE id_paciente=%s AND hospital_origen=%s',
                   (d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas'], d['id_paciente'], d['hospital_origen']))
    else:
        db.execute('INSERT INTO historial_replica (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas) VALUES (%s,%s,%s,%s,%s)',
                   (d['id_paciente'], d['hospital_origen'], d['tipo_sangre'], d['alergias'], d['enfermedades_cronicas']))
    return jsonify({'success': True})

@app.route('/api/estado_nodos')
def api_estado_nodos():
    import requests as req
    nodos = {}
    for key, url, nombre in [('lpz', config.LPZ_URL, 'La Paz (LPZ)'), ('stcz', config.STCZ_URL, 'Santa Cruz (STCZ)')]:
        try:
            r = req.get(url + '/api/health', timeout=2)
            nodos[key] = {'nombre': nombre, 'conectado': r.status_code == 200}
        except Exception:
            nodos[key] = {'nombre': nombre, 'conectado': False}
    return jsonify(nodos)

@app.route('/api/health')
def api_health():
    return jsonify({'nodo': 'CBBA', 'estado': 'activo', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=True)
