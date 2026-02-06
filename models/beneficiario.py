"""
Modelo para beneficiários (pacientes) identificados nas guias.
"""
from models.base import db, utcnow


class Beneficiario(db.Model):
    __tablename__ = "beneficiarios"

    id = db.Column(db.Integer, primary_key=True)
    numero_carteirinha = db.Column(db.String(20), index=True)
    nome = db.Column(db.String(200))
    data_nascimento = db.Column(db.Date)
    sexo = db.Column(db.String(1))  # M, F
    cpf = db.Column(db.String(11))
    cns = db.Column(db.String(15))  # Cartão Nacional de Saúde
    operadora_id = db.Column(db.Integer, db.ForeignKey("operadoras.id"))
    plano = db.Column(db.String(100))
    vigencia_inicio = db.Column(db.Date)
    vigencia_fim = db.Column(db.Date)
    criado_em = db.Column(db.DateTime, default=utcnow)

    guias = db.relationship("GuiaTISS", backref="beneficiario", lazy="dynamic")

    def __repr__(self):
        return f"<Beneficiario {self.numero_carteirinha}>"
