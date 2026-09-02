"""
Kanban router — the board read model.

Sits on its own prefix rather than under /candidatures: the board is its own
resource, and keeping it out of that router also removes the ordering trap
where a literal path competes with /candidatures/{candidature_id}.

Writes stay on the candidature: moving a card is a change to a candidature,
so drag & drop still goes through PATCH /candidatures/{id}/move.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.logging import get_logger
from app.schemas.candidature import KanbanBoardResponse
from app.services.candidature_services import CandidatureService

logger = get_logger(__name__)
router = APIRouter(prefix="/kanban", tags=["Kanban"])


@router.get(
    "",
    response_model=KanbanBoardResponse,
    summary="Get the Kanban board, grouped by column",
)
async def get_kanban_board(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> KanbanBoardResponse:
    """
    Returns the board as `{status: [cards]}`, ready to render.

    Cards arrive already grouped and ordered, so the client neither groups
    nor sorts — it cannot end up disagreeing with the API about the order of
    a column. Every column is present, empty ones included, so a column never
    disappears once its last card leaves.

    Not paginated: a board shows all of its cards.
    """
    service = CandidatureService(db)
    return await service.get_board(uuid.UUID(user_id))
