"""
Rotas de gerenciamento dos agentes de auditoria.
"""
from flask import Blueprint, jsonify

from agentes.registro_agentes import RegistroAgentes, AGENTES_DISPONIVEIS

bp_agentes = Blueprint("agentes", __name__, url_prefix="/api/v1/agentes")


@bp_agentes.route("/", methods=["GET"])
def listar_agentes():
    """
    Lista todos os agentes de auditoria disponíveis.

    Retorna tipo, descrição, nível primário e versão de cada agente.
    """
    agentes = RegistroAgentes.listar_agentes()
    return jsonify(
        {
            "total_agentes": len(agentes),
            "agentes": agentes,
        }
    )


@bp_agentes.route("/<tipo>", methods=["GET"])
def detalhe_agente(tipo):
    """
    Detalha um agente específico com suas heurísticas e regras.
    """
    if tipo not in AGENTES_DISPONIVEIS:
        return jsonify({"erro": f"Agente '{tipo}' não encontrado."}), 404

    info = AGENTES_DISPONIVEIS[tipo]
    agente = info["classe"]()

    return jsonify(
        {
            "tipo": tipo,
            "versao": agente.versao,
            "descricao": info["descricao"],
            "nivel_primario": info["nivel_primario"],
            "formato_resposta": {
                "descricao": "Formato padrão de resposta dos agentes",
                "campos": {
                    "agente_tipo": "Identificador do agente",
                    "agente_versao": "Versão do agente",
                    "nivel": "tecnico | administrativo | regulatorio",
                    "confianca": "alta | media | baixa",
                    "confianca_score": "Score numérico 0.0-1.0",
                    "titulo": "Título do achado",
                    "descricao": "Descrição detalhada do erro/oportunidade",
                    "evidencia": "Dados que sustentam o achado",
                    "regra_referencia": "Referência à regra TISS/ANS",
                    "norma_ans": "Norma ANS aplicável",
                    "base_legal": "Fundamentação legal/regulatória",
                    "impacto_valor": "Valor estimado do impacto financeiro",
                    "impacto_tipo": "Tipo de impacto (perda_receita, glosa, subfaturamento)",
                    "acao_recomendada": "Ação corretiva recomendada",
                },
            },
        }
    )
