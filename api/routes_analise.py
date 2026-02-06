"""
Rotas de análise e auditoria.
"""
from flask import Blueprint, request, jsonify

from agentes.registro_agentes import RegistroAgentes
from analise.detector_padroes import DetectorPadroes
from analise.calculadora_impacto import CalculadoraImpacto
from models.achado_auditoria import AchadoAuditoria
from models.guia_tiss import GuiaTISS

bp_analise = Blueprint("analise", __name__, url_prefix="/api/v1/analise")


@bp_analise.route("/documento/<int:doc_id>", methods=["POST"])
def analisar_documento(doc_id):
    """
    Executa análise completa de um documento ingerido.
    Roda todos os agentes de auditoria e retorna achados.

    Query params:
        agentes: Lista de agentes a executar (separados por vírgula).
                 Se omitido, executa todos.
    """
    agentes_param = request.args.get("agentes")
    agentes_selecionados = (
        [a.strip() for a in agentes_param.split(",")]
        if agentes_param
        else None
    )

    motor = RegistroAgentes.criar_motor(agentes_selecionados)
    resultado = motor.analisar_documento(doc_id)

    return jsonify(resultado)


@bp_analise.route("/guia/<int:guia_id>", methods=["POST"])
def analisar_guia(guia_id):
    """
    Executa análise de uma guia específica.
    """
    guia = GuiaTISS.query.get_or_404(guia_id)

    agentes_param = request.args.get("agentes")
    agentes_selecionados = (
        [a.strip() for a in agentes_param.split(",")]
        if agentes_param
        else None
    )

    motor = RegistroAgentes.criar_motor(agentes_selecionados)

    achados = []
    for agente in motor._agentes:
        achados_agente = agente.analisar(guia)
        for a in achados_agente:
            a["guia_id"] = guia.id
        achados.extend(achados_agente)

    return jsonify(
        {
            "guia_id": guia_id,
            "numero_guia": guia.numero_guia_prestador,
            "total_achados": len(achados),
            "achados": achados,
        }
    )


@bp_analise.route("/achados", methods=["GET"])
def listar_achados():
    """
    Lista achados de auditoria com filtros.

    Query params:
        documento_id, guia_id, agente_tipo, nivel, confianca,
        resolvido, pagina, por_pagina
    """
    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = request.args.get("por_pagina", 20, type=int)

    query = AchadoAuditoria.query.order_by(AchadoAuditoria.criado_em.desc())

    # Filtros
    doc_id = request.args.get("documento_id", type=int)
    if doc_id:
        query = query.filter_by(documento_id=doc_id)

    guia_id = request.args.get("guia_id", type=int)
    if guia_id:
        query = query.filter_by(guia_id=guia_id)

    agente = request.args.get("agente_tipo")
    if agente:
        query = query.filter_by(agente_tipo=agente)

    nivel = request.args.get("nivel")
    if nivel:
        query = query.filter_by(nivel=nivel)

    confianca = request.args.get("confianca")
    if confianca:
        query = query.filter_by(confianca=confianca)

    resolvido = request.args.get("resolvido")
    if resolvido is not None:
        query = query.filter_by(resolvido=resolvido.lower() == "true")

    paginacao = query.paginate(page=pagina, per_page=por_pagina, error_out=False)

    return jsonify(
        {
            "achados": [a.to_dict() for a in paginacao.items],
            "paginacao": {
                "pagina": paginacao.page,
                "por_pagina": paginacao.per_page,
                "total": paginacao.total,
                "paginas": paginacao.pages,
            },
        }
    )


@bp_analise.route("/padroes/glosa", methods=["GET"])
def padroes_glosa():
    """Detecta padrões recorrentes de glosa."""
    registro_ans = request.args.get("registro_ans")
    detector = DetectorPadroes()
    resultado = detector.detectar_padroes_glosa(registro_ans)
    return jsonify(resultado)


@bp_analise.route("/padroes/procedimentos", methods=["GET"])
def procedimentos_problematicos():
    """Identifica procedimentos com alta taxa de glosa."""
    detector = DetectorPadroes()
    resultado = detector.detectar_procedimentos_problematicos()
    return jsonify(resultado)


@bp_analise.route("/padroes/temporal", methods=["GET"])
def padroes_temporais():
    """Detecta padrões temporais de faturamento e glosa."""
    detector = DetectorPadroes()
    resultado = detector.detectar_padroes_temporais()
    return jsonify(resultado)


@bp_analise.route("/impacto/glosas-recuperaveis", methods=["GET"])
def glosas_recuperaveis():
    """Identifica glosas potencialmente recuperáveis."""
    registro_ans = request.args.get("registro_ans")
    calc = CalculadoraImpacto()
    resultado = calc.calcular_glosas_recuperaveis(registro_ans)
    return jsonify(resultado)
