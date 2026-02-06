"""
Modelo para procedimentos e itens faturáveis dentro de uma guia TISS.
"""
from models.base import db, utcnow


class Procedimento(db.Model):
    __tablename__ = "procedimentos"

    id = db.Column(db.Integer, primary_key=True)
    guia_id = db.Column(db.Integer, db.ForeignKey("guias_tiss.id"), nullable=False)

    # Identificação do procedimento
    codigo_tuss = db.Column(db.String(10), nullable=False, index=True)
    descricao = db.Column(db.String(500))
    tabela_referencia = db.Column(db.String(2))  # 22=TUSS, 00=própria

    # Quantidades e valores
    quantidade_solicitada = db.Column(db.Integer)
    quantidade_autorizada = db.Column(db.Integer)
    quantidade_realizada = db.Column(db.Integer)
    valor_unitario = db.Column(db.Numeric(12, 2))
    valor_total = db.Column(db.Numeric(12, 2))

    # Dados do procedimento
    data_realizacao = db.Column(db.Date)
    hora_inicio = db.Column(db.Time)
    hora_fim = db.Column(db.Time)
    via_acesso = db.Column(db.String(1))  # Código TISS
    tecnica_utilizada = db.Column(db.String(1))  # Código TISS
    grau_participacao = db.Column(db.String(2))  # 00=Cirurgião, 01=Auxiliar, etc.

    # Profissional executante
    profissional_nome = db.Column(db.String(200))
    profissional_conselho = db.Column(db.String(10))  # CRM, COREN, etc.
    profissional_numero = db.Column(db.String(15))
    profissional_uf = db.Column(db.String(2))
    profissional_cbos = db.Column(db.String(6))

    # Valores de glosa/pagamento
    valor_pago = db.Column(db.Numeric(12, 2))
    valor_glosado = db.Column(db.Numeric(12, 2))

    # Porte CBHPM (quando aplicável)
    porte_cbhpm = db.Column(db.String(3))

    criado_em = db.Column(db.DateTime, default=utcnow, nullable=False)

    def __repr__(self):
        return f"<Procedimento TUSS:{self.codigo_tuss} x{self.quantidade_realizada}>"
