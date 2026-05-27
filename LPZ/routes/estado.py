from flask import Blueprint
from utils.response import success_response

estado_bp = Blueprint("estado", __name__)


@estado_bp.route("/estado")
def estado():
    return success_response({"hospital": "LPZ", "status": "activo"})
