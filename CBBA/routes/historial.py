from flask import Blueprint, request
from utils.response import success_response, error_response
from services.patient_service import (
    get_all_histories_for_patient,
    create_local_history
)

historial_bp = Blueprint("historial", __name__)


@historial_bp.route("/historial/<int:patient_id>", methods=["GET"])
def obtener_historial(patient_id):
    historial = get_all_histories_for_patient(patient_id)
    return success_response(historial)


@historial_bp.route("/historial", methods=["POST"])
def crear_historial():
    data = request.get_json()
    if not data or not data.get("id_paciente"):
        return error_response("El campo 'id_paciente' es obligatorio", 400)
    historial = create_local_history(data)
    return success_response(historial, 201)
