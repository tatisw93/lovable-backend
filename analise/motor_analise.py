"""
Motor de análise central.
Coordena a execução de todos os agentes de auditoria sobre os dados
ingeridos e normalizados.
"""
from typing import Optional

from models.base import db
from models.guia_tiss import GuiaTISS
from models.documento import Documento
from models.achado_auditoria import AchadoAuditoria


class MotorAnalise:
    """
    Motor central de análise que:
    1. Recebe dados normalizados de um documento
    2. Executa cada agente de auditoria registrado
    3. Coleta e persiste os achados
    4. Calcula estatísticas agregadas
    """

    def __init__(self):
        self._agentes = []

    def registrar_agente(self, agente):
        """Registra um agente de auditoria no motor."""
        self._agentes.append(agente)

    def analisar_documento(self, documento_id: int) -> dict:
        """
        Executa análise completa de um documento já ingerido.

        Args:
            documento_id: ID do documento no banco.

        Returns:
            dict com achados, estatísticas e resumo.
        """
        documento = Documento.query.get(documento_id)
        if not documento:
            return {"erro": f"Documento {documento_id} não encontrado."}

        guias = GuiaTISS.query.filter_by(documento_id=documento_id).all()
        if not guias:
            return {
                "documento_id": documento_id,
                "achados": [],
                "mensagem": "Nenhuma guia encontrada para análise.",
            }

        todos_achados = []
        for guia in guias:
            achados_guia = self._analisar_guia(guia, documento)
            todos_achados.extend(achados_guia)

        # Persistir achados
        for achado_dict in todos_achados:
            achado = AchadoAuditoria(
                guia_id=achado_dict.get("guia_id"),
                procedimento_id=achado_dict.get("procedimento_id"),
                documento_id=documento_id,
                agente_tipo=achado_dict["agente_tipo"],
                agente_versao=achado_dict.get("agente_versao", "1.0.0"),
                nivel=achado_dict["nivel"],
                confianca=achado_dict["confianca"],
                confianca_score=achado_dict.get("confianca_score"),
                titulo=achado_dict["titulo"],
                descricao=achado_dict["descricao"],
                evidencia=achado_dict.get("evidencia"),
                regra_referencia=achado_dict.get("regra_referencia"),
                norma_ans=achado_dict.get("norma_ans"),
                base_legal=achado_dict.get("base_legal"),
                impacto_valor=achado_dict.get("impacto_valor"),
                impacto_tipo=achado_dict.get("impacto_tipo"),
                acao_recomendada=achado_dict.get("acao_recomendada"),
            )
            db.session.add(achado)

        db.session.commit()

        # Calcular estatísticas
        resumo = self._gerar_resumo(todos_achados)

        return {
            "documento_id": documento_id,
            "total_guias_analisadas": len(guias),
            "total_achados": len(todos_achados),
            "achados": todos_achados,
            "resumo": resumo,
        }

    def _analisar_guia(self, guia: GuiaTISS, documento: Documento) -> list[dict]:
        """Executa todos os agentes sobre uma guia."""
        achados = []
        for agente in self._agentes:
            try:
                achados_agente = agente.analisar(guia)
                for achado in achados_agente:
                    achado["guia_id"] = guia.id
                achados.extend(achados_agente)
            except Exception as e:
                achados.append(
                    {
                        "guia_id": guia.id,
                        "agente_tipo": agente.tipo,
                        "nivel": "tecnico",
                        "confianca": "baixa",
                        "titulo": f"Erro no agente {agente.tipo}",
                        "descricao": f"Erro durante execução: {str(e)}",
                    }
                )
        return achados

    def _gerar_resumo(self, achados: list[dict]) -> dict:
        """Gera resumo estatístico dos achados."""
        if not achados:
            return {"total": 0}

        por_nivel = {}
        por_confianca = {}
        por_agente = {}
        impacto_total = 0.0

        for a in achados:
            nivel = a.get("nivel", "desconhecido")
            por_nivel[nivel] = por_nivel.get(nivel, 0) + 1

            conf = a.get("confianca", "desconhecido")
            por_confianca[conf] = por_confianca.get(conf, 0) + 1

            agente = a.get("agente_tipo", "desconhecido")
            por_agente[agente] = por_agente.get(agente, 0) + 1

            imp = a.get("impacto_valor")
            if imp:
                impacto_total += float(imp)

        return {
            "total": len(achados),
            "por_nivel": por_nivel,
            "por_confianca": por_confianca,
            "por_agente": por_agente,
            "impacto_financeiro_total_estimado": round(impacto_total, 2),
        }
