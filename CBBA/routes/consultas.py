from flask import Blueprint
from utils.response import success_response, error_response
from services.lpz_service import buscar_paciente_nacional

consultas_bp = Blueprint("consultas", __name__)


@consultas_bp.route("/buscar_nacional/<int:patient_id>", methods=["GET"])
def buscar_nacional(patient_id):
    resultado = buscar_paciente_nacional(patient_id)
    if "error" in resultado:
        return error_response(resultado["error"], 404)
    return success_response(resultado)
