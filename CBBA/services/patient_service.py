from config import LOCAL_HOSPITAL
from db import execute_query, check_connection


def get_local_patient(patient_id):
    row = execute_query(
        "SELECT id_paciente, nombre, tipo_sangre, alergias, enfermedades_cronicas, id_hospital "
        "FROM paciente WHERE id_paciente = ?",
        (patient_id,),
        fetchone=True
    )
    if row is None:
        return None
    return {
        "id_paciente": row[0],
        "nombre": row[1],
        "tipo_sangre": row[2],
        "alergias": row[3],
        "enfermedades_cronicas": row[4],
        "id_hospital": row[5],
        "hospital_origen": LOCAL_HOSPITAL
    }


def get_all_local_patients():
    rows = execute_query(
        "SELECT id_paciente, nombre, tipo_sangre, alergias, enfermedades_cronicas, id_hospital "
        "FROM paciente ORDER BY id_paciente",
        fetchall=True
    )
    return [
        {
            "id_paciente": r[0],
            "nombre": r[1],
            "tipo_sangre": r[2],
            "alergias": r[3],
            "enfermedades_cronicas": r[4],
            "id_hospital": r[5],
            "hospital_origen": LOCAL_HOSPITAL
        }
        for r in rows
    ]


def create_local_patient(data):
    execute_query(
        "INSERT INTO paciente (nombre, tipo_sangre, alergias, enfermedades_cronicas, id_hospital) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            data["nombre"],
            data.get("tipo_sangre"),
            data.get("alergias"),
            data.get("enfermedades_cronicas"),
            data.get("id_hospital", 2)
        )
    )
    row = execute_query(
        "SELECT MAX(id_paciente) FROM paciente",
        fetchone=True
    )
    new_id = row[0]
    return get_local_patient(new_id)


def get_all_histories_for_patient(patient_id):
    rows = execute_query(
        "SELECT id_historial, id_paciente, observaciones, fecha "
        "FROM historial_clinico WHERE id_paciente = ? ORDER BY fecha DESC",
        (patient_id,),
        fetchall=True
    )
    return [
        {
            "id_historial": r[0],
            "id_paciente": r[1],
            "observaciones": r[2],
            "fecha": str(r[3]) if r[3] else None
        }
        for r in rows
    ]


def create_local_history(data):
    execute_query(
        "INSERT INTO historial_clinico (id_paciente, observaciones, fecha) "
        "VALUES (?, ?, GETDATE())",
        (data["id_paciente"], data.get("observaciones"))
    )
    row = execute_query(
        "SELECT MAX(id_historial) FROM historial_clinico",
        fetchone=True
    )
    history_id = row[0]
    row = execute_query(
        "SELECT id_historial, id_paciente, observaciones, fecha "
        "FROM historial_clinico WHERE id_historial = ?",
        (history_id,),
        fetchone=True
    )
    if row is None:
        return None
    return {
        "id_historial": row[0],
        "id_paciente": row[1],
        "observaciones": row[2],
        "fecha": str(row[3]) if row[3] else None
    }


def check_all_conexiones():
    from services.lpz_service import check_node_health

    local_ok = check_connection()
    estados = {
        "CBBA": {
            "hospital": "Cochabamba",
            "status": "activo" if local_ok else "desconectado",
            "online": local_ok
        }
    }
    for hospital in ["LPZ", "STCZ"]:
        estados[hospital] = check_node_health(hospital)
    return estados
