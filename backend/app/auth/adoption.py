"""When accounts are switched on for an installation that was used without them, the
first account to register adopts everything created before (documents, questions,
conversations, watches). Later accounts start empty."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.auth.models import User
from app.models import Conversation, Document, PatentWatch, Query


def adopt_unowned_data(auth_session: Session, data_session: Session, user_id: uuid.UUID) -> int:
    """Give the first user ownership of pre-account data. Returns the documents adopted."""
    if auth_session.scalar(select(func.count(User.id))) != 1:
        return 0
    adopted = 0
    for model in (Document, Query, Conversation, PatentWatch):
        result = data_session.execute(
            update(model).where(model.owner_id.is_(None)).values(owner_id=user_id)
        )
        if model is Document:
            adopted = result.rowcount or 0
    data_session.commit()
    return adopted
