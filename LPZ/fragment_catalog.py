from config import LOCAL_HOSPITAL

FRAGMENTS = {}


def get_hospital_for_patient(patient_id):
    return FRAGMENTS.get(patient_id)


def register_fragment(patient_id, hospital):
    FRAGMENTS[patient_id] = hospital


def is_local(patient_id):
    return FRAGMENTS.get(patient_id) == LOCAL_HOSPITAL
