"""
Constantes e tabelas de referência da saúde suplementar brasileira.
Inclui códigos TISS, tipos de guia, motivos de glosa ANS, e regras estruturais.
"""
from enum import Enum


# ---------------------------------------------------------------------------
# Tipos de guia TISS (Padrão TISS 4.x)
# ---------------------------------------------------------------------------
class TipoGuiaTISS(str, Enum):
    CONSULTA = "guiaConsulta"
    SADT = "guiaSP_SADT"
    HONORARIOS = "guiaHonorarios"
    INTERNACAO = "guiaInternacao"
    ODONTOLOGIA = "guiaOdontologia"
    ANEXO_CLINICO = "guiaAnexoClinico"
    RESUMO_INTERNACAO = "guiaResumoInternacao"


# ---------------------------------------------------------------------------
# Tipos de prestador
# ---------------------------------------------------------------------------
class TipoPrestador(str, Enum):
    HOSPITAL = "hospital"
    CLINICA = "clinica"
    LABORATORIO = "laboratorio"
    CONSULTORIO = "consultorio"
    PRONTO_SOCORRO = "pronto_socorro"
    HOME_CARE = "home_care"


# ---------------------------------------------------------------------------
# Classificação de nível do achado de auditoria
# ---------------------------------------------------------------------------
class NivelAchado(str, Enum):
    TECNICO = "tecnico"
    ADMINISTRATIVO = "administrativo"
    REGULATORIO = "regulatorio"


# ---------------------------------------------------------------------------
# Classificação de confiança
# ---------------------------------------------------------------------------
class NivelConfianca(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


# ---------------------------------------------------------------------------
# Status de processamento
# ---------------------------------------------------------------------------
class StatusDocumento(str, Enum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    ERRO = "erro"


class StatusGuia(str, Enum):
    FATURADA = "faturada"
    GLOSADA_PARCIAL = "glosada_parcial"
    GLOSADA_TOTAL = "glosada_total"
    PAGA = "paga"
    PENDENTE = "pendente"
    RECURSO = "recurso"


# ---------------------------------------------------------------------------
# Motivos de glosa padronizados ANS (amostra dos mais recorrentes)
# Referência: Padrão TISS - Tabela de Motivos de Glosa
# ---------------------------------------------------------------------------
MOTIVOS_GLOSA_ANS = {
    "MG001": "Procedimento não coberto pelo plano contratado",
    "MG002": "Procedimento não autorizado previamente",
    "MG003": "Quantidade excede o permitido pelo protocolo",
    "MG004": "Código TUSS inválido ou inexistente",
    "MG005": "CID incompatível com procedimento solicitado",
    "MG006": "Beneficiário inativo na data do atendimento",
    "MG007": "Duplicidade de cobrança",
    "MG008": "Valor unitário acima do contratado",
    "MG009": "Guia fora do prazo de apresentação",
    "MG010": "Prestador não credenciado",
    "MG011": "Campos obrigatórios não preenchidos",
    "MG012": "Número da guia de autorização inválido",
    "MG013": "Data de atendimento fora da vigência da autorização",
    "MG014": "Procedimento incluído em pacote/diária",
    "MG015": "Material/medicamento sem justificativa clínica",
    "MG016": "Profissional executante sem registro válido",
    "MG017": "Inconsistência entre guia e lote",
    "MG018": "Assinatura ou identificação do beneficiário ausente",
    "MG019": "Procedimento incompatível com sexo/idade do beneficiário",
    "MG020": "Ausência de relatório médico obrigatório",
}

# ---------------------------------------------------------------------------
# Campos obrigatórios por tipo de guia TISS
# Referência: Padrão TISS versão 4.01.00 (ANS)
# ---------------------------------------------------------------------------
CAMPOS_OBRIGATORIOS_TISS = {
    TipoGuiaTISS.SADT: [
        "registroANS",
        "numeroGuiaPrestador",
        "dadosBeneficiario",
        "dadosSolicitante",
        "dadosSolicitacao",
        "dadosExecutante",
        "procedimentosRealizados",
    ],
    TipoGuiaTISS.HONORARIOS: [
        "registroANS",
        "numeroGuiaPrestador",
        "guiaSolicInternacao",
        "dadosBeneficiario",
        "dadosContratado",
        "dadosInternacao",
        "procedimentosRealizados",
    ],
    TipoGuiaTISS.INTERNACAO: [
        "registroANS",
        "numeroGuiaPrestador",
        "dadosBeneficiario",
        "dadosContratado",
        "dadosInternacao",
        "dadosSaidaInternacao",
        "procedimentosRealizados",
        "valorTotal",
    ],
    TipoGuiaTISS.CONSULTA: [
        "registroANS",
        "numeroGuiaPrestador",
        "dadosBeneficiario",
        "dadosContratadoExecutante",
        "dadosAtendimento",
    ],
}

# ---------------------------------------------------------------------------
# Regras de compatibilidade CID x Procedimento (amostra)
# ---------------------------------------------------------------------------
REGRAS_CID_PROCEDIMENTO = {
    # CIDs obstétricos requerem procedimentos específicos
    "O80": {"procedimentos_validos_prefixos": ["3100", "3101", "3102"]},
    # CIDs ortopédicos
    "S72": {"procedimentos_validos_prefixos": ["3040", "3041"]},
    # CIDs cardiológicos
    "I21": {"procedimentos_validos_prefixos": ["3050", "3051", "3060"]},
}

# ---------------------------------------------------------------------------
# Tabela de porte CBHPM simplificada (referência de valores mínimos)
# ---------------------------------------------------------------------------
PORTES_CBHPM = {
    "1A": {"valor_minimo": 16.20, "descricao": "Porte 1A - Procedimentos simples"},
    "1B": {"valor_minimo": 24.30, "descricao": "Porte 1B"},
    "1C": {"valor_minimo": 32.40, "descricao": "Porte 1C"},
    "2A": {"valor_minimo": 48.60, "descricao": "Porte 2A"},
    "2B": {"valor_minimo": 64.80, "descricao": "Porte 2B"},
    "2C": {"valor_minimo": 81.00, "descricao": "Porte 2C"},
    "3A": {"valor_minimo": 113.40, "descricao": "Porte 3A"},
    "3B": {"valor_minimo": 145.80, "descricao": "Porte 3B"},
    "3C": {"valor_minimo": 178.20, "descricao": "Porte 3C"},
    "4A": {"valor_minimo": 243.00, "descricao": "Porte 4A"},
    "4B": {"valor_minimo": 307.80, "descricao": "Porte 4B"},
    "4C": {"valor_minimo": 372.60, "descricao": "Porte 4C"},
    "5A": {"valor_minimo": 502.20, "descricao": "Porte 5A - Procedimentos alta complexidade"},
    "5B": {"valor_minimo": 631.80, "descricao": "Porte 5B"},
    "5C": {"valor_minimo": 761.40, "descricao": "Porte 5C"},
}

# ---------------------------------------------------------------------------
# Namespace XML TISS
# ---------------------------------------------------------------------------
TISS_XML_NAMESPACE = {
    "ans": "http://www.ans.gov.br/padroes/tiss/schemas",
}

# ---------------------------------------------------------------------------
# Limites operacionais padrão
# ---------------------------------------------------------------------------
PRAZO_APRESENTACAO_GUIA_DIAS = 30  # Prazo padrão para apresentação de guia
PRAZO_RECURSO_GLOSA_DIAS = 30     # Prazo para recurso de glosa
