"""
Configuração base do SQLAlchemy.
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)
