"""
Parser para documentos PDF.
Extrai texto e tenta identificar estruturas de dados de saúde:
- Relatórios de glosa
- Demonstrativos de pagamento
- Contratos
- Laudos e relatórios médicos
"""
import re
from typing import Optional

from ingestao.parsers.base import BaseParser, ResultadoParsing


class PdfParser(BaseParser):
    """Parser para documentos PDF usando pdfplumber."""

    def tipos_suportados(self) -> list[str]:
        return ["pdf"]

    def parse(self, conteudo: bytes, nome_arquivo: str) -> ResultadoParsing:
        resultado = ResultadoParsing()
        resultado.tipo_documento = "pdf"

        try:
            import pdfplumber
            import io

            with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
                texto_completo = ""
                tabelas_encontradas = []

                for pagina in pdf.pages:
                    texto = pagina.extract_text() or ""
                    texto_completo += texto + "\n"

                    # Extrair tabelas de cada página
                    for tabela in pagina.extract_tables() or []:
                        tabelas_encontradas.append(tabela)

                resultado.metadados["total_paginas"] = len(pdf.pages)
                resultado.metadados["texto_extraido"] = texto_completo[:10000]

                # Tentar identificar o tipo de documento
                tipo_doc = self._identificar_tipo_documento(texto_completo)
                resultado.metadados["tipo_documento_detectado"] = tipo_doc

                # Extrair dados conforme o tipo
                if tipo_doc == "demonstrativo_glosa":
                    self._extrair_glosas_pdf(
                        texto_completo, tabelas_encontradas, resultado
                    )
                elif tipo_doc == "demonstrativo_pagamento":
                    self._extrair_pagamentos_pdf(
                        texto_completo, tabelas_encontradas, resultado
                    )
                elif tipo_doc == "relatorio_faturamento":
                    self._extrair_faturamento_pdf(
                        texto_completo, tabelas_encontradas, resultado
                    )
                else:
                    # Extrair tudo que for possível
                    self._extrair_dados_genericos(
                        texto_completo, tabelas_encontradas, resultado
                    )

        except ImportError:
            resultado.erros.append(
                "Biblioteca pdfplumber não instalada. "
                "Execute: pip install pdfplumber"
            )
        except Exception as e:
            resultado.erros.append(f"Erro ao processar PDF: {str(e)}")

        return resultado

    def _identificar_tipo_documento(self, texto: str) -> str:
        """Identifica o tipo de documento PDF com base no conteúdo."""
        texto_lower = texto.lower()

        if any(
            termo in texto_lower
            for termo in ["glosa", "demonstrativo de glosa", "recurso de glosa"]
        ):
            return "demonstrativo_glosa"

        if any(
            termo in texto_lower
            for termo in [
                "demonstrativo de pagamento",
                "pagamento ao prestador",
                "extrato de pagamento",
            ]
        ):
            return "demonstrativo_pagamento"

        if any(
            termo in texto_lower
            for termo in [
                "faturamento",
                "conta hospitalar",
                "conta médica",
                "resumo de faturamento",
            ]
        ):
            return "relatorio_faturamento"

        if any(
            termo in texto_lower
            for termo in ["contrato", "aditivo contratual", "tabela de preços"]
        ):
            return "contrato"

        return "generico"

    def _extrair_glosas_pdf(
        self,
        texto: str,
        tabelas: list,
        resultado: ResultadoParsing,
    ):
        """Extrai informações de glosa de um PDF de demonstrativo."""
        # Regex para padrões comuns em demonstrativos de glosa
        padrao_guia = re.compile(
            r"(?:guia|nº\s*guia)[:\s]*(\d{8,20})", re.IGNORECASE
        )
        padrao_valor_glosa = re.compile(
            r"(?:valor\s*glosado|glosa)[:\s]*R?\$?\s*([\d.,]+)", re.IGNORECASE
        )
        padrao_motivo = re.compile(
            r"(?:motivo|justificativa)[:\s]*(.+?)(?:\n|$)", re.IGNORECASE
        )
        padrao_tuss = re.compile(r"\b(\d{8})\b")  # Código TUSS = 8 dígitos

        guias_encontradas = padrao_guia.findall(texto)
        for num_guia in guias_encontradas:
            resultado.guias.append(
                {"numero_guia_prestador": num_guia, "tipo_guia": "pdf_glosa"}
            )

        # Extrair glosas de tabelas
        for tabela in tabelas:
            if not tabela or len(tabela) < 2:
                continue
            cabecalho = [str(c).lower() if c else "" for c in tabela[0]]
            for linha in tabela[1:]:
                glosa_dict = self._mapear_linha_glosa(cabecalho, linha)
                if glosa_dict:
                    resultado.glosas.append(glosa_dict)

        # Extrair valores do texto
        valores_glosa = padrao_valor_glosa.findall(texto)
        motivos = padrao_motivo.findall(texto)
        codigos_tuss = padrao_tuss.findall(texto)

        resultado.metadados["valores_glosa_texto"] = valores_glosa[:20]
        resultado.metadados["motivos_texto"] = motivos[:20]
        resultado.metadados["codigos_tuss_texto"] = list(set(codigos_tuss))[:50]

    def _extrair_pagamentos_pdf(
        self,
        texto: str,
        tabelas: list,
        resultado: ResultadoParsing,
    ):
        """Extrai informações de pagamento de um demonstrativo."""
        padrao_valor_pago = re.compile(
            r"(?:valor\s*pago|total\s*pago)[:\s]*R?\$?\s*([\d.,]+)",
            re.IGNORECASE,
        )
        padrao_valor_apresentado = re.compile(
            r"(?:valor\s*apresentado|total\s*apresentado)[:\s]*R?\$?\s*([\d.,]+)",
            re.IGNORECASE,
        )

        valores_pagos = padrao_valor_pago.findall(texto)
        valores_apresentados = padrao_valor_apresentado.findall(texto)

        resultado.metadados["valores_pagos"] = valores_pagos[:20]
        resultado.metadados["valores_apresentados"] = valores_apresentados[:20]

        for tabela in tabelas:
            if not tabela or len(tabela) < 2:
                continue
            cabecalho = [str(c).lower() if c else "" for c in tabela[0]]
            for linha in tabela[1:]:
                proc = self._mapear_linha_procedimento(cabecalho, linha)
                if proc:
                    resultado.procedimentos.append(proc)

    def _extrair_faturamento_pdf(
        self,
        texto: str,
        tabelas: list,
        resultado: ResultadoParsing,
    ):
        """Extrai dados de relatório de faturamento."""
        for tabela in tabelas:
            if not tabela or len(tabela) < 2:
                continue
            cabecalho = [str(c).lower() if c else "" for c in tabela[0]]
            for linha in tabela[1:]:
                proc = self._mapear_linha_procedimento(cabecalho, linha)
                if proc:
                    resultado.procedimentos.append(proc)

    def _extrair_dados_genericos(
        self,
        texto: str,
        tabelas: list,
        resultado: ResultadoParsing,
    ):
        """Extração genérica para PDFs não classificados."""
        padrao_tuss = re.compile(r"\b(\d{8})\b")
        padrao_cid = re.compile(r"\b([A-Z]\d{2}(?:\.\d{1,2})?)\b")
        padrao_cnes = re.compile(r"(?:CNES)[:\s]*(\d{7})", re.IGNORECASE)
        padrao_ans = re.compile(
            r"(?:registro\s*ANS|ANS)[:\s]*(\d{6})", re.IGNORECASE
        )

        resultado.metadados["codigos_tuss"] = list(
            set(padrao_tuss.findall(texto))
        )[:50]
        resultado.metadados["codigos_cid"] = list(
            set(padrao_cid.findall(texto))
        )[:50]
        resultado.metadados["codigos_cnes"] = padrao_cnes.findall(texto)
        resultado.metadados["registros_ans"] = padrao_ans.findall(texto)

    def _mapear_linha_glosa(
        self, cabecalho: list[str], linha: list
    ) -> Optional[dict]:
        """Mapeia uma linha de tabela para um registro de glosa."""
        if not linha or len(linha) < 2:
            return None

        glosa = {}
        for i, col in enumerate(cabecalho):
            if i >= len(linha):
                break
            val = str(linha[i]).strip() if linha[i] else ""
            if not val:
                continue

            if any(t in col for t in ["motivo", "código motivo", "cod"]):
                glosa["codigo_motivo"] = val
            elif any(t in col for t in ["descrição motivo", "justificativa"]):
                glosa["descricao_motivo"] = val
            elif any(t in col for t in ["valor glosado", "glosa"]):
                glosa["valor_glosado"] = self._parse_valor(val)
            elif any(t in col for t in ["valor original", "valor apresentado"]):
                glosa["valor_original"] = self._parse_valor(val)
            elif any(t in col for t in ["guia", "nº guia"]):
                glosa["numero_guia"] = val
            elif any(t in col for t in ["tuss", "procedimento", "código"]):
                glosa["codigo_tuss"] = val

        return glosa if glosa.get("valor_glosado") or glosa.get("codigo_motivo") else None

    def _mapear_linha_procedimento(
        self, cabecalho: list[str], linha: list
    ) -> Optional[dict]:
        """Mapeia uma linha de tabela para um procedimento."""
        if not linha or len(linha) < 2:
            return None

        proc = {}
        for i, col in enumerate(cabecalho):
            if i >= len(linha):
                break
            val = str(linha[i]).strip() if linha[i] else ""
            if not val:
                continue

            if any(t in col for t in ["tuss", "código", "cod proc"]):
                proc["codigo_tuss"] = val
            elif any(t in col for t in ["descrição", "procedimento"]):
                proc["descricao"] = val
            elif any(t in col for t in ["qtd", "quantidade"]):
                proc["quantidade_realizada"] = val
            elif any(t in col for t in ["valor unitário", "vl unit"]):
                proc["valor_unitario"] = self._parse_valor(val)
            elif any(t in col for t in ["valor total", "vl total"]):
                proc["valor_total"] = self._parse_valor(val)
            elif any(t in col for t in ["valor pago", "vl pago"]):
                proc["valor_pago"] = self._parse_valor(val)

        return proc if proc.get("codigo_tuss") else None

    @staticmethod
    def _parse_valor(texto: str) -> Optional[float]:
        """Converte texto monetário brasileiro em float."""
        try:
            limpo = (
                texto.replace("R$", "")
                .replace(" ", "")
                .replace(".", "")
                .replace(",", ".")
                .strip()
            )
            return float(limpo) if limpo else None
        except (ValueError, AttributeError):
            return None
