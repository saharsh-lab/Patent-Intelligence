"""Patent landscape map: a technology area in two dimensions (Phase 16)."""

from fastapi import APIRouter

from app.api.deps import EmbedderDep, PatentServiceDep, SessionDep
from app.core.errors import ValidationFailedError
from app.core.ownership import visible
from app.intelligence.landscape import build_landscape
from app.models import Document
from app.schemas.landscape import LandscapeOut, LandscapeRequest

router = APIRouter(prefix="/landscape", tags=["landscape"])


@router.post("", response_model=LandscapeOut)
def draw_landscape(
    body: LandscapeRequest, session: SessionDep, embedder: EmbedderDep, patents: PatentServiceDep
) -> LandscapeOut:
    """Search the patent offices for a topic and place every hit on a 2D map of meaning,
    grouped into clusters; optionally with the user's library and invention. Technical
    similarity only, not a legal assessment."""
    if body.document_id:
        document = session.get(Document, body.document_id)
        if document is None or not visible(document.owner_id):
            raise ValidationFailedError("That document is not in your library.")
    result = build_landscape(
        session,
        embedder,
        patents,
        keywords=body.keywords,
        invention=body.invention,
        document_id=body.document_id,
        patent_id=body.patent_id,
        include_library=body.include_library,
        limit=body.limit,
    )
    return LandscapeOut(**result.to_json())
