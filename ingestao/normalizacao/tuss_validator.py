"""
Validador de códigos TUSS (Terminologia Unificada da Saúde Suplementar).
Referência: Padrão TUSS ANS - Tabela 22.

O código TUSS possui 8 dígitos numéricos organizados em:
- Tabela 22: Procedimentos e eventos em saúde
- Tabela 18: Diárias e taxas
- Tabela 19: Materiais
- Tabela 20: Medicamentos (OPME)

Estrutura: GGSSSSDD
- GG: Grupo
- SSSS: Subgrupo/sequencial
- DD: Dígito verificador (em algumas versões)
"""
import re


# Faixas de códigos TUSS por grupo (amostra representativa)
FAIXAS_TUSS = {
    "10": {"descricao": "Consultas", "inicio": 10101012, "fim": 10199999},
    "20": {"descricao": "Procedimentos diagnósticos e terapêuticos", "inicio": 20101015, "fim": 29999999},
    "30": {"descricao": "Procedimentos cirúrgicos", "inicio": 30101018, "fim": 39999999},
    "40": {"descricao": "Procedimentos clínicos", "inicio": 40101010, "fim": 49999999},
    "50": {"descricao": "Outros procedimentos", "inicio": 50000000, "fim": 59999999},
    "60": {"descricao": "Diárias e taxas", "inicio": 60000000, "fim": 69999999},
    "70": {"descricao": "Materiais e OPME", "inicio": 70000000, "fim": 79999999},
    "80": {"descricao": "Medicamentos", "inicio": 80000000, "fim": 89999999},
    "90": {"descricao": "Gases medicinais e nutricionais", "inicio": 90000000, "fim": 99999999},
}

# Códigos TUSS frequentemente glosados por uso incorreto
CODIGOS_ATENCAO = {
    "10101012": "Consulta em consultório - verificar se não há duplicidade no mesmo dia",
    "10101039": "Consulta em pronto-socorro - verificar caráter de urgência",
    "40304361": "Sessão de fisioterapia - verificar limite contratual",
    "40301630": "Hemograma completo - verificar duplicidade",
    "40302040": "Glicose - verificar duplicidade",
}


class TussValidator:
    """Validador de códigos TUSS."""

    PADRAO_TUSS = re.compile(r"^\d{8}$")

    def validar(self, codigo: str) -> dict:
        """
        Valida um código TUSS.

        Returns:
            dict com: valido (bool), mensagem (str), grupo (str|None)
        """
        codigo = str(codigo).strip()

        # Verificar formato
        if not self.PADRAO_TUSS.match(codigo):
            return {
                "valido": False,
                "mensagem": f"Código TUSS '{codigo}' deve ter exatamente 8 dígitos numéricos.",
                "grupo": None,
            }

        # Verificar faixa
        codigo_int = int(codigo)
        grupo_encontrado = None
        for prefixo, info in FAIXAS_TUSS.items():
            if info["inicio"] <= codigo_int <= info["fim"]:
                grupo_encontrado = info["descricao"]
                break

        if not grupo_encontrado:
            return {
                "valido": False,
                "mensagem": (
                    f"Código TUSS '{codigo}' não pertence a nenhuma faixa conhecida. "
                    "Verifique se o código está atualizado conforme última publicação ANS."
                ),
                "grupo": None,
            }

        resultado = {
            "valido": True,
            "mensagem": f"Código TUSS válido - Grupo: {grupo_encontrado}",
            "grupo": grupo_encontrado,
        }

        # Verificar se é código de atenção
        if codigo in CODIGOS_ATENCAO:
            resultado["atencao"] = CODIGOS_ATENCAO[codigo]

        return resultado

    def obter_grupo(self, codigo: str) -> str:
        """Retorna o grupo do código TUSS."""
        try:
            codigo_int = int(str(codigo).strip())
            for prefixo, info in FAIXAS_TUSS.items():
                if info["inicio"] <= codigo_int <= info["fim"]:
                    return info["descricao"]
        except ValueError:
            pass
        return "Desconhecido"
