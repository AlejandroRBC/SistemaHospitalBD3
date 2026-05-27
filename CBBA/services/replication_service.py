from services.lpz_service import enviar_replica


def replicate_critical_data(patient_data):
    replicas = []
    for hospital in ["LPZ", "STCZ"]:
        result = enviar_replica(hospital, patient_data)
        replicas.append({hospital: result})
    return replicas
