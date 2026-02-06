"""
Modelo para operadoras de planos de saúde.
"""
from models.base import db, utcnow


class Operadora(db.Model):
    __tablename__ = "operadoras"

    id = db.Column(db.Integer, primary_key=True)
    registro_ans = db.Column(db.String(6), unique=True, index=True)
    cnpj = db.Column(db.String(14))
    razao_social = db.Column(db.String(300))
    nome_fantasia = db.Column(db.String(300))
    modalidade = db.Column(db.String(50))  # Medicina de grupo, Cooperativa, etc.

    # Regras conhecidas da operadora
    regras_contrato = db.Column(db.JSON)  # Regras contratuais específicas
    padroes_glosa = db.Column(db.JSON)  # Padrões recorrentes de glosa observados

    criado_em = db.Column(db.DateTime, default=utcnow)
    atualizado_em = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    guias = db.relationship("GuiaTISS", backref="operadora", lazy="dynamic")
    beneficiarios = db.relationship("Beneficiario", backref="operadora", lazy="dynamic")

    def __repr__(self):
        return f"<Operadora ANS:{self.registro_ans} {self.razao_social}>"
