"""SQLAlchemy ORM models (database tables).

Importing this package registers every table on `Base.metadata`, which Alembic
uses to generate and check migrations.
"""

from app.models.base import Base
from app.models.conversation import Conversation
from app.models.corpus import ApiCache, Chunk, Document, Patent
from app.models.runs import (
    AgentRun,
    ClaimVerification,
    Evaluation,
    Query,
    RetrievalResult,
    ToolCall,
)
from app.models.watch import PatentWatch, WatchHit

__all__ = [
    "AgentRun",
    "ApiCache",
    "Base",
    "Chunk",
    "ClaimVerification",
    "Conversation",
    "Document",
    "Evaluation",
    "Patent",
    "PatentWatch",
    "Query",
    "RetrievalResult",
    "ToolCall",
    "WatchHit",
]
