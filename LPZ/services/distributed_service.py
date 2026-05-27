from fragment_catalog import get_hospital_for_patient
from config import LOCAL_HOSPITAL
from services.patient_service import get_local_patient
from services.remote_query_service import get_remote_patient


def buscar_paciente_distribuido(patient_id):
    hospital = get_hospital_for_patient(patient_id)
    if hospital is None:
        return {"error": "Paciente no registrado en el sistema distribuido"}
    if hospital == LOCAL_HOSPITAL:
        return get_local_patient(patient_id)
    return get_remote_patient(hospital, patient_id)


def obtener_estado_conexiones():
    from services.remote_query_service import check_node_health

    estados = {}
    for hospital in ["CBBA", "STCZ"]:
        estados[hospital] = check_node_health(hospital)
    return estados
