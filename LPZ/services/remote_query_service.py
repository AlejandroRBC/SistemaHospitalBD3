import requests
from hospital_ips import HOSPITALS
from utils.response import error_response

TIMEOUT = 5


def get_remote_patient(hospital, patient_id):
    url = f"{HOSPITALS[hospital]}/paciente/{patient_id}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"Paciente no encontrado en {hospital}"}
    except requests.ConnectionError:
        return {"error": f"Sin conexion con {hospital}"}
    except requests.Timeout:
        return {"error": f"Tiempo de espera agotado para {hospital}"}


def post_replica_remote(hospital, data):
    url = f"{HOSPITALS[hospital]}/replica"
    try:
        resp = requests.post(url, json=data, timeout=TIMEOUT)
        if resp.status_code == 201:
            return resp.json()
        return {"error": f"Replica rechazada por {hospital}"}
    except (requests.ConnectionError, requests.Timeout) as e:
        return {"error": f"No se pudo replicar en {hospital}: {str(e)}"}


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
