"""
Parser para documentos de texto livre.
Usa heurísticas e regex para extrair dados de saúde de textos
desestruturados: logs de faturamento, e-mails, relatórios textuais.
"""
import re
from typing import Optional

from ingestao.parsers.base import BaseParser, ResultadoParsing


class TextoParser(BaseParser):
    """Parser para documentos de texto livre."""

    # Padrões regex para identificação de entidades
    PADRAO_TUSS = re.compile(r"\b(\d{8})\b")
    PADRAO_CID = re.compile(r"\b([A-Z]\d{2}(?:\.\d{1,2})?)\b")
    PADRAO_CNES = re.compile(r"(?:CNES)[:\s]*(\d{7})", re.IGNORECASE)
    PADRAO_ANS = re.compile(
        r"(?:registro\s*ANS|ANS\s*n[ºo°]?)[:\s]*(\d{6})", re.IGNORECASE
    )
    PADRAO_GUIA = re.compile(
        r"(?:guia|n[ºo°]\s*guia)[:\s]*(\d{8,20})", re.IGNORECASE
    )
    PADRAO_VALOR = re.compile(
        r"R\$\s*([\d.,]+)", re.IGNORECASE
    )
    PADRAO_CPF = re.compile(r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b")
    PADRAO_CNPJ = re.compile(
        r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b"
    )
    PADRAO_DATA = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
    PADRAO_CARTEIRINHA = re.compile(
        r"(?:carteirinha|carteira|matrícula)[:\s]*(\d{10,20})", re.IGNORECASE
    )

    def tipos_suportados(self) -> list[str]:
        return ["txt"]

    def parse(self, conteudo: bytes, nome_arquivo: str) -> ResultadoParsing:
        resultado = ResultadoParsing()
        resultado.tipo_documento = "texto"

        try:
            texto = conteudo.decode("utf-8", errors="replace")
        except Exception:
            texto = conteudo.decode("latin-1", errors="replace")

        resultado.metadados["tamanho_caracteres"] = len(texto)

        # Extrair todas as entidades reconhecíveis
        codigos_tuss = list(set(self.PADRAO_TUSS.findall(texto)))
        codigos_cid = list(set(self.PADRAO_CID.findall(texto)))
        codigos_cnes = self.PADRAO_CNES.findall(texto)
        registros_ans = self.PADRAO_ANS.findall(texto)
        numeros_guia = self.PADRAO_GUIA.findall(texto)
        valores = self.PADRAO_VALOR.findall(texto)
        carteirinhas = self.PADRAO_CARTEIRINHA.findall(texto)
        datas = self.PADRAO_DATA.findall(texto)

        resultado.metadados.update(
            {
                "codigos_tuss": codigos_tuss[:100],
                "codigos_cid": codigos_cid[:100],
                "codigos_cnes": codigos_cnes[:20],
                "registros_ans": registros_ans[:20],
                "valores_monetarios": valores[:50],
                "datas_encontradas": datas[:50],
            }
        )

        # Criar guias a partir de números encontrados
        for num in numeros_guia:
            resultado.guias.append(
                {
                    "numero_guia_prestador": num,
                    "tipo_guia": "texto_livre",
                }
            )

        # Criar beneficiários a partir de carteirinhas
        for cart in carteirinhas:
            resultado.beneficiarios.append({"numero_carteirinha": cart})

        # Criar procedimentos a partir de códigos TUSS em contexto
        for match in re.finditer(
            r"(\d{8})\s*[-–]\s*(.+?)(?:\s*(?:qtd|x|quantidade)[:\s]*(\d+))?"
            r"(?:\s*R\$\s*([\d.,]+))?",
            texto,
            re.IGNORECASE,
        ):
            proc = {
                "codigo_tuss": match.group(1),
                "descricao": match.group(2).strip() if match.group(2) else None,
                "quantidade_realizada": match.group(3),
                "valor_total": match.group(4),
            }
            resultado.procedimentos.append(proc)

        # Detectar menções a glosa no texto
        padroes_glosa_texto = re.finditer(
            r"(?:glos[ao]|negad[ao]|indeferid[ao])[:\s]*(.+?)(?:\n|$)",
            texto,
            re.IGNORECASE,
        )
        for match in padroes_glosa_texto:
            resultado.glosas.append(
                {
                    "descricao_motivo": match.group(1).strip(),
                    "fonte": "texto_livre",
                }
            )

        if not any(
            [
                resultado.guias,
                resultado.procedimentos,
                resultado.glosas,
                codigos_tuss,
                codigos_cid,
            ]
        ):
            resultado.avisos.append(
                "Nenhum dado estruturado de saúde identificado no texto."
            )

        return resultado
