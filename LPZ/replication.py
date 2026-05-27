from config import LOCAL_HOSPITAL
from services.remote_query_service import post_replica_remote

CRITICAL_FIELDS = ["tipo_sangre", "alergias", "enfermedades_cronicas"]


def replicate_to_nodes(patient_data):
    replicas = []
    for hospital in ["CBBA", "STCZ"]:
        result = post_replica_remote(hospital, patient_data)
        replicas.append({hospital: result})
    return replicas


def get_critical_only(data):
    return {
        "id_paciente": data.get("id_paciente"),
        "hospital_origen": LOCAL_HOSPITAL,
        "tipo_sangre": data.get("tipo_sangre"),
        "alergias": data.get("alergias"),
        "enfermedades_cronicas": data.get("enfermedades_cronicas")
    }
