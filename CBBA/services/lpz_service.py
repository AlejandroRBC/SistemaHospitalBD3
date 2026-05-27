import requests
from hospital_ips import HOSPITALS

TIMEOUT = 5


def buscar_paciente_nacional(patient_id):
    url = f"{HOSPITALS['LPZ']}/buscar_paciente/{patient_id}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"Paciente no encontrado en la red nacional"}
    except requests.ConnectionError:
        return {"error": "Sin conexion con el nodo mediador (LPZ)"}
    except requests.Timeout:
        return {"error": "Tiempo de espera agotado al consultar LPZ"}


def check_node_health(hospital):
    url = f"{HOSPITALS[hospital]}/estado"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            return {"status": data.get("status", "activo"), "online": True}
        return {"status": "error", "online": False}
    except (requests.ConnectionError, requests.Timeout):
        return {"status": "desconectado", "online": False}


def enviar_replica(hospital, data):
    url = f"{HOSPITALS[hospital]}/replica"
    try:
        resp = requests.post(url, json=data, timeout=TIMEOUT)
        if resp.status_code == 201:
            return resp.json()
        return {"error": f"Replica rechazada por {hospital}"}
    except (requests.ConnectionError, requests.Timeout) as e:
        return {"error": f"No se pudo replicar en {hospital}: {str(e)}"}
