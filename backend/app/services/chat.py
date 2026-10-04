"""Chat conversations with memory and attached documents.

Memory works by **rewriting**, not by pasting the chat into the answer prompt:

    "What does claim 2 add?"  +  conversation so far
        → LLM rewrites it as a standalone question
          ("What does claim 2 of the wireless charging patent US9178361B2 add?")
        → the normal pipeline: retrieve → answer from evidence → verify each sentence

So earlier turns decide *what is asked*, but every answer is still built only from
retrieved passages and verified against them; the conversation itself is never treated
as evidence. The rewritten question is stored and shown ("Understood as: …").

Documents attached to a conversation scope its answers ("talk to this document").
Everything is owned by a user: conversations, attached documents, and the runs.
"""

import logging
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationFailedError
from app.llm.providers import ChatMessage, LLMProvider
from app.models import AgentRun, Document, Patent, Query
from app.models.conversation import DEFAULT_TITLE, Conversation
from app.patents.base import PatentSource
from app.rag.embeddings import EmbeddingProvider
from app.services.agent import AgentService
from app.services.answering import AnswerService
from app.services.documents import DocumentService

logger = logging.getLogger(__name__)

HISTORY_TURNS = 4  # previous question/answer pairs given to the rewriter
ANSWER_CHARS = 500  # each previous answer is shortened to this for the rewriter

_REWRITE_PROMPT = """\
You turn the user's latest message into a standalone question for a patent search
system. Use the conversation only to resolve references such as "it", "this patent",
"the second one", "claim 2" or "what about cooling?". Keep publication numbers, claim
numbers and technical terms exactly. If the message is already standalone, return it
unchanged. Do not answer the question. Reply with ONLY the question."""


class ChatService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
        patent_sources: dict[str, PatentSource],
        *,
        owner_id: uuid.UUID | None,
        pipeline: str = "agentic",
    ):
        self.session = session
        self.settings = settings
        self.embedder = embedder
        self.llm = llm
        self.sources = patent_sources
        self.owner_id = owner_id
        self.pipeline = pipeline

    # ------------------------------------------------------------------ conversations

    def create(self, title: str | None = None) -> Conversation:
        conversation = Conversation(
            owner_id=self.owner_id, title=(title or "").strip()[:200] or DEFAULT_TITLE
        )
        self.session.add(conversation)
        self.session.commit()
        return conversation

    def list_conversations(self) -> list[Conversation]:
        return list(
            self.session.scalars(
                select(Conversation)
                .where(self._owned(Conversation.owner_id))
                .order_by(Conversation.updated_at.desc())
            )
        )

    def get(self, conversation_id: uuid.UUID) -> Conversation:
        conversation = self.session.get(Conversation, conversation_id)
        if conversation is None or conversation.owner_id != self.owner_id:
            raise NotFoundError("Conversation not found.")  # same answer for "not yours"
        return conversation

    def rename(self, conversation_id: uuid.UUID, title: str) -> Conversation:
        conversation = self.get(conversation_id)
        title = " ".join(title.split())[:200]
        if not title:
            raise ValidationFailedError("Enter a title.")
        conversation.title = title
        self.session.commit()
        return conversation

    def delete(self, conversation_id: uuid.UUID) -> None:
        """Deletes the conversation and its messages (runs); attached documents stay."""
        conversation = self.get(conversation_id)
        self.session.execute(delete(Query).where(Query.conversation_id == conversation.id))
        self.session.delete(conversation)
        self.session.commit()

    # ------------------------------------------------------------------ documents

    # Attached sources are stored as "<document uuid>" or "patent:<patent uuid>"
    def documents(self, conversation: Conversation) -> list[Document]:
        ids = [uuid.UUID(i) for i in conversation.document_ids or [] if ":" not in i]
        if not ids:
            return []
        found = {
            d.id: d
            for d in self.session.scalars(
                select(Document).where(Document.id.in_(ids), self._owned(Document.owner_id))
            )
        }
        return [found[i] for i in ids if i in found]  # skips documents deleted since

    def patents(self, conversation: Conversation) -> list[Patent]:
        ids = [
            uuid.UUID(i.split(":", 1)[1])
            for i in conversation.document_ids or []
            if i.startswith("patent:")
        ]
        found = {p.id: p for p in self.session.scalars(select(Patent).where(Patent.id.in_(ids)))}
        return [found[i] for i in ids if i in found]

    def attach_existing(
        self,
        conversation_id: uuid.UUID,
        *,
        document_id: uuid.UUID | None = None,
        patent_id: uuid.UUID | None = None,
    ) -> Conversation:
        """Attach a document from the user's library, or an imported (public) patent."""
        conversation = self.get(conversation_id)
        if document_id is not None:
            document = self.session.get(Document, document_id)
            if document is None or document.owner_id != self.owner_id or document.status != "ready":
                raise NotFoundError("Document not found.")
            key, label = str(document.id), document.title or document.filename
        elif patent_id is not None:
            patent = self.session.get(Patent, patent_id)
            if patent is None:
                raise NotFoundError("Patent not found.")
            key, label = f"patent:{patent.id}", patent.title or patent.publication_number
        else:
            raise ValidationFailedError("Choose a document or a patent.")
        if key not in (conversation.document_ids or []):
            conversation.document_ids = [*(conversation.document_ids or []), key]
        if conversation.title == DEFAULT_TITLE:
            conversation.title = label[:200]
        conversation.updated_at = datetime.now(UTC)
        self.session.commit()
        return conversation

    def attach_upload(
        self, conversation_id: uuid.UUID, filename: str | None, data: bytes
    ) -> tuple[Document, bool]:
        conversation = self.get(conversation_id)
        documents = DocumentService(self.session, self.settings, self.embedder)
        document, created = documents.upload(filename, data)
        conversation = self.get(conversation_id)  # the upload committed
        if str(document.id) not in (conversation.document_ids or []):
            conversation.document_ids = [*(conversation.document_ids or []), str(document.id)]
        if conversation.title == DEFAULT_TITLE:
            conversation.title = (document.title or document.filename)[:200]
        conversation.updated_at = datetime.now(UTC)
        self.session.commit()
        return document, created

    def detach(self, conversation_id: uuid.UUID, document_id: uuid.UUID) -> None:
        conversation = self.get(conversation_id)
        keys = {str(document_id), f"patent:{document_id}"}
        conversation.document_ids = [i for i in conversation.document_ids or [] if i not in keys]
        self.session.commit()

    # ------------------------------------------------------------------ messages

    def messages(self, conversation: Conversation) -> list[AgentRun]:
        return list(
            self.session.scalars(
                select(AgentRun)
                .join(AgentRun.query)
                .where(Query.conversation_id == conversation.id)
                .order_by(AgentRun.started_at)
            )
        )

    def send(self, conversation_id: uuid.UUID, message: str) -> AgentRun:
        conversation = self.get(conversation_id)
        message = message.strip()
        if not message:
            raise ValidationFailedError("Type a message.")
        history = self.messages(conversation)[-HISTORY_TURNS:]
        standalone = self.rewrite(message, history)
        documents = [d.id for d in self.documents(conversation) if d.status == "ready"]
        patents = [p.id for p in self.patents(conversation)]

        service = self._service()
        # The owner is applied by the request's owner scope (app/core/ownership.py)
        run = service.ask(
            standalone,
            document_ids=documents or None,
            patent_ids=patents or None,
            conversation_id=conversation.id,
        )
        run = self.session.get(AgentRun, run.id)
        run.query.meta = {
            **(run.query.meta or {}),
            "user_message": message,
            "interpreted_as": standalone if standalone != message else None,
        }
        conversation = self.get(conversation_id)
        if conversation.title == DEFAULT_TITLE:
            conversation.title = _title_from(message)
        conversation.updated_at = datetime.now(UTC)
        self.session.commit()
        return run

    def rewrite(self, message: str, history: list[AgentRun]) -> str:
        """Standalone version of a follow-up question (unchanged if there is no history,
        no real LLM, or the rewrite looks wrong)."""
        if not history or self.settings.llm_provider == "fake":
            return message
        turns = []
        for run in history:
            question = (run.query.meta or {}).get("user_message") or run.query.query_text
            answer = (run.answer_text or "(no answer: insufficient evidence)")[:ANSWER_CHARS]
            turns.append(f"User: {question}\nAssistant: {answer}")
        prompt = "\n\n".join(turns) + f"\n\nLatest user message: {message}"
        try:
            response = self.llm.complete(
                [ChatMessage("system", _REWRITE_PROMPT), ChatMessage("user", prompt)],
                temperature=0.0,
                max_tokens=120,
            )
        except Exception as exc:  # noqa: BLE001 - memory is a convenience, never a failure
            logger.info("Question rewrite failed (%s); using the message as is", type(exc).__name__)
            return message
        return _accept_rewrite(message, response.text)

    # ------------------------------------------------------------------ helpers

    def _service(self) -> AnswerService:
        if self.pipeline == "baseline":
            return AnswerService(self.session, self.settings, self.embedder, self.llm)
        return AgentService(self.session, self.settings, self.embedder, self.llm, self.sources)

    def _owned(self, column):
        return column.is_(None) if self.owner_id is None else column == self.owner_id


def _accept_rewrite(original: str, text: str) -> str:
    """Guard against rewriters that answer, ramble or return nothing."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()
    text = re.sub(r"^(standalone question|question)\s*:\s*", "", text.strip(), flags=re.IGNORECASE)
    text = text.strip().strip('"').strip()
    if not text or len(text) > max(300, 3 * len(original)) or "\n\n" in text:
        return original
    return text


def _title_from(message: str) -> str:
    title = " ".join(message.split())
    return title if len(title) <= 60 else title[:57].rsplit(" ", 1)[0] + "…"
