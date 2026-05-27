from flask import Blueprint, request
from utils.response import success_response, error_response
from services.patient_service import (
    get_local_patient,
    create_local_patient,
    get_all_local_patients
)

pacientes_bp = Blueprint("pacientes", __name__)


@pacientes_bp.route("/paciente/<int:patient_id>", methods=["GET"])
def obtener_paciente(patient_id):
    paciente = get_local_patient(patient_id)
    if paciente is None:
        return error_response("Paciente no encontrado", 404)
    return success_response(paciente)


@pacientes_bp.route("/pacientes", methods=["GET"])
def listar_pacientes():
    return success_response(get_all_local_patients())


@pacientes_bp.route("/paciente", methods=["POST"])
def crear_paciente():
    data = request.get_json()
    if not data or not data.get("nombre"):
        return error_response("El campo 'nombre' es obligatorio", 400)
    paciente = create_local_patient(data)
    return success_response(paciente, 201)
