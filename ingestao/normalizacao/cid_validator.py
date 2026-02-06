"""
Validador de códigos CID-10 (Classificação Internacional de Doenças).
Referência: OMS CID-10 / CID-10 adaptação brasileira.

Formato: Letra + 2 dígitos + opcionalmente ponto + 1-2 dígitos
Exemplos: A00, A00.0, Z99.9, S72.0
"""
import re


# Capítulos CID-10 e suas faixas
CAPITULOS_CID10 = {
    "A": {"inicio": "A00", "fim": "B99", "descricao": "Doenças infecciosas e parasitárias"},
    "B": {"inicio": "A00", "fim": "B99", "descricao": "Doenças infecciosas e parasitárias"},
    "C": {"inicio": "C00", "fim": "D48", "descricao": "Neoplasias"},
    "D": {"inicio": "C00", "fim": "D89", "descricao": "Neoplasias / Doenças do sangue"},
    "E": {"inicio": "E00", "fim": "E90", "descricao": "Doenças endócrinas, nutricionais e metabólicas"},
    "F": {"inicio": "F00", "fim": "F99", "descricao": "Transtornos mentais e comportamentais"},
    "G": {"inicio": "G00", "fim": "G99", "descricao": "Doenças do sistema nervoso"},
    "H": {"inicio": "H00", "fim": "H95", "descricao": "Doenças do olho e ouvido"},
    "I": {"inicio": "I00", "fim": "I99", "descricao": "Doenças do aparelho circulatório"},
    "J": {"inicio": "J00", "fim": "J99", "descricao": "Doenças do aparelho respiratório"},
    "K": {"inicio": "K00", "fim": "K93", "descricao": "Doenças do aparelho digestivo"},
    "L": {"inicio": "L00", "fim": "L99", "descricao": "Doenças da pele"},
    "M": {"inicio": "M00", "fim": "M99", "descricao": "Doenças do sistema osteomuscular"},
    "N": {"inicio": "N00", "fim": "N99", "descricao": "Doenças do aparelho geniturinário"},
    "O": {"inicio": "O00", "fim": "O99", "descricao": "Gravidez, parto e puerpério"},
    "P": {"inicio": "P00", "fim": "P96", "descricao": "Afecções originadas no período perinatal"},
    "Q": {"inicio": "Q00", "fim": "Q99", "descricao": "Malformações congênitas"},
    "R": {"inicio": "R00", "fim": "R99", "descricao": "Sintomas e sinais não classificados"},
    "S": {"inicio": "S00", "fim": "T98", "descricao": "Lesões e causas externas"},
    "T": {"inicio": "S00", "fim": "T98", "descricao": "Lesões e causas externas"},
    "V": {"inicio": "V01", "fim": "Y98", "descricao": "Causas externas de morbidade"},
    "W": {"inicio": "V01", "fim": "Y98", "descricao": "Causas externas de morbidade"},
    "X": {"inicio": "V01", "fim": "Y98", "descricao": "Causas externas de morbidade"},
    "Y": {"inicio": "V01", "fim": "Y98", "descricao": "Causas externas de morbidade"},
    "Z": {"inicio": "Z00", "fim": "Z99", "descricao": "Fatores que influenciam o estado de saúde"},
}

# CIDs que requerem atenção especial em auditoria
CIDS_ATENCAO = {
    "Z76.5": "Pessoa fingindo ser doente - possível fraude",
    "R69": "Causas desconhecidas e não especificadas - CID inespecífico",
    "Z02.7": "Emissão de atestado médico - não justifica procedimento",
}


class CidValidator:
    """Validador de códigos CID-10."""

    PADRAO_CID = re.compile(r"^[A-Z]\d{2}(\.\d{1,2})?$")

    def normalizar(self, codigo: str) -> str:
        """Normaliza um código CID para formato padrão."""
        codigo = str(codigo).strip().upper()
        # Remover espaços e caracteres estranhos
        codigo = re.sub(r"[^A-Z0-9.]", "", codigo)
        # Garantir formato com ponto se tiver mais de 3 caracteres
        if len(codigo) > 3 and "." not in codigo:
            codigo = codigo[:3] + "." + codigo[3:]
        return codigo

    def validar(self, codigo: str) -> bool:
        """Verifica se o código CID-10 tem formato válido."""
        codigo = self.normalizar(codigo)
        if not self.PADRAO_CID.match(codigo):
            return False
        # Verificar se a letra pertence a um capítulo conhecido
        return codigo[0] in CAPITULOS_CID10

    def obter_capitulo(self, codigo: str) -> str:
        """Retorna a descrição do capítulo CID-10."""
        codigo = self.normalizar(codigo)
        if codigo and codigo[0] in CAPITULOS_CID10:
            return CAPITULOS_CID10[codigo[0]]["descricao"]
        return "Desconhecido"

    def verificar_atencao(self, codigo: str) -> dict | None:
        """Verifica se o CID requer atenção especial."""
        codigo = self.normalizar(codigo)
        if codigo in CIDS_ATENCAO:
            return {"codigo": codigo, "alerta": CIDS_ATENCAO[codigo]}
        # Verificar sem subcategoria
        codigo_base = codigo.split(".")[0]
        if codigo_base in CIDS_ATENCAO:
            return {"codigo": codigo_base, "alerta": CIDS_ATENCAO[codigo_base]}
        return None
