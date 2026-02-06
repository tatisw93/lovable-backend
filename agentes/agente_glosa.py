"""
Agente de Glosa Recorrente.
Analisa padrões históricos de glosa para prevenir rejeições futuras.

Heurísticas:
- Procedimentos com taxa de glosa acima de 20%
- Motivos de glosa recorrentes por operadora
- Padrões de valor que excedem limites contratuais
- Duplicidade de cobrança
"""
from collections import defaultdict
from decimal import Decimal

from agentes.base import AgenteBase
from models.guia_tiss import GuiaTISS
from models.procedimento import Procedimento
from models.glosa import Glosa
from models.base import db
from dominio.constantes import (
    NivelAchado,
    NivelConfianca,
    MOTIVOS_GLOSA_ANS,
)


class AgenteGlosaRecorrente(AgenteBase):
    """Agente especializado em detecção de padrões de glosa."""

    tipo = "glosa_recorrente"
    versao = "1.0.0"
    descricao = (
        "Identifica padrões recorrentes de glosa, duplicidades e "
        "procedimentos com alta probabilidade de rejeição."
    )

    def analisar(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        procedimentos = guia.procedimentos.all()

        # 1. Verificar duplicidade de procedimentos na mesma guia
        achados.extend(self._verificar_duplicidade(guia, procedimentos))

        # 2. Verificar procedimentos historicamente glosados
        achados.extend(self._verificar_historico_glosa(guia, procedimentos))

        # 3. Verificar se há glosas registradas e recorrentes
        achados.extend(self._verificar_glosas_existentes(guia))

        # 4. Verificar valores fora do padrão
        achados.extend(self._verificar_valores_atipicos(guia, procedimentos))

        return achados

    def _verificar_duplicidade(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        """Detecta cobrança duplicada de procedimentos."""
        achados = []
        contagem = defaultdict(list)

        for proc in procedimentos:
            chave = (
                proc.codigo_tuss,
                str(proc.data_realizacao),
                proc.profissional_numero or "",
            )
            contagem[chave].append(proc)

        for chave, procs in contagem.items():
            if len(procs) > 1:
                tuss, data, prof = chave
                valor_duplicado = sum(
                    float(p.valor_total or 0) for p in procs[1:]
                )
                achados.append(
                    self._criar_achado(
                        titulo="Possível duplicidade de cobrança",
                        descricao=(
                            f"Procedimento {tuss} cobrado {len(procs)} vezes na "
                            f"mesma guia, mesma data ({data})"
                            + (f", mesmo profissional ({prof})" if prof else "")
                            + ". Operadoras glosam itens duplicados automaticamente "
                            "(MG007)."
                        ),
                        nivel=NivelAchado.ADMINISTRATIVO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.90,
                        regra_referencia="Padrão TISS - Vedação de duplicidade",
                        norma_ans="RN 412/2016 - Regras de faturamento",
                        base_legal=(
                            "Cobranças duplicadas de mesmo procedimento, data e "
                            "profissional são automaticamente glosadas (MG007). "
                            "Caso haja justificativa clínica para repetição, "
                            "deve ser documentada."
                        ),
                        impacto_valor=valor_duplicado,
                        impacto_tipo="glosa_duplicidade",
                        acao_recomendada=(
                            "Remover cobrança duplicada ou, se clinicamente justificado, "
                            "anexar relatório médico justificando a repetição."
                        ),
                        evidencia=(
                            f"TUSS {tuss}: {len(procs)} ocorrências em {data}. "
                            f"IDs: {[p.id for p in procs]}"
                        ),
                    )
                )

        return achados

    def _verificar_historico_glosa(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        """Verifica se os procedimentos da guia têm histórico de glosa."""
        achados = []

        for proc in procedimentos:
            # Buscar glosas históricas para este código TUSS nesta operadora
            historico = (
                db.session.query(
                    Glosa.codigo_motivo,
                    db.func.count(Glosa.id).label("freq"),
                )
                .join(GuiaTISS, Glosa.guia_id == GuiaTISS.id)
                .join(Procedimento, Glosa.procedimento_id == Procedimento.id)
                .filter(
                    Procedimento.codigo_tuss == proc.codigo_tuss,
                    GuiaTISS.registro_ans == guia.registro_ans,
                )
                .group_by(Glosa.codigo_motivo)
                .having(db.func.count(Glosa.id) >= 3)
                .all()
            )

            for codigo_motivo, freq in historico:
                motivo_desc = MOTIVOS_GLOSA_ANS.get(
                    codigo_motivo, "Motivo não catalogado"
                )
                achados.append(
                    self._criar_achado(
                        titulo=f"Procedimento com glosa recorrente ({freq}x)",
                        descricao=(
                            f"Procedimento {proc.codigo_tuss} ({proc.descricao or 'N/D'}) "
                            f"foi glosado {freq} vezes pela operadora "
                            f"ANS {guia.registro_ans} com motivo "
                            f"'{codigo_motivo}: {motivo_desc}'. "
                            "Alta probabilidade de nova glosa."
                        ),
                        nivel=NivelAchado.ADMINISTRATIVO.value,
                        confianca=NivelConfianca.ALTA.value if freq >= 5 else NivelConfianca.MEDIA.value,
                        confianca_score=min(0.5 + freq * 0.1, 0.95),
                        regra_referencia=f"Histórico de glosa - Motivo {codigo_motivo}",
                        base_legal=f"Motivo padronizado: {motivo_desc}",
                        impacto_valor=float(proc.valor_total or 0),
                        impacto_tipo="glosa_recorrente",
                        acao_recomendada=(
                            f"Revisar procedimento {proc.codigo_tuss} antes do envio. "
                            f"Resolver causa raiz do motivo de glosa '{codigo_motivo}'."
                        ),
                        procedimento_id=proc.id,
                    )
                )

        return achados

    def _verificar_glosas_existentes(self, guia: GuiaTISS) -> list[dict]:
        """Analisa glosas já registradas na guia."""
        achados = []
        glosas = guia.glosas.all()

        if not glosas:
            return achados

        valor_total_glosa = sum(float(g.valor_glosado or 0) for g in glosas)
        valor_guia = float(guia.valor_total_informado or 0)

        if valor_guia > 0:
            taxa_glosa = valor_total_glosa / valor_guia * 100
            if taxa_glosa > 30:
                achados.append(
                    self._criar_achado(
                        titulo=f"Taxa de glosa elevada: {taxa_glosa:.1f}%",
                        descricao=(
                            f"Guia {guia.numero_guia_prestador}: {len(glosas)} "
                            f"glosa(s) totalizando R${valor_total_glosa:.2f} de "
                            f"R${valor_guia:.2f} ({taxa_glosa:.1f}%). "
                            "Taxa acima de 30% indica problema sistêmico."
                        ),
                        nivel=NivelAchado.ADMINISTRATIVO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.90,
                        impacto_valor=valor_total_glosa,
                        impacto_tipo="perda_receita",
                        acao_recomendada=(
                            "Análise detalhada dos motivos de glosa. "
                            "Considerar recurso para glosas administrativas."
                        ),
                    )
                )

        return achados

    def _verificar_valores_atipicos(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        """Detecta valores fora do padrão para o procedimento."""
        achados = []

        for proc in procedimentos:
            if not proc.valor_unitario or not proc.codigo_tuss:
                continue

            # Buscar média de valor para este TUSS nesta operadora
            media_result = (
                db.session.query(
                    db.func.avg(Procedimento.valor_unitario).label("media"),
                    db.func.count(Procedimento.id).label("total"),
                )
                .join(GuiaTISS, Procedimento.guia_id == GuiaTISS.id)
                .filter(
                    Procedimento.codigo_tuss == proc.codigo_tuss,
                    GuiaTISS.registro_ans == guia.registro_ans,
                    Procedimento.valor_unitario > 0,
                )
                .first()
            )

            if media_result and media_result.total >= 5 and media_result.media:
                media = float(media_result.media)
                valor = float(proc.valor_unitario)
                desvio_pct = abs(valor - media) / media * 100

                if desvio_pct > 50:
                    achados.append(
                        self._criar_achado(
                            titulo=f"Valor atípico: {desvio_pct:.0f}% da média",
                            descricao=(
                                f"Procedimento {proc.codigo_tuss}: valor unitário "
                                f"R${valor:.2f} difere {desvio_pct:.0f}% da média "
                                f"praticada (R${media:.2f}) para esta operadora. "
                                "Valores muito acima são glosados por MG008."
                            ),
                            nivel=NivelAchado.ADMINISTRATIVO.value,
                            confianca=(
                                NivelConfianca.MEDIA.value
                                if desvio_pct < 100
                                else NivelConfianca.ALTA.value
                            ),
                            confianca_score=min(0.5 + desvio_pct / 200, 0.95),
                            regra_referencia="Tabela contratual de valores",
                            impacto_valor=abs(valor - media) * (proc.quantidade_realizada or 1),
                            impacto_tipo="glosa_valor" if valor > media else "subfaturamento",
                            acao_recomendada=(
                                "Verificar valor contra tabela contratual vigente."
                            ),
                            procedimento_id=proc.id,
                        )
                    )

        return achados
