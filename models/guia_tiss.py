"""
Modelo para guias TISS extraídas dos documentos.
Representa guias SP/SADT, Honorários, Internação, Consulta.
"""
from models.base import db, utcnow
from dominio.constantes import StatusGuia


class GuiaTISS(db.Model):
    __tablename__ = "guias_tiss"

    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(db.Integer, db.ForeignKey("documentos.id"), nullable=False)
    tipo_guia = db.Column(db.String(30), nullable=False)  # TipoGuiaTISS
    numero_guia_prestador = db.Column(db.String(20), index=True)
    numero_guia_operadora = db.Column(db.String(20), index=True)
    numero_autorizacao = db.Column(db.String(20))
    registro_ans = db.Column(db.String(6))
    versao_tiss = db.Column(db.String(10))

    # Beneficiário
    beneficiario_id = db.Column(db.Integer, db.ForeignKey("beneficiarios.id"))

    # Prestador
    prestador_id = db.Column(db.Integer, db.ForeignKey("prestadores.id"))

    # Operadora
    operadora_id = db.Column(db.Integer, db.ForeignKey("operadoras.id"))

    # Dados do atendimento
    data_atendimento = db.Column(db.Date)
    data_fim_atendimento = db.Column(db.Date)
    tipo_atendimento = db.Column(db.String(2))  # Código TISS
    indicacao_acidente = db.Column(db.String(1))
    carater_atendimento = db.Column(db.String(1))  # Eletivo, Urgência

    # Diagnósticos
    cid_principal = db.Column(db.String(10))
    cid_secundario = db.Column(db.String(10))
    cid_terciario = db.Column(db.String(10))

    # Valores
    valor_total_informado = db.Column(db.Numeric(12, 2))
    valor_total_pago = db.Column(db.Numeric(12, 2))
    valor_total_glosado = db.Column(db.Numeric(12, 2))

    # Status
    status = db.Column(
        db.String(20), default=StatusGuia.PENDENTE.value, nullable=False
    )

    # Dados brutos XML/origem
    dados_brutos = db.Column(db.JSON)

    # Campos de controle de qualidade
    campos_ausentes = db.Column(db.JSON)  # Lista de campos obrigatórios faltantes
    inconsistencias = db.Column(db.JSON)  # Inconsistências detectadas

    criado_em = db.Column(db.DateTime, default=utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relacionamentos
    procedimentos = db.relationship("Procedimento", backref="guia", lazy="dynamic")
    glosas = db.relationship("Glosa", backref="guia", lazy="dynamic")
    achados = db.relationship("AchadoAuditoria", backref="guia", lazy="dynamic")

    def __repr__(self):
        return f"<GuiaTISS {self.tipo_guia} #{self.numero_guia_prestador}>"
