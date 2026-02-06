"""
Modelo para achados de auditoria gerados pelos agentes.
Este é o output principal dos agentes — cada achado representa um erro,
desvio ou oportunidade identificada.
"""
from models.base import db, utcnow
from dominio.constantes import NivelAchado, NivelConfianca


class AchadoAuditoria(db.Model):
    __tablename__ = "achados_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    guia_id = db.Column(db.Integer, db.ForeignKey("guias_tiss.id"))
    procedimento_id = db.Column(db.Integer, db.ForeignKey("procedimentos.id"))
    documento_id = db.Column(db.Integer, db.ForeignKey("documentos.id"))

    # Identificação do agente
    agente_tipo = db.Column(db.String(50), nullable=False)  # Tipo do agente que gerou
    agente_versao = db.Column(db.String(10), default="1.0.0")

    # Classificação
    nivel = db.Column(db.String(20), nullable=False)  # NivelAchado
    confianca = db.Column(db.String(10), nullable=False)  # NivelConfianca
    confianca_score = db.Column(db.Float)  # Score numérico 0.0-1.0

    # Descrição do achado
    titulo = db.Column(db.String(300), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    evidencia = db.Column(db.Text)  # Dados que sustentam o achado

    # Justificativa regulatória
    regra_referencia = db.Column(db.String(100))  # Ex: "TISS 4.01 §3.2"
    norma_ans = db.Column(db.String(100))  # Ex: "RN 305/2012"
    base_legal = db.Column(db.Text)  # Descrição da base legal/regulatória

    # Impacto financeiro
    impacto_valor = db.Column(db.Numeric(12, 2))  # Valor estimado do impacto
    impacto_tipo = db.Column(db.String(30))  # perda_receita, glosa_indevida, subfaturamento

    # Recomendação
    acao_recomendada = db.Column(db.Text)

    # Controle
    resolvido = db.Column(db.Boolean, default=False)
    data_resolucao = db.Column(db.DateTime)
    observacao_resolucao = db.Column(db.Text)

    criado_em = db.Column(db.DateTime, default=utcnow, nullable=False)

    procedimento = db.relationship(
        "Procedimento",
        backref=db.backref("achados", lazy="dynamic"),
    )
    documento = db.relationship(
        "Documento",
        backref=db.backref("achados", lazy="dynamic"),
    )

    def to_dict(self):
        """Serializa o achado no formato padrão de resposta dos agentes."""
        return {
            "id": self.id,
            "agente": {
                "tipo": self.agente_tipo,
                "versao": self.agente_versao,
            },
            "classificacao": {
                "nivel": self.nivel,
                "confianca": self.confianca,
                "confianca_score": self.confianca_score,
            },
            "achado": {
                "titulo": self.titulo,
                "descricao": self.descricao,
                "evidencia": self.evidencia,
            },
            "justificativa": {
                "regra_referencia": self.regra_referencia,
                "norma_ans": self.norma_ans,
                "base_legal": self.base_legal,
            },
            "impacto_financeiro": {
                "valor_estimado": float(self.impacto_valor) if self.impacto_valor else None,
                "tipo": self.impacto_tipo,
            },
            "acao_recomendada": self.acao_recomendada,
            "status": {
                "resolvido": self.resolvido,
                "data_resolucao": (
                    self.data_resolucao.isoformat() if self.data_resolucao else None
                ),
            },
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }

    def __repr__(self):
        return f"<AchadoAuditoria [{self.nivel}] {self.titulo[:50]}>"
