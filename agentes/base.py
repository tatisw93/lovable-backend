"""
Classe base para todos os agentes de auditoria.
Define o contrato que cada agente deve implementar.
"""
from abc import ABC, abstractmethod
from typing import Any

from models.guia_tiss import GuiaTISS
from dominio.constantes import NivelAchado, NivelConfianca


class AgenteBase(ABC):
    """
    Interface base para agentes de auditoria médica.

    Cada agente deve:
    1. Analisar uma guia TISS e seus procedimentos
    2. Retornar uma lista de achados padronizados
    3. Cada achado deve incluir:
       - Nível (técnico, administrativo, regulatório)
       - Confiança (alta, média, baixa)
       - Justificativa com referência regulatória
       - Impacto financeiro estimado (quando possível)
       - Ação recomendada
    """

    tipo: str = "base"
    versao: str = "1.0.0"
    descricao: str = ""

    @abstractmethod
    def analisar(self, guia: GuiaTISS) -> list[dict]:
        """
        Analisa uma guia TISS e retorna achados de auditoria.

        Args:
            guia: Objeto GuiaTISS com procedimentos carregados.

        Returns:
            Lista de dicts no formato padrão de achado.
        """
        ...

    def _criar_achado(
        self,
        titulo: str,
        descricao: str,
        nivel: str,
        confianca: str,
        confianca_score: float,
        regra_referencia: str = "",
        norma_ans: str = "",
        base_legal: str = "",
        impacto_valor: float = None,
        impacto_tipo: str = "",
        acao_recomendada: str = "",
        evidencia: str = "",
        procedimento_id: int = None,
    ) -> dict:
        """
        Cria um achado no formato padrão.

        Formato de resposta dos agentes — pronto para uso em produto:
        {
            "agente_tipo": str,
            "agente_versao": str,
            "nivel": "tecnico" | "administrativo" | "regulatorio",
            "confianca": "alta" | "media" | "baixa",
            "confianca_score": float (0.0 - 1.0),
            "titulo": str,
            "descricao": str,
            "evidencia": str,
            "regra_referencia": str,
            "norma_ans": str,
            "base_legal": str,
            "impacto_valor": float | None,
            "impacto_tipo": str,
            "acao_recomendada": str,
            "procedimento_id": int | None,
        }
        """
        return {
            "agente_tipo": self.tipo,
            "agente_versao": self.versao,
            "nivel": nivel,
            "confianca": confianca,
            "confianca_score": confianca_score,
            "titulo": titulo,
            "descricao": descricao,
            "evidencia": evidencia,
            "regra_referencia": regra_referencia,
            "norma_ans": norma_ans,
            "base_legal": base_legal,
            "impacto_valor": impacto_valor,
            "impacto_tipo": impacto_tipo,
            "acao_recomendada": acao_recomendada,
            "procedimento_id": procedimento_id,
        }
