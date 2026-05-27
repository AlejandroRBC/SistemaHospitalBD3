from db import execute_query, execute_openquery, execute_openquery_insert
from services.patient_service import get_local_patient


def buscar_paciente_nacional(patient_id):
    local = get_local_patient(patient_id)
    if local is not None:
        return local

    try:
        rows = execute_openquery(
            "SELECT id_paciente, nombre, tipo_sangre, alergias, "
            "enfermedades_cronicas, id_hospital "
            f"FROM paciente WHERE id_paciente = {patient_id}"
        )
        if rows:
            r = rows[0]
            return {
                "id_paciente": r[0],
                "nombre": r[1],
                "tipo_sangre": r[2],
                "alergias": r[3],
                "enfermedades_cronicas": r[4],
                "id_hospital": r[5],
                "hospital_origen": "LPZ"
            }
        return {"error": "Paciente no encontrado en la red nacional"}
    except Exception as e:
        return {"error": f"Error al consultar LPZ via Linked Server: {str(e)}"}


def check_node_health(hospital):
    if hospital == "LPZ":
        try:
            execute_openquery("SELECT 1")
            return {"status": "activo", "online": True}
        except Exception:
            return {"status": "desconectado", "online": False}
    return {"status": "desconectado", "online": False}


def enviar_replica(hospital, data):
    if hospital == "LPZ":
        try:
            execute_openquery_insert(
                "replica_critica",
                ["id_paciente", "hospital_origen", "tipo_sangre",
                 "alergias", "enfermedades_cronicas"],
                (
                    data["id_paciente"],
                    data.get("hospital_origen", "CBBA"),
                    data.get("tipo_sangre"),
                    data.get("alergias"),
                    data.get("enfermedades_cronicas")
                )
            )
            return {"mensaje": f"Replica almacenada en {hospital}"}
        except Exception as e:
            return {"error": f"No se pudo replicar en {hospital}: {str(e)}"}
    return {"error": f"STCZ no implementado"}
