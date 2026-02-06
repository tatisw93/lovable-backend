"""
Testes dos validadores TUSS, CID e TISS.
"""
import unittest

from ingestao.normalizacao.tuss_validator import TussValidator
from ingestao.normalizacao.cid_validator import CidValidator
from ingestao.normalizacao.tiss_validator import TissValidator


class TestTussValidator(unittest.TestCase):
    """Testes do validador TUSS."""

    def setUp(self):
        self.validator = TussValidator()

    def test_codigo_valido_consulta(self):
        resultado = self.validator.validar("10101012")
        self.assertTrue(resultado["valido"])
        self.assertIn("Consultas", resultado["grupo"])

    def test_codigo_valido_procedimento(self):
        resultado = self.validator.validar("20101015")
        self.assertTrue(resultado["valido"])

    def test_codigo_invalido_formato(self):
        resultado = self.validator.validar("12345")
        self.assertFalse(resultado["valido"])

    def test_codigo_invalido_letras(self):
        resultado = self.validator.validar("ABCD1234")
        self.assertFalse(resultado["valido"])

    def test_codigo_atencao(self):
        resultado = self.validator.validar("10101012")
        self.assertIn("atencao", resultado)

    def test_obter_grupo(self):
        self.assertEqual(self.validator.obter_grupo("10101012"), "Consultas")
        self.assertEqual(self.validator.obter_grupo("XXXXX"), "Desconhecido")


class TestCidValidator(unittest.TestCase):
    """Testes do validador CID-10."""

    def setUp(self):
        self.validator = CidValidator()

    def test_cid_valido_simples(self):
        self.assertTrue(self.validator.validar("J06"))

    def test_cid_valido_com_subcategoria(self):
        self.assertTrue(self.validator.validar("J06.9"))

    def test_cid_invalido(self):
        self.assertFalse(self.validator.validar("123"))

    def test_normalizar_sem_ponto(self):
        self.assertEqual(self.validator.normalizar("J069"), "J06.9")

    def test_normalizar_minusculo(self):
        self.assertEqual(self.validator.normalizar("j06"), "J06")

    def test_obter_capitulo(self):
        capitulo = self.validator.obter_capitulo("I21")
        self.assertIn("circulat", capitulo.lower())

    def test_verificar_atencao(self):
        alerta = self.validator.verificar_atencao("R69")
        self.assertIsNotNone(alerta)


class TestTissValidator(unittest.TestCase):
    """Testes do validador TISS."""

    def setUp(self):
        self.validator = TissValidator()

    def test_guia_sem_registro_ans(self):
        guia = {"tipo_guia": "guiaSP_SADT", "numero_guia_prestador": "G001"}
        erros = self.validator.validar_guia(guia)
        campos_erro = [e["campo"] for e in erros]
        self.assertIn("registroANS", campos_erro)

    def test_guia_completa(self):
        guia = {
            "tipo_guia": "guiaConsulta",
            "numero_guia_prestador": "G001",
            "registro_ans": "123456",
            "data_atendimento": "2024-12-01",
            "prestador_id": 1,
        }
        erros = self.validator.validar_guia(guia)
        campos_erro = [e["campo"] for e in erros]
        self.assertNotIn("registroANS", campos_erro)

    def test_registro_ans_invalido(self):
        guia = {
            "tipo_guia": "guiaSP_SADT",
            "numero_guia_prestador": "G001",
            "registro_ans": "12AB",
        }
        erros = self.validator.validar_guia(guia)
        tem_erro_ans = any("registroANS" in e.get("campo", "") for e in erros)
        self.assertTrue(tem_erro_ans)


if __name__ == "__main__":
    unittest.main()
