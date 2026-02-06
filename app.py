"""
Serviço de Ingestão e Auditoria Médica - Saúde Suplementar Brasileira.

Aplicação Flask que oferece:
- Ingestão de documentos multi-formato (XML TISS, PDF, planilhas, texto)
- Normalização e validação conforme padrões TISS/ANS
- Análise automatizada por agentes de auditoria especializados
- Detecção de erros, glosas e oportunidades de receita
- Frontend de upload e acompanhamento
"""
import os

from flask import Flask, jsonify, render_template
from flask_cors import CORS

from config import config_by_name
from models.base import db


def create_app(config_name: str = None) -> Flask:
    """Factory de criação da aplicação Flask."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_by_name[config_name])

    CORS(app)

    # Inicializar banco de dados
    db.init_app(app)

    # Registrar blueprints de API
    from api.routes_ingestao import bp_ingestao
    from api.routes_analise import bp_analise
    from api.routes_agentes import bp_agentes
    from api.routes_harmonizacao import bp_harmonizacao

    app.register_blueprint(bp_ingestao)
    app.register_blueprint(bp_analise)
    app.register_blueprint(bp_agentes)
    app.register_blueprint(bp_harmonizacao)

    # Criar tabelas
    with app.app_context():
        import models  # noqa: F401
        db.create_all()

    # ---- Frontend routes ----

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/upload", methods=["GET"])
    def upload_page():
        return render_template("upload.html")

    @app.route("/documentos", methods=["GET"])
    def documentos_page():
        return render_template("documentos.html")

    @app.route("/achados", methods=["GET"])
    def achados_page():
        return render_template("achados.html")

    @app.route("/padroes", methods=["GET"])
    def padroes_page():
        return render_template("padroes.html")

    # ---- API info ----

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/info", methods=["GET"])
    def api_info():
        return jsonify(
            {
                "servico": "Auditoria Médica - Saúde Suplementar",
                "versao": "1.0.0",
                "status": "operacional",
            }
        )

    return app


# Gunicorn entry point
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
