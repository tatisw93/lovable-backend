"""
Agente de Conformidade Regulatória ANS.
Verifica aderência a normas da ANS, regras de cobertura e requisitos
regulatórios.

Heurísticas:
- Prazo de apresentação de guia
- Compatibilidade CID x procedimento x sexo/idade
- Verificação de autorização prévia
- Procedimentos no Rol ANS
- Prazo de recurso de glosa
"""
from datetime import date, timedelta

from agentes.base import AgenteBase
from models.guia_tiss import GuiaTISS
from models.procedimento import Procedimento
from dominio.constantes import (
    NivelAchado,
    NivelConfianca,
    PRAZO_APRESENTACAO_GUIA_DIAS,
    PRAZO_RECURSO_GLOSA_DIAS,
    REGRAS_CID_PROCEDIMENTO,
)
from ingestao.normalizacao.cid_validator import CidValidator, CIDS_ATENCAO


class AgenteConformidadeANS(AgenteBase):
    """Agente especializado em conformidade regulatória."""

    tipo = "conformidade_ans"
    versao = "1.0.0"
    descricao = (
        "Verifica conformidade com normas ANS, regras de cobertura, "
        "prazos regulatórios e compatibilidade clínica."
    )

    def __init__(self):
        self.cid_validator = CidValidator()

    def analisar(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        procedimentos = guia.procedimentos.all()

        # 1. Verificar prazo de apresentação
        achados.extend(self._verificar_prazo_apresentacao(guia))

        # 2. Verificar compatibilidade CID x procedimento
        achados.extend(self._verificar_cid_procedimento(guia, procedimentos))

        # 3. Verificar CIDs de atenção especial
        achados.extend(self._verificar_cid_atencao(guia))

        # 4. Verificar autorização prévia
        achados.extend(self._verificar_autorizacao(guia))

        # 5. Verificar prazo de recurso de glosas
        achados.extend(self._verificar_prazo_recurso(guia))

        return achados

    def _verificar_prazo_apresentacao(self, guia: GuiaTISS) -> list[dict]:
        achados = []

        if not guia.data_atendimento:
            return achados

        hoje = date.today()
        dias = (hoje - guia.data_atendimento).days

        if dias > PRAZO_APRESENTACAO_GUIA_DIAS:
            achados.append(
                self._criar_achado(
                    titulo=f"Guia fora do prazo de apresentação ({dias} dias)",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador}: atendimento em "
                        f"{guia.data_atendimento.isoformat()}, {dias} dias atrás. "
                        f"Prazo padrão é de {PRAZO_APRESENTACAO_GUIA_DIAS} dias. "
                        "Guias fora do prazo são glosadas (MG009)."
                    ),
                    nivel=NivelAchado.REGULATORIO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.95,
                    regra_referencia="RN 305/2012 - Prazo de apresentação",
                    norma_ans="RN 305/2012",
                    base_legal=(
                        "Conforme RN 305/2012 da ANS e regras contratuais, "
                        "guias devem ser apresentadas dentro do prazo estipulado. "
                        "O não cumprimento resulta em glosa por MG009."
                    ),
                    impacto_valor=float(guia.valor_total_informado or 0),
                    impacto_tipo="glosa_prazo",
                    acao_recomendada=(
                        "Apresentar guia imediatamente. Verificar se contrato "
                        "permite prazo diferenciado. Preparar justificativa "
                        "caso necessário recurso."
                    ),
                )
            )
        elif dias > PRAZO_APRESENTACAO_GUIA_DIAS - 5:
            # Alerta preventivo
            achados.append(
                self._criar_achado(
                    titulo=f"Guia próxima do vencimento ({dias}/{PRAZO_APRESENTACAO_GUIA_DIAS} dias)",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador}: faltam "
                        f"{PRAZO_APRESENTACAO_GUIA_DIAS - dias} dia(s) para "
                        "expirar o prazo de apresentação."
                    ),
                    nivel=NivelAchado.ADMINISTRATIVO.value,
                    confianca=NivelConfianca.MEDIA.value,
                    confianca_score=0.75,
                    regra_referencia="RN 305/2012 - Prazo de apresentação",
                    norma_ans="RN 305/2012",
                    acao_recomendada="Priorizar envio desta guia.",
                )
            )

        return achados

    def _verificar_cid_procedimento(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        """Verifica compatibilidade entre CID e procedimentos."""
        achados = []
        cid = guia.cid_principal

        if not cid:
            return achados

        cid_base = cid.split(".")[0] if "." in cid else cid

        if cid_base in REGRAS_CID_PROCEDIMENTO:
            regra = REGRAS_CID_PROCEDIMENTO[cid_base]
            prefixos_validos = regra.get("procedimentos_validos_prefixos", [])

            for proc in procedimentos:
                if not proc.codigo_tuss:
                    continue

                compativel = any(
                    proc.codigo_tuss.startswith(p) for p in prefixos_validos
                )

                if not compativel and prefixos_validos:
                    achados.append(
                        self._criar_achado(
                            titulo="Possível incompatibilidade CID x procedimento",
                            descricao=(
                                f"Procedimento {proc.codigo_tuss} ({proc.descricao or 'N/D'}) "
                                f"pode ser incompatível com CID {cid}. "
                                f"Procedimentos esperados para este CID iniciam com: "
                                f"{', '.join(prefixos_validos)}. "
                                "Operadoras glosam por MG005 quando há incompatibilidade."
                            ),
                            nivel=NivelAchado.REGULATORIO.value,
                            confianca=NivelConfianca.MEDIA.value,
                            confianca_score=0.60,
                            regra_referencia="Tabela de compatibilidade CID x TUSS",
                            norma_ans="RN 465/2021 - Rol de Procedimentos",
                            base_legal=(
                                "A compatibilidade entre diagnóstico (CID) e "
                                "procedimento (TUSS) é verificada pelas operadoras. "
                                "Incompatibilidades resultam em glosa (MG005)."
                            ),
                            impacto_valor=float(proc.valor_total or 0),
                            impacto_tipo="glosa_incompatibilidade",
                            acao_recomendada=(
                                "Verificar se o CID informado é o mais adequado "
                                "para justificar o procedimento realizado."
                            ),
                            procedimento_id=proc.id,
                        )
                    )

        return achados

    def _verificar_cid_atencao(self, guia: GuiaTISS) -> list[dict]:
        """Verifica CIDs que requerem atenção especial."""
        achados = []
        cid = guia.cid_principal

        if not cid:
            return achados

        alerta = self.cid_validator.verificar_atencao(cid)
        if alerta:
            achados.append(
                self._criar_achado(
                    titulo=f"CID de atenção especial: {alerta['codigo']}",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador} utiliza CID "
                        f"{alerta['codigo']}: {alerta['alerta']}. "
                        "CIDs inespecíficos ou de atenção especial podem "
                        "resultar em glosa."
                    ),
                    nivel=NivelAchado.REGULATORIO.value,
                    confianca=NivelConfianca.MEDIA.value,
                    confianca_score=0.70,
                    regra_referencia="CID-10 - Classificação de atenção",
                    acao_recomendada=(
                        "Substituir por CID mais específico que justifique "
                        "os procedimentos realizados."
                    ),
                )
            )

        return achados

    def _verificar_autorizacao(self, guia: GuiaTISS) -> list[dict]:
        """Verifica se guia possui autorização quando necessário."""
        achados = []

        # Guias SADT e internação geralmente requerem autorização
        tipos_autorizacao = ["guiaSP_SADT", "guiaInternacao", "guiaHonorarios"]

        if guia.tipo_guia in tipos_autorizacao and not guia.numero_autorizacao:
            achados.append(
                self._criar_achado(
                    titulo="Guia sem número de autorização",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador} ({guia.tipo_guia}): "
                        "número de autorização ausente. Procedimentos que requerem "
                        "autorização prévia são glosados sem este campo (MG002)."
                    ),
                    nivel=NivelAchado.REGULATORIO.value,
                    confianca=NivelConfianca.MEDIA.value,
                    confianca_score=0.65,
                    regra_referencia="TISS 4.01 - Autorização prévia",
                    norma_ans="RN 259/2011 - Autorização prévia",
                    base_legal=(
                        "Conforme RN 259/2011, procedimentos eletivos podem "
                        "requerer autorização prévia da operadora."
                    ),
                    impacto_valor=float(guia.valor_total_informado or 0),
                    impacto_tipo="glosa_autorizacao",
                    acao_recomendada=(
                        "Verificar se os procedimentos requerem autorização "
                        "prévia e incluir o número de autorização."
                    ),
                )
            )

        return achados

    def _verificar_prazo_recurso(self, guia: GuiaTISS) -> list[dict]:
        """Verifica prazo de recurso para glosas existentes."""
        achados = []
        glosas = guia.glosas.all()
        hoje = date.today()

        for glosa in glosas:
            if glosa.recurso_apresentado or not glosa.data_glosa:
                continue

            dias = (hoje - glosa.data_glosa).days
            if dias > PRAZO_RECURSO_GLOSA_DIAS:
                achados.append(
                    self._criar_achado(
                        titulo=f"Glosa com prazo de recurso vencido ({dias} dias)",
                        descricao=(
                            f"Glosa de R${float(glosa.valor_glosado or 0):.2f} "
                            f"(motivo: {glosa.codigo_motivo}) com {dias} dias. "
                            f"Prazo de recurso ({PRAZO_RECURSO_GLOSA_DIAS} dias) "
                            "expirado."
                        ),
                        nivel=NivelAchado.REGULATORIO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.95,
                        norma_ans="RN 412/2016 - Prazo de recurso",
                        impacto_valor=float(glosa.valor_glosado or 0),
                        impacto_tipo="perda_receita",
                        acao_recomendada=(
                            "Recurso fora do prazo regulamentar. "
                            "Avaliar negociação direta com operadora."
                        ),
                    )
                )
            elif dias > PRAZO_RECURSO_GLOSA_DIAS - 5:
                achados.append(
                    self._criar_achado(
                        titulo=f"Glosa próxima do vencimento de recurso ({dias} dias)",
                        descricao=(
                            f"Glosa de R${float(glosa.valor_glosado or 0):.2f} "
                            f"com {PRAZO_RECURSO_GLOSA_DIAS - dias} dia(s) restantes "
                            "para apresentar recurso."
                        ),
                        nivel=NivelAchado.ADMINISTRATIVO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.90,
                        norma_ans="RN 412/2016 - Prazo de recurso",
                        impacto_valor=float(glosa.valor_glosado or 0),
                        impacto_tipo="perda_receita",
                        acao_recomendada="Priorizar apresentação de recurso.",
                    )
                )

        return achados
