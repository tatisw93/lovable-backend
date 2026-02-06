"""
Modelo para registros de glosa.
"""
from models.base import db, utcnow


class Glosa(db.Model):
    __tablename__ = "glosas"

    id = db.Column(db.Integer, primary_key=True)
    guia_id = db.Column(db.Integer, db.ForeignKey("guias_tiss.id"), nullable=False)
    procedimento_id = db.Column(db.Integer, db.ForeignKey("procedimentos.id"))

    # Identificação da glosa
    codigo_motivo = db.Column(db.String(10))  # Código padronizado ANS
    descricao_motivo = db.Column(db.String(500))
    motivo_detalhado = db.Column(db.Text)  # Justificativa textual da operadora

    # Valores
    valor_glosado = db.Column(db.Numeric(12, 2), nullable=False)
    valor_original = db.Column(db.Numeric(12, 2))

    # Classificação
    tipo_glosa = db.Column(db.String(20))  # administrativa, tecnica, linear
    recorrente = db.Column(db.Boolean, default=False)  # Padrão recorrente detectado

    # Recurso
    recurso_apresentado = db.Column(db.Boolean, default=False)
    resultado_recurso = db.Column(db.String(20))  # aceito, negado, parcial
    valor_recuperado = db.Column(db.Numeric(12, 2))

    # Datas
    data_glosa = db.Column(db.Date)
    data_recurso = db.Column(db.Date)

    criado_em = db.Column(db.DateTime, default=utcnow)

    procedimento = db.relationship(
        "Procedimento", backref=db.backref("glosas", lazy="dynamic")
    )

    def __repr__(self):
        return f"<Glosa {self.codigo_motivo} R${self.valor_glosado}>"
