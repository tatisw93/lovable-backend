"""
Calculadora de impacto financeiro.
Estima o impacto monetário de achados de auditoria.
"""
from decimal import Decimal
from typing import Optional

from models.base import db
from models.guia_tiss import GuiaTISS
from models.procedimento import Procedimento
from models.glosa import Glosa


class CalculadoraImpacto:
    """
    Calcula impacto financeiro de diferentes cenários:
    - Subfaturamento (itens não cobrados)
    - Glosas indevidas (passíveis de recurso)
    - Erros de codificação (valor incorreto)
    - Duplicidade (cobranças duplicadas)
    """

    def calcular_subfaturamento(self, guia: GuiaTISS) -> dict:
        """
        Calcula potencial subfaturamento de uma guia.
        Verifica se existem procedimentos que deveriam ter sido cobrados
        mas não constam na guia.
        """
        procedimentos = guia.procedimentos.all()
        achados = []
        valor_potencial = Decimal("0")

        for proc in procedimentos:
            # Verificar quantidade zerada ou ausente
            if not proc.quantidade_realizada or proc.quantidade_realizada <= 0:
                if proc.valor_unitario:
                    impacto = proc.valor_unitario  # Mínimo de 1 unidade
                    achados.append(
                        {
                            "tipo": "quantidade_zerada",
                            "procedimento_id": proc.id,
                            "codigo_tuss": proc.codigo_tuss,
                            "impacto_estimado": float(impacto),
                            "descricao": (
                                f"Procedimento {proc.codigo_tuss} sem quantidade informada. "
                                "Possível subfaturamento."
                            ),
                        }
                    )
                    valor_potencial += impacto

            # Verificar valor unitário zerado
            if proc.quantidade_realizada and (
                not proc.valor_unitario or proc.valor_unitario <= 0
            ):
                achados.append(
                    {
                        "tipo": "valor_zerado",
                        "procedimento_id": proc.id,
                        "codigo_tuss": proc.codigo_tuss,
                        "descricao": (
                            f"Procedimento {proc.codigo_tuss} com valor unitário "
                            "zerado ou ausente."
                        ),
                    }
                )

            # Verificar valor total inconsistente
            if (
                proc.valor_unitario
                and proc.quantidade_realizada
                and proc.valor_total
            ):
                esperado = proc.valor_unitario * proc.quantidade_realizada
                if proc.valor_total < esperado:
                    diferenca = esperado - proc.valor_total
                    achados.append(
                        {
                            "tipo": "valor_total_menor",
                            "procedimento_id": proc.id,
                            "codigo_tuss": proc.codigo_tuss,
                            "valor_informado": float(proc.valor_total),
                            "valor_esperado": float(esperado),
                            "impacto_estimado": float(diferenca),
                            "descricao": (
                                f"Valor total informado (R${proc.valor_total}) menor "
                                f"que o calculado (R${esperado})."
                            ),
                        }
                    )
                    valor_potencial += diferenca

        return {
            "achados": achados,
            "valor_potencial_subfaturamento": float(valor_potencial),
        }

    def calcular_glosas_recuperaveis(
        self, registro_ans: Optional[str] = None
    ) -> dict:
        """
        Identifica glosas potencialmente recuperáveis via recurso.
        """
        query = Glosa.query.filter(
            Glosa.recurso_apresentado == False,
            Glosa.valor_glosado > 0,
        )

        if registro_ans:
            query = query.join(GuiaTISS).filter(
                GuiaTISS.registro_ans == registro_ans
            )

        glosas = query.all()
        total_recuperavel = Decimal("0")
        glosas_analisadas = []

        for glosa in glosas:
            probabilidade = self._estimar_probabilidade_recurso(glosa)
            valor_esperado = (
                glosa.valor_glosado * Decimal(str(probabilidade))
                if glosa.valor_glosado
                else Decimal("0")
            )

            glosas_analisadas.append(
                {
                    "glosa_id": glosa.id,
                    "codigo_motivo": glosa.codigo_motivo,
                    "valor_glosado": float(glosa.valor_glosado or 0),
                    "probabilidade_recuperacao": probabilidade,
                    "valor_esperado_recuperacao": float(valor_esperado),
                }
            )
            total_recuperavel += valor_esperado

        return {
            "total_glosas_analisadas": len(glosas_analisadas),
            "valor_total_glosado": sum(
                float(g.valor_glosado or 0) for g in glosas
            ),
            "valor_esperado_recuperacao": float(total_recuperavel),
            "glosas": glosas_analisadas[:50],
        }

    def _estimar_probabilidade_recurso(self, glosa: Glosa) -> float:
        """
        Estima probabilidade de sucesso em recurso de glosa.
        Base: histórico de recursos anteriores com mesmo código de motivo.
        """
        if not glosa.codigo_motivo:
            return 0.3  # Sem motivo específico, probabilidade baixa

        # Consultar histórico de recursos com mesmo motivo
        historico = (
            Glosa.query.filter(
                Glosa.codigo_motivo == glosa.codigo_motivo,
                Glosa.recurso_apresentado == True,
                Glosa.resultado_recurso.isnot(None),
            )
            .all()
        )

        if not historico:
            # Sem histórico, usar probabilidade base por tipo de motivo
            return self._probabilidade_base(glosa.codigo_motivo)

        aceitos = sum(
            1 for g in historico if g.resultado_recurso == "aceito"
        )
        parciais = sum(
            1 for g in historico if g.resultado_recurso == "parcial"
        )

        return round((aceitos + parciais * 0.5) / len(historico), 2)

    @staticmethod
    def _probabilidade_base(codigo_motivo: str) -> float:
        """Probabilidade base de sucesso por tipo de motivo de glosa."""
        # Glosas administrativas têm maior chance de reversão
        altas = {"MG011", "MG012", "MG017", "MG018"}
        medias = {"MG002", "MG003", "MG008", "MG009", "MG013"}
        baixas = {"MG001", "MG005", "MG006", "MG019"}

        if codigo_motivo in altas:
            return 0.7
        if codigo_motivo in medias:
            return 0.5
        if codigo_motivo in baixas:
            return 0.2
        return 0.4
