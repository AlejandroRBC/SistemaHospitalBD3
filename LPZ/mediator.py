from fragment_catalog import get_hospital_for_patient, get_hospital_from_catalog
from services.patient_service import get_local_patient
from services.remote_query_service import get_remote_patient
from db import execute_query


def log_distributed_query(solicitante, destino, endpoint, estado):
    try:
        execute_query(
            "INSERT INTO distributed_logs "
            "(hospital_solicitante, hospital_destino, endpoint, estado) "
            "VALUES (%s, %s, %s, %s)",
            (solicitante, destino, endpoint, estado)
        )
    except Exception:
        pass


def resolve_patient(patient_id, solicitante="CBBA"):
    hospital = get_hospital_for_patient(patient_id)
    if hospital is None:
        log_distributed_query(solicitante, "desconocido",
                              f"/buscar_paciente/{patient_id}", "error")
        return {"error": "Paciente no encontrado en el catalogo"}
    if hospital == "LPZ":
        log_distributed_query(solicitante, "LPZ",
                              f"/buscar_paciente/{patient_id}", "ok")
        return get_local_patient(patient_id)
    resultado = get_remote_patient(hospital, patient_id)
    estado_log = "ok" if "error" not in resultado else "error"
    log_distributed_query(solicitante, hospital,
                          f"/buscar_paciente/{patient_id}", estado_log)
    return resultado
