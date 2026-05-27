from flask import Blueprint, request
from utils.response import success_response, error_response
from services.patient_service import get_consultas_for_patient

consultas_bp = Blueprint("consultas", __name__)


@consultas_bp.route("/consulta/<int:patient_id>", methods=["GET"])
def obtener_consultas(patient_id):
    consultas = get_consultas_for_patient(patient_id)
    return success_response(consultas)


@consultas_bp.route("/hospitales", methods=["GET"])
def listar_hospitales():
    from services.patient_service import get_all_hospitals
    return success_response(get_all_hospitals())
