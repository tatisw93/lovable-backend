"""
Registro central de agentes de auditoria.
Gerencia a criação e configuração de todos os agentes disponíveis.
"""
from agentes.base import AgenteBase
from agentes.agente_estrutura_tiss import AgenteEstruturaTISS
from agentes.agente_glosa import AgenteGlosaRecorrente
from agentes.agente_subfaturamento import AgenteSubfaturamento
from agentes.agente_conformidade import AgenteConformidadeANS
from agentes.agente_codificacao import AgenteCodificacao
from analise.motor_analise import MotorAnalise


# Definição de todos os agentes disponíveis
AGENTES_DISPONIVEIS = {
    "estrutura_tiss": {
        "classe": AgenteEstruturaTISS,
        "descricao": (
            "Valida conformidade estrutural das guias TISS: campos obrigatórios, "
            "formatos, consistência de dados."
        ),
        "nivel_primario": "tecnico",
    },
    "glosa_recorrente": {
        "classe": AgenteGlosaRecorrente,
        "descricao": (
            "Detecta padrões recorrentes de glosa, duplicidades e "
            "procedimentos com alta probabilidade de rejeição."
        ),
        "nivel_primario": "administrativo",
    },
    "subfaturamento": {
        "classe": AgenteSubfaturamento,
        "descricao": (
            "Detecta oportunidades de receita perdida: itens não faturados, "
            "quantidades incorretas, procedimentos complementares ausentes."
        ),
        "nivel_primario": "administrativo",
    },
    "conformidade_ans": {
        "classe": AgenteConformidadeANS,
        "descricao": (
            "Verifica conformidade com normas ANS: prazos, cobertura, "
            "autorização, compatibilidade clínica."
        ),
        "nivel_primario": "regulatorio",
    },
    "codificacao": {
        "classe": AgenteCodificacao,
        "descricao": (
            "Valida corretude de codificação TUSS, CID-10, CBHPM. "
            "Identifica erros de codificação que causam glosa."
        ),
        "nivel_primario": "tecnico",
    },
}


class RegistroAgentes:
    """Gerencia agentes de auditoria."""

    @staticmethod
    def listar_agentes() -> list[dict]:
        """Lista todos os agentes disponíveis."""
        return [
            {
                "tipo": tipo,
                "descricao": info["descricao"],
                "nivel_primario": info["nivel_primario"],
                "versao": info["classe"].versao if hasattr(info["classe"], "versao") else "1.0.0",
            }
            for tipo, info in AGENTES_DISPONIVEIS.items()
        ]

    @staticmethod
    def criar_motor(agentes_selecionados: list[str] = None) -> MotorAnalise:
        """
        Cria um motor de análise com os agentes selecionados.

        Args:
            agentes_selecionados: Lista de tipos de agente. Se None, todos.

        Returns:
            MotorAnalise configurado.
        """
        motor = MotorAnalise()

        tipos = agentes_selecionados or list(AGENTES_DISPONIVEIS.keys())
        for tipo in tipos:
            if tipo in AGENTES_DISPONIVEIS:
                agente = AGENTES_DISPONIVEIS[tipo]["classe"]()
                motor.registrar_agente(agente)

        return motor
