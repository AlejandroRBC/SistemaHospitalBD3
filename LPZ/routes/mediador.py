from flask import Blueprint, request
from utils.response import success_response, error_response
from mediator import resolve_patient
from db import execute_query

mediador_bp = Blueprint("mediador", __name__)


@mediador_bp.route("/buscar_paciente/<int:patient_id>", methods=["GET"])
def buscar_paciente_nacional(patient_id):
    resultado = resolve_patient(patient_id)
    if "error" in resultado:
        return error_response(resultado["error"], 404)
    return success_response(resultado)


@mediador_bp.route("/replica", methods=["POST"])
def recibir_replica():
    data = request.get_json()
    if not data or not data.get("id_paciente"):
        return error_response("Datos de replica incompletos", 400)

    execute_query(
        """INSERT INTO replica_critica
           (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas)
           VALUES (%s, %s, %s, %s, %s)""",
        (
            data["id_paciente"],
            data.get("hospital_origen", "DESCONOCIDO"),
            data.get("tipo_sangre"),
            data.get("alergias"),
            data.get("enfermedades_cronicas")
        )
    )
    return success_response({"mensaje": "Replica almacenada correctamente"}, 201)
