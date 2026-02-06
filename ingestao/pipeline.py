"""
Pipeline principal de ingestão.
Orquestra: recepção → parsing → normalização → enriquecimento → persistência.
"""
import hashlib
import json
import os
from decimal import Decimal
from typing import Optional

from models.base import db
from models.documento import Documento
from models.guia_tiss import GuiaTISS
from models.procedimento import Procedimento
from models.prestador import Prestador
from models.operadora import Operadora
from models.glosa import Glosa
from models.beneficiario import Beneficiario
from dominio.constantes import StatusDocumento
from ingestao.parsers import obter_parser
from ingestao.normalizacao.normalizador import Normalizador
from ingestao.enriquecimento.enriquecedor import Enriquecedor


class PipelineIngestao:
    """
    Pipeline completo de ingestão de documentos.

    Fluxo:
    1. Recepção e deduplicação (hash SHA-256)
    2. Parsing por tipo de arquivo
    3. Normalização e validação
    4. Enriquecimento com dados derivados
    5. Persistência no banco de dados
    """

    def __init__(self):
        self.normalizador = Normalizador()
        self.enriquecedor = Enriquecedor()

    def processar_arquivo(
        self, conteudo: bytes, nome_arquivo: str, tipo_arquivo: Optional[str] = None
    ) -> dict:
        """
        Processa um arquivo completo pelo pipeline.

        Args:
            conteudo: Bytes do arquivo.
            nome_arquivo: Nome original do arquivo.
            tipo_arquivo: Tipo/extensão (se None, será inferido).

        Returns:
            dict com resultado do processamento.
        """
        if not tipo_arquivo:
            tipo_arquivo = self._inferir_tipo(nome_arquivo)

        # 1. Calcular hash e verificar duplicatas
        hash_conteudo = hashlib.sha256(conteudo).hexdigest()
        doc_existente = Documento.query.filter_by(hash_conteudo=hash_conteudo).first()
        if doc_existente:
            return {
                "status": "duplicado",
                "documento_id": doc_existente.id,
                "mensagem": f"Documento já processado anteriormente (ID: {doc_existente.id}).",
            }

        # 2. Criar registro do documento
        documento = Documento(
            nome_arquivo=nome_arquivo,
            tipo_arquivo=tipo_arquivo,
            tamanho_bytes=len(conteudo),
            hash_conteudo=hash_conteudo,
            status=StatusDocumento.PROCESSANDO.value,
        )
        db.session.add(documento)
        db.session.flush()  # Para obter o ID

        try:
            # 3. Parsing
            parser = obter_parser(tipo_arquivo)
            resultado_parsing = parser.parse(conteudo, nome_arquivo)

            if resultado_parsing.erros:
                documento.status = StatusDocumento.ERRO.value
                documento.erro_processamento = "; ".join(resultado_parsing.erros)
                db.session.commit()
                return {
                    "status": "erro_parsing",
                    "documento_id": documento.id,
                    "erros": resultado_parsing.erros,
                }

            # 4. Normalização
            resultado_norm = self.normalizador.normalizar(resultado_parsing)

            # 5. Enriquecimento
            dados_enriquecidos = self.enriquecedor.enriquecer(
                resultado_norm.dados_normalizados
            )

            # 6. Persistência
            resultado_persistencia = self._persistir(documento, dados_enriquecidos)

            # 7. Atualizar documento
            documento.status = StatusDocumento.CONCLUIDO.value
            documento.metadados_extraidos = self._json_safe({
                "estatisticas": resultado_norm.estatisticas,
                "alertas": resultado_norm.alertas[:50],
                "erros_validacao": resultado_norm.erros_validacao[:50],
            })
            db.session.commit()

            return {
                "status": "sucesso",
                "documento_id": documento.id,
                "estatisticas": resultado_norm.estatisticas,
                "alertas": resultado_norm.alertas,
                "erros_validacao": resultado_norm.erros_validacao,
                "alertas_enriquecimento": dados_enriquecidos.get(
                    "alertas_enriquecimento", []
                ),
                **resultado_persistencia,
            }

        except Exception as e:
            documento.status = StatusDocumento.ERRO.value
            documento.erro_processamento = str(e)
            db.session.commit()
            return {
                "status": "erro",
                "documento_id": documento.id,
                "erro": str(e),
            }

    def _persistir(self, documento: Documento, dados: dict) -> dict:
        """Persiste os dados extraídos e normalizados no banco."""
        contadores = {
            "guias_criadas": 0,
            "procedimentos_criados": 0,
            "glosas_criadas": 0,
            "prestadores_criados": 0,
            "beneficiarios_criados": 0,
        }

        # Cache de entidades criadas para relacionamentos
        mapa_guias = {}  # numero_guia -> GuiaTISS
        mapa_prestadores = {}  # cnes -> Prestador
        mapa_beneficiarios = {}  # carteirinha -> Beneficiario

        # Persistir prestadores
        for prest_data in dados.get("prestadores", []):
            cnes = prest_data.get("cnes")
            if not cnes or cnes in mapa_prestadores:
                continue
            prestador = Prestador.query.filter_by(cnes=cnes).first()
            if not prestador:
                prestador = Prestador(
                    cnes=cnes,
                    cnpj=prest_data.get("cnpj"),
                    razao_social=prest_data.get("razao_social"),
                )
                db.session.add(prestador)
                db.session.flush()
                contadores["prestadores_criados"] += 1
            mapa_prestadores[cnes] = prestador

        # Persistir beneficiários
        for benef_data in dados.get("beneficiarios", []):
            cart = benef_data.get("numero_carteirinha")
            if not cart or cart in mapa_beneficiarios:
                continue
            beneficiario = Beneficiario.query.filter_by(
                numero_carteirinha=cart
            ).first()
            if not beneficiario:
                beneficiario = Beneficiario(
                    numero_carteirinha=cart,
                    nome=benef_data.get("nome"),
                    cns=benef_data.get("cns"),
                )
                db.session.add(beneficiario)
                db.session.flush()
                contadores["beneficiarios_criados"] += 1
            mapa_beneficiarios[cart] = beneficiario

        # Persistir guias
        for guia_data in dados.get("guias", []):
            num_guia = guia_data.get("numero_guia_prestador")
            guia = GuiaTISS(
                documento_id=documento.id,
                tipo_guia=guia_data.get("tipo_guia", ""),
                numero_guia_prestador=num_guia,
                numero_guia_operadora=guia_data.get("numero_guia_operadora"),
                numero_autorizacao=guia_data.get("numero_autorizacao"),
                registro_ans=guia_data.get("registro_ans"),
                data_atendimento=self._parse_date_safe(
                    guia_data.get("data_atendimento")
                ),
                data_fim_atendimento=self._parse_date_safe(
                    guia_data.get("data_fim_atendimento")
                ),
                tipo_atendimento=guia_data.get("tipo_atendimento"),
                carater_atendimento=guia_data.get("carater_atendimento"),
                cid_principal=guia_data.get("cid_principal"),
                valor_total_informado=guia_data.get("valor_total_informado"),
                dados_brutos=self._json_safe(guia_data),
            )
            db.session.add(guia)
            db.session.flush()
            contadores["guias_criadas"] += 1
            if num_guia:
                mapa_guias[num_guia] = guia

        # Persistir procedimentos
        for proc_data in dados.get("procedimentos", []):
            ref_guia = proc_data.get("numero_guia_ref")
            guia_obj = mapa_guias.get(ref_guia)
            if not guia_obj:
                # Associar à primeira guia se houver
                guia_obj = next(iter(mapa_guias.values()), None)

            proc = Procedimento(
                guia_id=guia_obj.id if guia_obj else None,
                codigo_tuss=proc_data.get("codigo_tuss", ""),
                descricao=proc_data.get("descricao"),
                tabela_referencia=proc_data.get("tabela_referencia"),
                quantidade_realizada=self._safe_int(
                    proc_data.get("quantidade_realizada")
                ),
                valor_unitario=proc_data.get("valor_unitario"),
                valor_total=proc_data.get("valor_total"),
                data_realizacao=self._parse_date_safe(
                    proc_data.get("data_realizacao")
                ),
                profissional_nome=proc_data.get("profissional_nome"),
                profissional_conselho=proc_data.get("profissional_conselho"),
                profissional_numero=proc_data.get("profissional_numero"),
                profissional_uf=proc_data.get("profissional_uf"),
                profissional_cbos=proc_data.get("profissional_cbos"),
            )
            # guia_id is required - skip if no guia
            if proc.guia_id:
                db.session.add(proc)
                contadores["procedimentos_criados"] += 1

        # Persistir glosas
        for glosa_data in dados.get("glosas", []):
            ref_guia = glosa_data.get("numero_guia")
            guia_obj = mapa_guias.get(ref_guia)
            if not guia_obj:
                guia_obj = next(iter(mapa_guias.values()), None)

            if guia_obj:
                glosa = Glosa(
                    guia_id=guia_obj.id,
                    codigo_motivo=glosa_data.get("codigo_motivo"),
                    descricao_motivo=glosa_data.get("descricao_motivo"),
                    valor_glosado=glosa_data.get("valor_glosado") or 0,
                    valor_original=glosa_data.get("valor_original"),
                )
                db.session.add(glosa)
                contadores["glosas_criadas"] += 1

        db.session.flush()
        return contadores

    @staticmethod
    def _json_safe(obj):
        """Convert Decimal values to float for JSON serialization."""
        if isinstance(obj, dict):
            return {k: PipelineIngestao._json_safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [PipelineIngestao._json_safe(v) for v in obj]
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    @staticmethod
    def _inferir_tipo(nome_arquivo: str) -> str:
        """Infere o tipo do arquivo pela extensão."""
        ext = nome_arquivo.rsplit(".", 1)[-1].lower() if "." in nome_arquivo else ""
        return ext or "txt"

    @staticmethod
    def _parse_date_safe(valor):
        """Parse seguro de data."""
        if valor is None:
            return None
        from datetime import datetime, date

        if isinstance(valor, (date, datetime)):
            return valor
        try:
            return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(valor):
        """Conversão segura para inteiro."""
        if valor is None:
            return None
        try:
            return int(float(str(valor)))
        except (ValueError, TypeError):
            return None
