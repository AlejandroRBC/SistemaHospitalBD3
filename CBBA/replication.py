from config import LOCAL_HOSPITAL

CRITICAL_FIELDS = ["tipo_sangre", "alergias", "enfermedades_cronicas"]


def get_critical_only(data):
    return {
        "id_paciente": data.get("id_paciente"),
        "hospital_origen": LOCAL_HOSPITAL,
        "tipo_sangre": data.get("tipo_sangre"),
        "alergias": data.get("alergias"),
        "enfermedades_cronicas": data.get("enfermedades_cronicas")
    }
