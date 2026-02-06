"""
Serviço de Ingestão e Auditoria Médica - Saúde Suplementar Brasileira.

Aplicação Flask que oferece:
- Ingestão de documentos multi-formato (XML TISS, PDF, planilhas, texto)
- Normalização e validação conforme padrões TISS/ANS
- Análise automatizada por agentes de auditoria especializados
- Detecção de erros, glosas e oportunidades de receita
"""
import os

from flask import Flask, jsonify

from config import config_by_name
from models.base import db


def create_app(config_name: str = None) -> Flask:
    """Factory de criação da aplicação Flask."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Inicializar banco de dados
    db.init_app(app)

    # Registrar blueprints
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
        # Importar modelos para que o SQLAlchemy os registre
        import models  # noqa: F401
        db.create_all()

    # Rota de health check
    @app.route("/", methods=["GET"])
    def index():
        return jsonify(
            {
                "servico": "Auditoria Médica - Saúde Suplementar",
                "versao": "1.0.0",
                "status": "operacional",
                "endpoints": {
                    "ingestao": "/api/v1/ingestao/upload",
                    "documentos": "/api/v1/ingestao/documentos",
                    "analise": "/api/v1/analise/documento/<id>",
                    "achados": "/api/v1/analise/achados",
                    "padroes_glosa": "/api/v1/analise/padroes/glosa",
                    "agentes": "/api/v1/agentes/",
                    "harmonizacao": "/harmonizacao",
                },
            }
        )

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
