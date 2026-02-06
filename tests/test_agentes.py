"""
Testes dos agentes de auditoria.
"""
import unittest
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import date

from agentes.agente_estrutura_tiss import AgenteEstruturaTISS
from agentes.agente_codificacao import AgenteCodificacao
from agentes.registro_agentes import RegistroAgentes


class TestAgenteEstruturaTISS(unittest.TestCase):
    """Testes do agente de estrutura TISS."""

    def setUp(self):
        self.agente = AgenteEstruturaTISS()

    def test_tipo_agente(self):
        self.assertEqual(self.agente.tipo, "estrutura_tiss")

    def test_detecta_registro_ans_ausente(self):
        guia = MagicMock()
        guia.registro_ans = None
        guia.numero_guia_prestador = "G001"
        guia.tipo_guia = "guiaSP_SADT"
        guia.cid_principal = "J06"
        guia.data_atendimento = date.today()
        guia.data_fim_atendimento = None
        guia.beneficiario_id = 1
        guia.valor_total_informado = Decimal("150.00")
        guia.campos_ausentes = None
        guia.dados_brutos = {}
        guia.procedimentos = MagicMock()
        guia.procedimentos.count.return_value = 1

        achados = self.agente.analisar(guia)
        titulos = [a["titulo"] for a in achados]
        self.assertTrue(any("ANS" in t for t in titulos))

    def test_detecta_cid_ausente_sadt(self):
        guia = MagicMock()
        guia.registro_ans = "123456"
        guia.numero_guia_prestador = "G001"
        guia.tipo_guia = "guiaSP_SADT"
        guia.cid_principal = None
        guia.data_atendimento = date.today()
        guia.data_fim_atendimento = None
        guia.beneficiario_id = 1
        guia.valor_total_informado = Decimal("150.00")
        guia.campos_ausentes = None
        guia.dados_brutos = {}
        guia.procedimentos = MagicMock()
        guia.procedimentos.count.return_value = 1

        achados = self.agente.analisar(guia)
        titulos = [a["titulo"] for a in achados]
        self.assertTrue(any("CID" in t for t in titulos))

    def test_guia_sem_procedimentos(self):
        guia = MagicMock()
        guia.registro_ans = "123456"
        guia.numero_guia_prestador = "G001"
        guia.tipo_guia = "guiaSP_SADT"
        guia.cid_principal = "J06"
        guia.data_atendimento = date.today()
        guia.data_fim_atendimento = None
        guia.beneficiario_id = 1
        guia.valor_total_informado = Decimal("150.00")
        guia.campos_ausentes = None
        guia.dados_brutos = {}
        guia.procedimentos = MagicMock()
        guia.procedimentos.count.return_value = 0

        achados = self.agente.analisar(guia)
        titulos = [a["titulo"] for a in achados]
        self.assertTrue(any("procedimento" in t.lower() for t in titulos))


class TestAgenteCodificacao(unittest.TestCase):
    """Testes do agente de codificacao."""

    def setUp(self):
        self.agente = AgenteCodificacao()

    def test_tipo_agente(self):
        self.assertEqual(self.agente.tipo, "codificacao")

    def test_detecta_cid_invalido(self):
        guia = MagicMock()
        guia.cid_principal = "XYZ"
        guia.numero_guia_prestador = "G001"
        guia.tipo_guia = "guiaSP_SADT"
        guia.registro_ans = "123456"
        guia.procedimentos = MagicMock()
        guia.procedimentos.all.return_value = []

        achados = self.agente.analisar(guia)
        titulos = [a["titulo"] for a in achados]
        self.assertTrue(any("CID" in t for t in titulos))


class TestRegistroAgentes(unittest.TestCase):
    """Testes do registro de agentes."""

    def test_listar_agentes(self):
        agentes = RegistroAgentes.listar_agentes()
        self.assertTrue(len(agentes) >= 5)
        tipos = [a["tipo"] for a in agentes]
        self.assertIn("estrutura_tiss", tipos)
        self.assertIn("glosa_recorrente", tipos)
        self.assertIn("subfaturamento", tipos)
        self.assertIn("conformidade_ans", tipos)
        self.assertIn("codificacao", tipos)


class TestFormatoRespostaAgente(unittest.TestCase):
    """Verifica que todos os agentes retornam achados no formato padrao."""

    def test_formato_padrao(self):
        guia = MagicMock()
        guia.registro_ans = None
        guia.numero_guia_prestador = "G001"
        guia.tipo_guia = "guiaSP_SADT"
        guia.cid_principal = None
        guia.data_atendimento = date.today()
        guia.data_fim_atendimento = None
        guia.beneficiario_id = None
        guia.valor_total_informado = Decimal("100.00")
        guia.campos_ausentes = ["registroANS"]
        guia.dados_brutos = {}
        guia.procedimentos = MagicMock()
        guia.procedimentos.count.return_value = 0
        guia.procedimentos.all.return_value = []
        guia.glosas = MagicMock()
        guia.glosas.all.return_value = []

        agente = AgenteEstruturaTISS()
        achados = agente.analisar(guia)

        campos_obrigatorios = [
            "agente_tipo",
            "agente_versao",
            "nivel",
            "confianca",
            "confianca_score",
            "titulo",
            "descricao",
        ]

        for achado in achados:
            for campo in campos_obrigatorios:
                self.assertIn(
                    campo,
                    achado,
                    f"Campo obrigatorio '{campo}' ausente no achado: {achado.get('titulo')}",
                )
            self.assertIn(achado["nivel"], ["tecnico", "administrativo", "regulatorio"])
            self.assertIn(achado["confianca"], ["alta", "media", "baixa"])
            self.assertIsInstance(achado["confianca_score"], float)
            self.assertGreaterEqual(achado["confianca_score"], 0.0)
            self.assertLessEqual(achado["confianca_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
