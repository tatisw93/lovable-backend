"""
Testes da API REST.
"""
import unittest
import json
from io import BytesIO

from app import create_app
from models.base import db


class TestAPIBase(unittest.TestCase):
    """Classe base para testes de API."""

    def setUp(self):
        self.app = create_app("development")
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


class TestHealthCheck(TestAPIBase):
    """Testes do health check."""

    def test_index_html(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"AuditMed", resp.data)

    def test_health(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "ok")

    def test_upload_page(self):
        resp = self.client.get("/upload")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Upload", resp.data)

    def test_documentos_page(self):
        resp = self.client.get("/documentos")
        self.assertEqual(resp.status_code, 200)

    def test_achados_page(self):
        resp = self.client.get("/achados")
        self.assertEqual(resp.status_code, 200)

    def test_padroes_page(self):
        resp = self.client.get("/padroes")
        self.assertEqual(resp.status_code, 200)


class TestIngestaoAPI(TestAPIBase):
    """Testes da API de ingestao."""

    def test_upload_sem_arquivo(self):
        resp = self.client.post("/api/v1/ingestao/upload")
        self.assertEqual(resp.status_code, 400)

    def test_upload_tipo_invalido(self):
        data = {"arquivo": (BytesIO(b"conteudo"), "test.exe")}
        resp = self.client.post(
            "/api/v1/ingestao/upload",
            data=data,
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 400)

    def test_upload_xml_valido(self):
        xml = b"""<?xml version="1.0"?>
        <mensagemTISS>
          <guiaSP_SADT>
            <registroANS>123456</registroANS>
            <numeroGuiaPrestador>G001</numeroGuiaPrestador>
            <procedimentoExecutado>
              <codigoProcedimento>10101012</codigoProcedimento>
              <quantidadeExecutada>1</quantidadeExecutada>
              <valorUnitario>150.00</valorUnitario>
              <valorTotal>150.00</valorTotal>
            </procedimentoExecutado>
            <valorTotalGeral>150.00</valorTotalGeral>
          </guiaSP_SADT>
        </mensagemTISS>"""

        data = {"arquivo": (BytesIO(xml), "guia.xml")}
        resp = self.client.post(
            "/api/v1/ingestao/upload",
            data=data,
            content_type="multipart/form-data",
        )
        self.assertIn(resp.status_code, [200, 422])

    def test_listar_documentos_vazio(self):
        resp = self.client.get("/api/v1/ingestao/documentos")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["documentos"], [])

    def test_upload_csv(self):
        csv = b"codigo_tuss;descricao;quantidade;valor_unitario;valor_total\n10101012;Consulta;1;150.00;150.00\n"
        data = {"arquivo": (BytesIO(csv), "procedimentos.csv")}
        resp = self.client.post(
            "/api/v1/ingestao/upload",
            data=data,
            content_type="multipart/form-data",
        )
        self.assertIn(resp.status_code, [200, 422])


class TestAgentesAPI(TestAPIBase):
    """Testes da API de agentes."""

    def test_listar_agentes(self):
        resp = self.client.get("/api/v1/agentes/")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["total_agentes"] >= 5)

    def test_detalhe_agente(self):
        resp = self.client.get("/api/v1/agentes/estrutura_tiss")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["tipo"], "estrutura_tiss")
        self.assertIn("formato_resposta", data)

    def test_agente_inexistente(self):
        resp = self.client.get("/api/v1/agentes/inexistente")
        self.assertEqual(resp.status_code, 404)


class TestAnaliseAPI(TestAPIBase):
    """Testes da API de analise."""

    def test_listar_achados_vazio(self):
        resp = self.client.get("/api/v1/analise/achados")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["achados"], [])

    def test_padroes_glosa_vazio(self):
        resp = self.client.get("/api/v1/analise/padroes/glosa")
        self.assertEqual(resp.status_code, 200)

    def test_padroes_temporais_vazio(self):
        resp = self.client.get("/api/v1/analise/padroes/temporal")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
