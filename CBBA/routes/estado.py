from flask import Blueprint
from utils.response import success_response
from services.patient_service import check_all_conexiones

estado_bp = Blueprint("estado", __name__)


@estado_bp.route("/estado")
def estado():
    return success_response({"hospital": "CBBA", "status": "activo"})


@estado_bp.route("/check_conexiones")
def check_conexiones():
    estados = check_all_conexiones()
    return success_response(estados)
