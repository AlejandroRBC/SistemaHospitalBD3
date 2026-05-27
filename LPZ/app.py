from flask import Flask, render_template
from config import DEBUG, PORT

app = Flask(__name__)

from routes.estado import estado_bp
from routes.pacientes import pacientes_bp
from routes.historial import historial_bp
from routes.mediador import mediador_bp
from routes.consultas import consultas_bp

app.register_blueprint(estado_bp)
app.register_blueprint(pacientes_bp)
app.register_blueprint(historial_bp)
app.register_blueprint(mediador_bp)
app.register_blueprint(consultas_bp)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    print(f"Servidor LPZ iniciado en puerto {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
