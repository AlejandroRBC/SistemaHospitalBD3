from flask import Blueprint, request
from utils.response import success_response, error_response
from db import execute_query

replica_bp = Blueprint("replica", __name__)


@replica_bp.route("/replica", methods=["POST"])
def recibir_replica():
    data = request.get_json()
    if not data or not data.get("id_paciente"):
        return error_response("Datos de replica incompletos", 400)

    execute_query(
        """INSERT INTO replica_critica
           (id_paciente, hospital_origen, tipo_sangre, alergias, enfermedades_cronicas)
           VALUES (?, ?, ?, ?, ?)""",
        (
            data["id_paciente"],
            data.get("hospital_origen", "DESCONOCIDO"),
            data.get("tipo_sangre"),
            data.get("alergias"),
            data.get("enfermedades_cronicas")
        )
    )
    return success_response({"mensaje": "Replica almacenada correctamente"}, 201)
