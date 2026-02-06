"""
Testes dos parsers de documentos.
"""
import unittest

from ingestao.parsers.tiss_xml import TissXmlParser
from ingestao.parsers.texto_parser import TextoParser
from ingestao.parsers.planilha_parser import PlanilhaParser


class TestTissXmlParser(unittest.TestCase):
    """Testes do parser XML TISS."""

    def setUp(self):
        self.parser = TissXmlParser()

    def test_parse_xml_invalido(self):
        resultado = self.parser.parse(b"<invalido>", "test.xml")
        self.assertTrue(len(resultado.erros) > 0)

    def test_parse_xml_vazio(self):
        resultado = self.parser.parse(b"<root></root>", "test.xml")
        self.assertEqual(len(resultado.guias), 0)
        self.assertTrue(len(resultado.avisos) > 0)

    def test_parse_guia_sadt_basica(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <mensagemTISS>
          <cabecalho>
            <versaoPadrao>4.01.00</versaoPadrao>
          </cabecalho>
          <prestadorParaOperadora>
            <loteGuias>
              <guiaSP_SADT>
                <registroANS>123456</registroANS>
                <numeroGuiaPrestador>G00001</numeroGuiaPrestador>
                <dadosBeneficiario>
                  <numeroCarteira>9999999</numeroCarteira>
                  <nomeBeneficiario>Paciente Teste</nomeBeneficiario>
                </dadosBeneficiario>
                <procedimentoExecutado>
                  <codigoProcedimento>10101012</codigoProcedimento>
                  <descricaoProcedimento>Consulta em consultorio</descricaoProcedimento>
                  <quantidadeExecutada>1</quantidadeExecutada>
                  <valorUnitario>150.00</valorUnitario>
                  <valorTotal>150.00</valorTotal>
                </procedimentoExecutado>
                <diagnosticoCID>J06</diagnosticoCID>
                <valorTotalGeral>150.00</valorTotalGeral>
              </guiaSP_SADT>
            </loteGuias>
          </prestadorParaOperadora>
        </mensagemTISS>
        """
        resultado = self.parser.parse(xml, "tiss_test.xml")
        self.assertEqual(len(resultado.erros), 0)
        self.assertTrue(len(resultado.guias) > 0)
        self.assertEqual(resultado.guias[0]["registro_ans"], "123456")
        self.assertTrue(len(resultado.procedimentos) > 0)
        self.assertEqual(resultado.procedimentos[0]["codigo_tuss"], "10101012")

    def test_tipos_suportados(self):
        self.assertEqual(self.parser.tipos_suportados(), ["xml"])


class TestTextoParser(unittest.TestCase):
    """Testes do parser de texto."""

    def setUp(self):
        self.parser = TextoParser()

    def test_extrair_codigos_tuss(self):
        texto = b"Procedimento 10101012 - Consulta realizado em 01/01/2024"
        resultado = self.parser.parse(texto, "test.txt")
        self.assertIn("10101012", resultado.metadados.get("codigos_tuss", []))

    def test_extrair_cid(self):
        texto = b"Diagnostico: J06.9 - IVAS"
        resultado = self.parser.parse(texto, "test.txt")
        codigos_cid = resultado.metadados.get("codigos_cid", [])
        self.assertTrue(any("J06" in c for c in codigos_cid))

    def test_extrair_guias(self):
        texto = b"Referente a guia: 12345678901234"
        resultado = self.parser.parse(texto, "test.txt")
        self.assertTrue(len(resultado.guias) > 0)

    def test_texto_sem_dados_saude(self):
        texto = b"Este texto nao contem dados de saude relevantes para analise."
        resultado = self.parser.parse(texto, "test.txt")
        self.assertTrue(len(resultado.avisos) > 0)


class TestPlanilhaParser(unittest.TestCase):
    """Testes do parser de planilhas."""

    def setUp(self):
        self.parser = PlanilhaParser()

    def test_parse_csv_procedimentos(self):
        csv = (
            b"codigo_tuss;descricao;quantidade;valor_unitario;valor_total\n"
            b"10101012;Consulta;1;150.00;150.00\n"
            b"40301630;Hemograma;1;25.00;25.00\n"
        )
        resultado = self.parser.parse(csv, "test.csv")
        self.assertTrue(len(resultado.procedimentos) > 0)

    def test_parse_csv_vazio(self):
        csv = b""
        resultado = self.parser.parse(csv, "test.csv")
        self.assertTrue(
            len(resultado.avisos) > 0 or len(resultado.procedimentos) == 0
        )

    def test_detectar_delimitador_ponto_virgula(self):
        self.assertEqual(
            self.parser._detectar_delimitador("a;b;c;d\n1;2;3;4"), ";"
        )

    def test_detectar_delimitador_virgula(self):
        self.assertEqual(
            self.parser._detectar_delimitador("a,b,c,d\n1,2,3,4"), ","
        )


if __name__ == "__main__":
    unittest.main()
