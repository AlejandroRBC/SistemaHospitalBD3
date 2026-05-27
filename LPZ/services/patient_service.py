from config import LOCAL_HOSPITAL
from db import execute_query


def get_local_patient(patient_id):
    row = execute_query(
        "SELECT id_paciente, nombre, tipo_sangre, alergias, enfermedades_cronicas, id_hospital "
        "FROM paciente WHERE id_paciente = %s",
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
        "VALUES (%s, %s, %s, %s, %s)",
        (
            data["nombre"],
            data.get("tipo_sangre"),
            data.get("alergias"),
            data.get("enfermedades_cronicas"),
            data.get("id_hospital", 1)
        )
    )
    row = execute_query(
        "SELECT MAX(id_paciente) FROM paciente",
        fetchone=True
    )
    new_id = row[0]
    from fragment_catalog import register_fragment
    register_fragment(new_id, LOCAL_HOSPITAL)
    return get_local_patient(new_id)


def get_local_history(history_id):
    row = execute_query(
        "SELECT id_historial, id_paciente, observaciones, fecha "
        "FROM historial_clinico WHERE id_historial = %s",
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


def get_all_histories_for_patient(patient_id):
    rows = execute_query(
        "SELECT id_historial, id_paciente, observaciones, fecha "
        "FROM historial_clinico WHERE id_paciente = %s ORDER BY fecha DESC",
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
        "VALUES (%s, %s, NOW())",
        (data["id_paciente"], data.get("observaciones"))
    )
    row = execute_query(
        "SELECT MAX(id_historial) FROM historial_clinico",
        fetchone=True
    )
    return get_local_history(row[0])
