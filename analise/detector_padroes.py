"""
Detector de padrões recorrentes em dados de auditoria.
Identifica padrões de glosa, faturamento e comportamento
que se repetem ao longo do tempo.
"""
from collections import Counter, defaultdict
from typing import Optional

from models.base import db
from models.glosa import Glosa
from models.procedimento import Procedimento
from models.guia_tiss import GuiaTISS


class DetectorPadroes:
    """
    Detecta padrões recorrentes nos dados históricos:
    - Glosas recorrentes por motivo/operadora/procedimento
    - Procedimentos frequentemente rejeitados
    - Padrões temporais de faturamento
    - Concentração de erros em prestadores específicos
    """

    def detectar_padroes_glosa(
        self, operadora_registro_ans: Optional[str] = None
    ) -> dict:
        """
        Detecta padrões recorrentes de glosa.

        Returns:
            dict com padrões identificados, frequências e recomendações.
        """
        query = db.session.query(
            Glosa.codigo_motivo,
            Glosa.descricao_motivo,
            db.func.count(Glosa.id).label("frequencia"),
            db.func.sum(Glosa.valor_glosado).label("valor_total"),
        ).group_by(
            Glosa.codigo_motivo, Glosa.descricao_motivo
        ).order_by(
            db.func.count(Glosa.id).desc()
        )

        if operadora_registro_ans:
            query = query.join(GuiaTISS).filter(
                GuiaTISS.registro_ans == operadora_registro_ans
            )

        resultados = query.limit(20).all()

        padroes = []
        for codigo, descricao, freq, valor in resultados:
            padroes.append(
                {
                    "codigo_motivo": codigo,
                    "descricao": descricao,
                    "frequencia": freq,
                    "valor_total_glosado": float(valor) if valor else 0,
                    "recorrente": freq >= 3,
                    "recomendacao": self._recomendar_acao_glosa(codigo, freq),
                }
            )

        return {
            "total_padroes": len(padroes),
            "padroes": padroes,
        }

    def detectar_procedimentos_problematicos(self) -> dict:
        """
        Identifica procedimentos com alta taxa de glosa.
        """
        # Procedimentos com mais glosas
        query = (
            db.session.query(
                Procedimento.codigo_tuss,
                Procedimento.descricao,
                db.func.count(Glosa.id).label("total_glosas"),
                db.func.sum(Glosa.valor_glosado).label("valor_glosado_total"),
                db.func.count(Procedimento.id).label("total_faturado"),
            )
            .outerjoin(Glosa, Glosa.procedimento_id == Procedimento.id)
            .group_by(Procedimento.codigo_tuss, Procedimento.descricao)
            .having(db.func.count(Glosa.id) > 0)
            .order_by(db.func.count(Glosa.id).desc())
            .limit(20)
        )

        resultados = query.all()
        problematicos = []
        for tuss, desc, glosas, valor_glosa, total in resultados:
            taxa = (glosas / total * 100) if total > 0 else 0
            problematicos.append(
                {
                    "codigo_tuss": tuss,
                    "descricao": desc,
                    "total_faturado": total,
                    "total_glosas": glosas,
                    "taxa_glosa_pct": round(taxa, 1),
                    "valor_glosado_total": float(valor_glosa) if valor_glosa else 0,
                    "criticidade": "alta" if taxa > 30 else "media" if taxa > 15 else "baixa",
                }
            )

        return {
            "total_procedimentos": len(problematicos),
            "procedimentos": problematicos,
        }

    def detectar_padroes_temporais(self) -> dict:
        """
        Detecta padrões temporais de faturamento e glosa.
        """
        # Agrupamento mensal de glosas
        query = (
            db.session.query(
                db.func.strftime("%Y-%m", GuiaTISS.data_atendimento).label("mes"),
                db.func.count(GuiaTISS.id).label("total_guias"),
                db.func.sum(GuiaTISS.valor_total_informado).label("valor_faturado"),
                db.func.sum(GuiaTISS.valor_total_glosado).label("valor_glosado"),
            )
            .filter(GuiaTISS.data_atendimento.isnot(None))
            .group_by(db.func.strftime("%Y-%m", GuiaTISS.data_atendimento))
            .order_by(db.func.strftime("%Y-%m", GuiaTISS.data_atendimento).desc())
            .limit(12)
        )

        resultados = query.all()
        meses = []
        for mes, total, faturado, glosado in resultados:
            faturado_f = float(faturado) if faturado else 0
            glosado_f = float(glosado) if glosado else 0
            taxa = (glosado_f / faturado_f * 100) if faturado_f > 0 else 0
            meses.append(
                {
                    "mes": mes,
                    "total_guias": total,
                    "valor_faturado": faturado_f,
                    "valor_glosado": glosado_f,
                    "taxa_glosa_pct": round(taxa, 1),
                }
            )

        return {"meses": meses}

    @staticmethod
    def _recomendar_acao_glosa(codigo_motivo: str, frequencia: int) -> str:
        """Gera recomendação de ação com base no padrão de glosa."""
        recomendacoes = {
            "MG001": "Revisar cobertura contratual antes do faturamento.",
            "MG002": "Implementar checagem de autorização prévia no fluxo de faturamento.",
            "MG003": "Validar quantidade contra protocolo antes de submissão.",
            "MG004": "Atualizar tabela TUSS e validar códigos automaticamente.",
            "MG005": "Implementar validação de compatibilidade CID x procedimento.",
            "MG007": "Implementar checagem de duplicidade antes do envio.",
            "MG008": "Alinhar valores com tabela contratual vigente.",
            "MG009": "Automatizar controle de prazo de apresentação.",
            "MG011": "Implementar validação de campos obrigatórios TISS.",
        }
        rec = recomendacoes.get(
            codigo_motivo,
            "Analisar causa raiz e implementar validação preventiva.",
        )
        if frequencia >= 10:
            rec += " URGENTE: Alta recorrência detectada - priorizar correção sistêmica."
        return rec
