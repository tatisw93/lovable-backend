"""
Configuração central do serviço de auditoria médica.
"""
import os


class Config:
    """Configuração base."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///auditoria_medica.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/auditoria_uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload

    # Google Sheets (harmonização legada)
    GOOGLE_CREDENTIALS_FILE = os.environ.get(
        "GOOGLE_CREDENTIALS_FILE", "credentials.json"
    )
    GOOGLE_SHEET_NAME = os.environ.get(
        "GOOGLE_SHEET_NAME", "Base Harmonização Arvo"
    )

    # Limiares de confiança dos agentes
    CONFIANCA_ALTA = 0.85
    CONFIANCA_MEDIA = 0.60
    CONFIANCA_BAIXA = 0.30


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
