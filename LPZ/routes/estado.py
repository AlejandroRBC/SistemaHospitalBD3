from flask import Blueprint
from utils.response import success_response
from services.distributed_service import obtener_estado_conexiones

estado_bp = Blueprint("estado", __name__)


@estado_bp.route("/estado")
def estado():
    return success_response({"hospital": "LPZ", "status": "activo"})


@estado_bp.route("/check_conexiones")
def check_conexiones():
    estados = obtener_estado_conexiones()
    return success_response(estados)
