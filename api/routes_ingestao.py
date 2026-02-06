"""
Rotas de ingestão de documentos.
"""
import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from ingestao.pipeline import PipelineIngestao
from models.documento import Documento
from dominio.constantes import StatusDocumento

bp_ingestao = Blueprint("ingestao", __name__, url_prefix="/api/v1/ingestao")

EXTENSOES_PERMITIDAS = {"xml", "pdf", "xlsx", "xls", "csv", "txt"}


def _extensao_permitida(nome: str) -> bool:
    return "." in nome and nome.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS


@bp_ingestao.route("/upload", methods=["POST"])
def upload_documento():
    """
    Upload e processamento de documento.

    Aceita: XML TISS, PDF, XLSX, XLS, CSV, TXT.
    Executa o pipeline completo: parsing → normalização → enriquecimento → persistência.

    Returns:
        JSON com resultado do processamento.
    """
    if "arquivo" not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado. Use o campo 'arquivo'."}), 400

    arquivo = request.files["arquivo"]
    if not arquivo.filename:
        return jsonify({"erro": "Nome de arquivo vazio."}), 400

    if not _extensao_permitida(arquivo.filename):
        return jsonify(
            {
                "erro": f"Tipo de arquivo não suportado. Extensões aceitas: {', '.join(EXTENSOES_PERMITIDAS)}",
            }
        ), 400

    conteudo = arquivo.read()
    nome = secure_filename(arquivo.filename)

    pipeline = PipelineIngestao()
    resultado = pipeline.processar_arquivo(conteudo, nome)

    status_code = 200 if resultado["status"] == "sucesso" else 422
    if resultado["status"] == "duplicado":
        status_code = 409

    return jsonify(resultado), status_code


@bp_ingestao.route("/documentos", methods=["GET"])
def listar_documentos():
    """Lista todos os documentos ingeridos."""
    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = request.args.get("por_pagina", 20, type=int)
    status = request.args.get("status")

    query = Documento.query.order_by(Documento.criado_em.desc())
    if status:
        query = query.filter_by(status=status)

    paginacao = query.paginate(page=pagina, per_page=por_pagina, error_out=False)

    return jsonify(
        {
            "documentos": [
                {
                    "id": d.id,
                    "nome_arquivo": d.nome_arquivo,
                    "tipo_arquivo": d.tipo_arquivo,
                    "tamanho_bytes": d.tamanho_bytes,
                    "status": d.status,
                    "criado_em": d.criado_em.isoformat() if d.criado_em else None,
                    "total_guias": d.guias.count(),
                }
                for d in paginacao.items
            ],
            "paginacao": {
                "pagina": paginacao.page,
                "por_pagina": paginacao.per_page,
                "total": paginacao.total,
                "paginas": paginacao.pages,
            },
        }
    )


@bp_ingestao.route("/documentos/<int:doc_id>", methods=["GET"])
def obter_documento(doc_id):
    """Obtém detalhes de um documento."""
    doc = Documento.query.get_or_404(doc_id)
    return jsonify(
        {
            "id": doc.id,
            "nome_arquivo": doc.nome_arquivo,
            "tipo_arquivo": doc.tipo_arquivo,
            "tamanho_bytes": doc.tamanho_bytes,
            "status": doc.status,
            "erro_processamento": doc.erro_processamento,
            "metadados_extraidos": doc.metadados_extraidos,
            "criado_em": doc.criado_em.isoformat() if doc.criado_em else None,
            "guias": [
                {
                    "id": g.id,
                    "tipo_guia": g.tipo_guia,
                    "numero_guia_prestador": g.numero_guia_prestador,
                    "registro_ans": g.registro_ans,
                    "cid_principal": g.cid_principal,
                    "valor_total_informado": float(g.valor_total_informado or 0),
                    "total_procedimentos": g.procedimentos.count(),
                }
                for g in doc.guias.all()
            ],
        }
    )
