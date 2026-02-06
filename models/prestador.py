"""
Modelo para prestadores de saúde.
"""
from models.base import db, utcnow


class Prestador(db.Model):
    __tablename__ = "prestadores"

    id = db.Column(db.Integer, primary_key=True)
    cnes = db.Column(db.String(7), unique=True, index=True)  # Cadastro Nacional
    cnpj = db.Column(db.String(14))
    razao_social = db.Column(db.String(300))
    nome_fantasia = db.Column(db.String(300))
    tipo = db.Column(db.String(30))  # TipoPrestador
    uf = db.Column(db.String(2))
    municipio = db.Column(db.String(100))
    codigo_municipio_ibge = db.Column(db.String(7))

    # Dados de credenciamento
    credenciado = db.Column(db.Boolean, default=True)
    data_credenciamento = db.Column(db.Date)

    criado_em = db.Column(db.DateTime, default=utcnow)
    atualizado_em = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    guias = db.relationship("GuiaTISS", backref="prestador", lazy="dynamic")

    def __repr__(self):
        return f"<Prestador CNES:{self.cnes} {self.razao_social}>"
