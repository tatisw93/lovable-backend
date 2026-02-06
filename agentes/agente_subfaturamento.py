"""
Agente de Subfaturamento.
Detecta itens não faturados, quantidades incorretas e oportunidades
de receita perdida.

Heurísticas:
- Procedimentos com quantidade zero ou ausente
- Valores unitários zerados
- Materiais/medicamentos sem cobrança associada
- Procedimentos complementares ausentes (ex: anestesia em cirurgia)
- Diárias não cobradas em internações
"""
from decimal import Decimal
from datetime import timedelta

from agentes.base import AgenteBase
from models.guia_tiss import GuiaTISS
from models.procedimento import Procedimento
from dominio.constantes import (
    TipoGuiaTISS,
    NivelAchado,
    NivelConfianca,
    PORTES_CBHPM,
)


# Procedimentos que normalmente requerem complementares
PROCEDIMENTOS_COM_COMPLEMENTARES = {
    # Cirurgias que normalmente requerem anestesia
    "3": {
        "descricao": "Procedimentos cirúrgicos",
        "complementares": [
            {"prefixo": "40801", "tipo": "anestesia", "descricao": "Ato anestésico"},
            {"prefixo": "60000", "tipo": "taxa_sala", "descricao": "Taxa de sala cirúrgica"},
        ],
    },
}

# Faixas de procedimentos de internação que requerem diárias
FAIXA_INTERNACAO_REQUER_DIARIA = {
    "prefixo_diaria": "6001",
    "descricao": "Diária hospitalar",
}


class AgenteSubfaturamento(AgenteBase):
    """Agente especializado em detecção de subfaturamento."""

    tipo = "subfaturamento"
    versao = "1.0.0"
    descricao = (
        "Detecta oportunidades de receita perdida por itens não faturados, "
        "quantidades incorretas e procedimentos complementares ausentes."
    )

    def analisar(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        procedimentos = guia.procedimentos.all()

        # 1. Verificar quantidades zeradas ou ausentes
        achados.extend(self._verificar_quantidades(guia, procedimentos))

        # 2. Verificar valores zerados
        achados.extend(self._verificar_valores(guia, procedimentos))

        # 3. Verificar procedimentos complementares ausentes
        achados.extend(self._verificar_complementares(guia, procedimentos))

        # 4. Verificar diárias em internação
        achados.extend(self._verificar_diarias(guia, procedimentos))

        # 5. Verificar inconsistência quantidade x valor
        achados.extend(self._verificar_calculo(guia, procedimentos))

        return achados

    def _verificar_quantidades(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        achados = []

        for proc in procedimentos:
            if not proc.quantidade_realizada or proc.quantidade_realizada <= 0:
                achados.append(
                    self._criar_achado(
                        titulo="Procedimento com quantidade zerada",
                        descricao=(
                            f"Procedimento {proc.codigo_tuss} ({proc.descricao or 'N/D'}) "
                            "na guia {guia.numero_guia_prestador} com quantidade "
                            "zerada ou não informada. Se o procedimento foi realizado, "
                            "a quantidade mínima é 1."
                        ),
                        nivel=NivelAchado.ADMINISTRATIVO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.90,
                        regra_referencia="TISS 4.01 - quantidadeExecutada",
                        base_legal=(
                            "Todo procedimento realizado deve ter quantidade mínima "
                            "de 1 unidade informada."
                        ),
                        impacto_valor=float(proc.valor_unitario or 0),
                        impacto_tipo="subfaturamento",
                        acao_recomendada=(
                            f"Informar quantidade realizada do procedimento {proc.codigo_tuss}."
                        ),
                        procedimento_id=proc.id,
                    )
                )

        return achados

    def _verificar_valores(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        achados = []

        for proc in procedimentos:
            if proc.quantidade_realizada and proc.quantidade_realizada > 0:
                if not proc.valor_unitario or float(proc.valor_unitario) <= 0:
                    achados.append(
                        self._criar_achado(
                            titulo="Procedimento sem valor unitário",
                            descricao=(
                                f"Procedimento {proc.codigo_tuss} com "
                                f"{proc.quantidade_realizada} unidade(s) realizada(s) "
                                "mas valor unitário zerado ou ausente. "
                                "Receita não faturada."
                            ),
                            nivel=NivelAchado.ADMINISTRATIVO.value,
                            confianca=NivelConfianca.ALTA.value,
                            confianca_score=0.92,
                            regra_referencia="TISS 4.01 - valorUnitario",
                            impacto_tipo="subfaturamento",
                            acao_recomendada=(
                                f"Informar valor unitário conforme tabela contratual "
                                f"para o procedimento {proc.codigo_tuss}."
                            ),
                            procedimento_id=proc.id,
                        )
                    )

                if not proc.valor_total or float(proc.valor_total) <= 0:
                    if proc.valor_unitario and float(proc.valor_unitario) > 0:
                        valor_correto = float(proc.valor_unitario) * proc.quantidade_realizada
                        achados.append(
                            self._criar_achado(
                                titulo="Valor total não informado",
                                descricao=(
                                    f"Procedimento {proc.codigo_tuss}: valor total "
                                    f"ausente. Deveria ser R${valor_correto:.2f} "
                                    f"(R${float(proc.valor_unitario):.2f} x "
                                    f"{proc.quantidade_realizada})."
                                ),
                                nivel=NivelAchado.ADMINISTRATIVO.value,
                                confianca=NivelConfianca.ALTA.value,
                                confianca_score=0.95,
                                impacto_valor=valor_correto,
                                impacto_tipo="subfaturamento",
                                acao_recomendada="Calcular e informar valor total.",
                                procedimento_id=proc.id,
                            )
                        )

        return achados

    def _verificar_complementares(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        """Detecta procedimentos complementares ausentes."""
        achados = []
        codigos_presentes = {p.codigo_tuss for p in procedimentos if p.codigo_tuss}

        for proc in procedimentos:
            if not proc.codigo_tuss:
                continue

            # Verificar se procedimento cirúrgico tem complementares
            prefixo = proc.codigo_tuss[:1]
            if prefixo in PROCEDIMENTOS_COM_COMPLEMENTARES:
                regra = PROCEDIMENTOS_COM_COMPLEMENTARES[prefixo]
                for comp in regra["complementares"]:
                    tem_complementar = any(
                        c.startswith(comp["prefixo"]) for c in codigos_presentes
                    )
                    if not tem_complementar:
                        achados.append(
                            self._criar_achado(
                                titulo=f"{comp['descricao']} ausente para procedimento cirúrgico",
                                descricao=(
                                    f"Procedimento cirúrgico {proc.codigo_tuss} "
                                    f"({proc.descricao or 'N/D'}) sem "
                                    f"{comp['descricao'].lower()} associado. "
                                    "Procedimentos cirúrgicos normalmente incluem "
                                    f"cobrança de {comp['tipo']}."
                                ),
                                nivel=NivelAchado.ADMINISTRATIVO.value,
                                confianca=NivelConfianca.MEDIA.value,
                                confianca_score=0.65,
                                base_legal=(
                                    f"{comp['descricao']} é item complementar padrão "
                                    "para procedimentos cirúrgicos."
                                ),
                                impacto_tipo="subfaturamento",
                                acao_recomendada=(
                                    f"Verificar se {comp['descricao'].lower()} foi "
                                    "realizado e incluir na cobrança."
                                ),
                                procedimento_id=proc.id,
                            )
                        )

        return achados

    def _verificar_diarias(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        """Verifica se guias de internação possuem diárias cobradas."""
        achados = []

        if guia.tipo_guia != TipoGuiaTISS.INTERNACAO.value:
            return achados

        if not guia.data_atendimento or not guia.data_fim_atendimento:
            return achados

        dias_internacao = (
            guia.data_fim_atendimento - guia.data_atendimento
        ).days

        if dias_internacao <= 0:
            return achados

        # Verificar se há diárias cobradas
        diarias = [
            p
            for p in procedimentos
            if p.codigo_tuss
            and p.codigo_tuss.startswith(
                FAIXA_INTERNACAO_REQUER_DIARIA["prefixo_diaria"]
            )
        ]

        if not diarias:
            achados.append(
                self._criar_achado(
                    titulo="Internação sem diárias cobradas",
                    descricao=(
                        f"Guia de internação {guia.numero_guia_prestador} com "
                        f"{dias_internacao} dia(s) de internação mas sem "
                        "cobrança de diárias. Possível subfaturamento."
                    ),
                    nivel=NivelAchado.ADMINISTRATIVO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.88,
                    base_legal=(
                        "Diárias hospitalares são itens faturáveis conforme "
                        "contrato e Tabela TUSS (faixa 60xxx)."
                    ),
                    impacto_tipo="subfaturamento",
                    acao_recomendada=(
                        f"Incluir cobrança de {dias_internacao} diária(s) "
                        "conforme tipo de acomodação."
                    ),
                )
            )
        else:
            total_diarias_cobradas = sum(
                d.quantidade_realizada or 0 for d in diarias
            )
            if total_diarias_cobradas < dias_internacao:
                diferenca = dias_internacao - total_diarias_cobradas
                achados.append(
                    self._criar_achado(
                        titulo="Quantidade de diárias inferior ao período de internação",
                        descricao=(
                            f"Internação de {dias_internacao} dia(s), porém apenas "
                            f"{total_diarias_cobradas} diária(s) cobrada(s). "
                            f"Faltam {diferenca} diária(s)."
                        ),
                        nivel=NivelAchado.ADMINISTRATIVO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.85,
                        impacto_tipo="subfaturamento",
                        acao_recomendada=(
                            f"Incluir {diferenca} diária(s) faltante(s)."
                        ),
                    )
                )

        return achados

    def _verificar_calculo(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        """Verifica inconsistências de cálculo que causam subfaturamento."""
        achados = []

        for proc in procedimentos:
            if (
                proc.valor_unitario
                and proc.quantidade_realizada
                and proc.valor_total
            ):
                esperado = float(proc.valor_unitario) * proc.quantidade_realizada
                informado = float(proc.valor_total)
                if informado < esperado - 0.01:
                    diferenca = esperado - informado
                    achados.append(
                        self._criar_achado(
                            titulo="Valor total abaixo do calculado",
                            descricao=(
                                f"Procedimento {proc.codigo_tuss}: valor total "
                                f"informado (R${informado:.2f}) é menor que "
                                f"unitário x quantidade (R${esperado:.2f}). "
                                f"Diferença: R${diferenca:.2f}."
                            ),
                            nivel=NivelAchado.ADMINISTRATIVO.value,
                            confianca=NivelConfianca.ALTA.value,
                            confianca_score=0.95,
                            impacto_valor=diferenca,
                            impacto_tipo="subfaturamento",
                            acao_recomendada=(
                                f"Corrigir valor total para R${esperado:.2f}."
                            ),
                            evidencia=(
                                f"R${float(proc.valor_unitario):.2f} x "
                                f"{proc.quantidade_realizada} = R${esperado:.2f}, "
                                f"informado: R${informado:.2f}"
                            ),
                            procedimento_id=proc.id,
                        )
                    )

        return achados
