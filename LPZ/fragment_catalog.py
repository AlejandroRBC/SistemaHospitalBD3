from config import LOCAL_HOSPITAL
from db import execute_query

FRAGMENTS = {}


def load_fragments():
    global FRAGMENTS
    try:
        rows = execute_query(
            "SELECT tabla, hospital FROM fragment_catalog",
            fetchall=True
        )
        FRAGMENTS = {row[0]: row[1] for row in rows}
    except Exception:
        FRAGMENTS = {}


def get_hospital_for_patient(patient_id):
    from services.patient_service import get_local_patient
    paciente = get_local_patient(patient_id)
    if paciente:
        return LOCAL_HOSPITAL
    for hospital in ["CBBA", "STCZ"]:
        try:
            from services.remote_query_service import check_node_health
            from hospital_ips import HOSPITALS
            import requests
            resp = requests.get(
                f"{HOSPITALS[hospital]}/paciente/{patient_id}",
                timeout=3
            )
            if resp.status_code == 200:
                return hospital
        except Exception:
            pass
    return None


def get_hospital_from_catalog(tabla):
    if not FRAGMENTS:
        load_fragments()
    return FRAGMENTS.get(tabla, LOCAL_HOSPITAL)


def register_fragment(patient_id, hospital):
    FRAGMENTS[patient_id] = hospital


def is_local(patient_id):
    return FRAGMENTS.get(patient_id) == LOCAL_HOSPITAL


load_fragments()
