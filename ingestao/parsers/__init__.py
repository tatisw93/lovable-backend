"""
Parsers para diferentes formatos de arquivo.
"""
from ingestao.parsers.base import BaseParser
from ingestao.parsers.tiss_xml import TissXmlParser
from ingestao.parsers.pdf_parser import PdfParser
from ingestao.parsers.planilha_parser import PlanilhaParser
from ingestao.parsers.texto_parser import TextoParser

PARSERS_POR_TIPO = {
    "xml": TissXmlParser,
    "pdf": PdfParser,
    "xlsx": PlanilhaParser,
    "xls": PlanilhaParser,
    "csv": PlanilhaParser,
    "txt": TextoParser,
}


def obter_parser(tipo_arquivo: str) -> BaseParser:
    """Retorna o parser apropriado para o tipo de arquivo."""
    cls = PARSERS_POR_TIPO.get(tipo_arquivo.lower())
    if cls is None:
        raise ValueError(f"Tipo de arquivo não suportado: {tipo_arquivo}")
    return cls()
