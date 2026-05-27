from fragment_catalog import get_hospital_for_patient, is_local
from services.patient_service import get_local_patient
from services.remote_query_service import get_remote_patient


def resolve_patient(patient_id):
    hospital = get_hospital_for_patient(patient_id)
    if hospital is None:
        return {"error": "Paciente no encontrado en el catalogo"}
    if is_local(patient_id):
        return get_local_patient(patient_id)
    return get_remote_patient(hospital, patient_id)
