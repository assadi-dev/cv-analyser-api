"""
ORM models package.

Import all models here so Alembic can discover them.
"""

from app.models.analyse import Analyse
from app.models.candidature import Candidature
from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage
from app.models.contact import Contact
from app.models.cv import CV
from app.models.kanban import Kanban
from app.models.preference import Preference
from app.models.user import User

__all__ = [
    "User",
    "Preference",
    "CV",
    "Candidature",
    "Contact",
    "Analyse",
    "ChatConversation",
    "ChatMessage",
    "Kanban",
]
