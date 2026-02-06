"""
Modelo para documentos ingeridos pelo sistema.
Representa qualquer arquivo de entrada: XML TISS, PDF, planilha, texto.
"""
from models.base import db, utcnow
from dominio.constantes import StatusDocumento


class Documento(db.Model):
    __tablename__ = "documentos"

    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(500), nullable=False)
    tipo_arquivo = db.Column(db.String(50), nullable=False)  # xml, pdf, xlsx, csv, txt
    tamanho_bytes = db.Column(db.Integer)
    hash_conteudo = db.Column(db.String(64), unique=True)  # SHA-256 para dedup
    status = db.Column(
        db.String(20),
        default=StatusDocumento.PENDENTE.value,
        nullable=False,
    )
    erro_processamento = db.Column(db.Text)
    metadados_extraidos = db.Column(db.JSON)  # Metadados brutos extraídos
    criado_em = db.Column(db.DateTime, default=utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relacionamentos
    guias = db.relationship("GuiaTISS", backref="documento", lazy="dynamic")

    def __repr__(self):
        return f"<Documento {self.nome_arquivo} [{self.status}]>"
