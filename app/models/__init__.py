"""
ORM models package.

Import all models here so Alembic can discover them.
"""

from app.models.analyse import Analyse
from app.models.candidature import Candidature
from app.models.contact import Contact
from app.models.cv import CV
from app.models.user import User

__all__ = ["User", "CV", "Candidature", "Contact", "Analyse"]
