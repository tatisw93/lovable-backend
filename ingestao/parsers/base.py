"""
Interface base para todos os parsers de documentos.
"""
from abc import ABC, abstractmethod
from typing import Any


class ResultadoParsing:
    """Resultado padronizado da extração de um documento."""

    def __init__(self):
        self.tipo_documento: str = ""
        self.guias: list[dict] = []
        self.procedimentos: list[dict] = []
        self.prestadores: list[dict] = []
        self.operadoras: list[dict] = []
        self.beneficiarios: list[dict] = []
        self.glosas: list[dict] = []
        self.metadados: dict[str, Any] = {}
        self.avisos: list[str] = []
        self.erros: list[str] = []

    def to_dict(self) -> dict:
        return {
            "tipo_documento": self.tipo_documento,
            "guias": self.guias,
            "procedimentos": self.procedimentos,
            "prestadores": self.prestadores,
            "operadoras": self.operadoras,
            "beneficiarios": self.beneficiarios,
            "glosas": self.glosas,
            "metadados": self.metadados,
            "avisos": self.avisos,
            "erros": self.erros,
        }


class BaseParser(ABC):
    """Interface base para parsers de documentos."""

    @abstractmethod
    def parse(self, conteudo: bytes, nome_arquivo: str) -> ResultadoParsing:
        """
        Extrai dados estruturados de um documento.

        Args:
            conteudo: Bytes brutos do arquivo.
            nome_arquivo: Nome original do arquivo.

        Returns:
            ResultadoParsing com os dados extraídos.
        """
        ...

    @abstractmethod
    def tipos_suportados(self) -> list[str]:
        """Retorna lista de extensões de arquivo suportadas."""
        ...
