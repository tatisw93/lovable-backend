"""
Agentes de auditoria médica.
Cada agente é especializado em um domínio de análise.
"""
from agentes.base import AgenteBase
from agentes.agente_estrutura_tiss import AgenteEstruturaTISS
from agentes.agente_glosa import AgenteGlosaRecorrente
from agentes.agente_subfaturamento import AgenteSubfaturamento
from agentes.agente_conformidade import AgenteConformidadeANS
from agentes.agente_codificacao import AgenteCodificacao
from agentes.registro_agentes import RegistroAgentes

__all__ = [
    "AgenteBase",
    "AgenteEstruturaTISS",
    "AgenteGlosaRecorrente",
    "AgenteSubfaturamento",
    "AgenteConformidadeANS",
    "AgenteCodificacao",
    "RegistroAgentes",
]
