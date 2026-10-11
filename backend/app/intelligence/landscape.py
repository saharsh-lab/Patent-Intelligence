"""Patent landscape map (Phase 16): a 2D picture of a technology area.

Each patent found for a topic (title + abstract, from the patent office, nothing
imported) becomes a point; patents and documents in the user's library can be added;
an invention (a library document or a pasted description) is drawn as a star.

    vectors     BGE-M3 embeddings of the same texts used to rank search results
    clusters    k-means in the full embedding space (k from the number of patents)
    positions   t-SNE to 2D when scikit-learn is installed, else PCA (numpy)
    closest     the five patents with the highest cosine similarity to the invention

Nearby points describe similar technology; the 2D distances are approximate (a 1,024-
dimensional space flattened to two), and the closeness is semantic, not legal.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailedError
from app.core.ownership import restrict
from app.intelligence.similarity import invention_text, record_text
from app.models import Chunk, Document, Patent
from app.patents.base import PatentQuery
from app.rag.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)

CLOSEST = 5
MIN_POINTS = 5

# Words that name the kind of patent or its boilerplate, not the technology. Observed
# (2026-10-11, "battery immersion cooling"): the first names were "invention, control,
# operation" and "utility, model, module", from "The invention relates to..." and "The
# utility model discloses..." in Chinese filings' abstracts.
_STOP = set(
    """invention utility model discloses disclosed relates related relating provides provided
    providing present embodiment embodiments technical field effect effects application
    applications solution problem therefore according corresponding respectively arranged
    connected fixedly mounted installed part parts body end side structure assembly formed
    efficient effectively improve improved improving high low good simple convenient reduce
    reduced reducing ensure ensures ensuring thereby wherein comprises comprising comprise
    include includes including used using use based method methods system systems device
    devices apparatus unit units module modules plurality first second third one two three
    set sets main new same such each other further also than then when where which while
    with without within between into onto from that this these those have has having been
    being are was were its their the and for of to in on at by or an a can may be is as so
    not thereof therefor means configured least more less via""".split()
)
_WORD = re.compile(r"[a-z][a-z\-]{2,}")


@dataclass
class LandscapePoint:
    key: str
    kind: str  # "patent" (found for the topic) | "library_patent" | "library_document"
    label: str
    title: str
    applicants: list[str] = field(default_factory=list)
    date: str | None = None
    abstract: str = ""
    url: str | None = None
    source: str | None = None
    full_text_likely: bool = False
    in_library: bool = False
    x: float = 0.0
    y: float = 0.0
    cluster: int | None = None
    similarity: float | None = None  # to the invention, when there is one
    closest: bool = False


@dataclass
class LandscapeResult:
    query: str
    method: str
    points: list[LandscapePoint]
    clusters: list[dict]
    invention: dict | None
    found: int  # patents returned by the patent office before filtering
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "query": self.query,
            "method": self.method,
            "points": [asdict(p) for p in self.points],
            "clusters": self.clusters,
            "invention": self.invention,
            "found": self.found,
            "notes": self.notes,
        }


# ---------------------------------------------------------------- maths (no DB)


def normalise(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


def choose_k(n: int) -> int:
    """About one cluster per 10–15 patents, between 2 and 6 (1 for very few)."""
    if n < 8:
        return 1
    return int(min(6, max(2, round((n / 4) ** 0.5))))


def kmeans(vectors: np.ndarray, k: int, seed: int = 0, iterations: int = 60) -> np.ndarray:
    """k-means with k-means++ starts; fixed seed, so the same data gives the same map."""
    n = len(vectors)
    if k <= 1 or n <= k:
        return np.zeros(n, dtype=int)
    rng = np.random.default_rng(seed)
    centres = [vectors[rng.integers(n)]]
    for _ in range(1, k):
        distances = np.min([((vectors - c) ** 2).sum(axis=1) for c in centres], axis=0)
        total = distances.sum()
        pick = rng.choice(n, p=distances / total) if total > 0 else rng.integers(n)
        centres.append(vectors[pick])
    centres = np.array(centres)
    labels = np.zeros(n, dtype=int)
    for step in range(iterations):
        distances = ((vectors[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
        new = distances.argmin(axis=1)
        if step and (new == labels).all():
            break
        labels = new
        for j in range(k):
            members = vectors[labels == j]
            if len(members):
                centres[j] = members.mean(axis=0)
    # number clusters by size, largest first, so colours are stable
    order = [j for j, _ in Counter(labels.tolist()).most_common()]
    return np.array([order.index(j) for j in labels])


def project_2d(vectors: np.ndarray, seed: int = 0) -> tuple[np.ndarray, str]:
    """2D positions scaled to [-1, 1]. t-SNE keeps neighbours together; PCA (the
    fallback) keeps the two directions of largest spread."""
    n = len(vectors)
    method = "PCA"
    coords = None
    if n >= 10:
        try:
            from sklearn.manifold import TSNE

            coords = TSNE(
                n_components=2,
                perplexity=max(2.0, min(30.0, (n - 1) / 3)),
                init="pca",
                random_state=seed,
                metric="cosine",
            ).fit_transform(vectors)
            method = "t-SNE"
        except ImportError:
            coords = None
    if coords is None:
        centred = vectors - vectors.mean(axis=0)
        _, _, vt = np.linalg.svd(centred, full_matrices=False)
        coords = centred @ vt[:2].T
        if coords.shape[1] < 2:
            coords = np.hstack([coords, np.zeros((n, 1))])
    coords = coords - coords.mean(axis=0)
    scale = np.abs(coords).max() or 1.0
    return coords / scale, method


def _terms(text: str) -> set[str]:
    """Words and two-word phrases ("cold plate", "energy storage") without boilerplate;
    phrases never span punctuation ("Battery pack. Battery..." gives no "pack battery")."""
    out: set[str] = set()
    for segment in re.split(r"[.,;:()\[\]!?]", text.lower()):
        words = _WORD.findall(segment)
        out |= {w for w in words if w not in _STOP}
        out |= {
            f"{a} {b}"
            for a, b in zip(words, words[1:], strict=False)
            if a not in _STOP and b not in _STOP and a != b
        }
    return out


def cluster_names(texts: list[str], labels: np.ndarray, k: int) -> list[str]:
    """Two terms typical of each cluster: frequent inside it (in a quarter of its members
    or more) and more frequent there than across the whole map. A phrase replaces the word
    it contains when it scores at least 60% as well ("thermal" -> "thermal management")."""
    docs = [_terms(t) for t in texts]
    overall = Counter(term for d in docs for term in d)
    n = len(docs)
    names = []
    for j in range(k):
        members = [d for d, label in zip(docs, labels, strict=True) if label == j]
        inside = Counter(term for d in members for term in d)
        scores = {}
        for term, count in inside.items():
            share = count / len(members)
            lift = share - overall[term] / n
            if (share >= 0.25 or len(members) < 4) and (lift > 0 or k == 1):
                scores[term] = (lift if k > 1 else share) * share * (1.6 if " " in term else 1.0)
        chosen: list[str] = []
        for term in sorted(scores, key=lambda t: (-scores[t], t)):
            if " " not in term:
                phrases = [p for p in scores if " " in p and term in p.split()]
                best = max(phrases, key=lambda p: scores[p], default=None)
                if best and scores[best] >= 0.6 * scores[term]:
                    term = best
            if any(set(term.split()) & set(c.split()) for c in chosen):
                continue  # no repeated word across the two names
            chosen.append(term)
            if len(chosen) == 2:
                break
        names.append(", ".join(chosen) if chosen else f"group {j + 1}")
    return names


# ---------------------------------------------------------------- building a map


def _library_vectors(session: Session, keys: set[str]) -> list[tuple[LandscapePoint, list]]:
    """Mean chunk vector of each library document (the user's own) and imported patent."""
    out = []
    documents = session.execute(
        restrict(
            select(Document, func.avg(Chunk.embedding, type_=Chunk.embedding.type))
            .join(Chunk, Chunk.document_id == Document.id)
            .where(Chunk.embedding.is_not(None))
            .group_by(Document.id),
            Document.owner_id,
        )
    ).all()
    for document, vector in documents:
        out.append(
            (
                LandscapePoint(
                    key=f"doc:{document.id}",
                    kind="library_document",
                    label=document.filename,
                    title=document.title or document.filename,
                    in_library=True,
                ),
                vector,
            )
        )
    patents = session.execute(
        select(Patent, func.avg(Chunk.embedding, type_=Chunk.embedding.type))
        .join(Chunk, Chunk.patent_id == Patent.id)
        .where(Chunk.embedding.is_not(None))
        .group_by(Patent.id)
    ).all()
    for patent, vector in patents:
        if patent.publication_number in keys:
            continue  # already on the map as a search result (marked "in library")
        out.append(
            (
                LandscapePoint(
                    key=f"patent:{patent.id}",
                    kind="library_patent",
                    label=patent.publication_number,
                    title=patent.title or patent.publication_number,
                    applicants=list(patent.applicants or []),
                    in_library=True,
                ),
                vector,
            )
        )
    return out


def build_landscape(
    session: Session,
    embedder: EmbeddingProvider,
    patent_service,
    *,
    keywords: str,
    invention: str | None = None,
    document_id: uuid.UUID | None = None,
    patent_id: uuid.UUID | None = None,
    include_library: bool = True,
    limit: int = 60,
) -> LandscapeResult:
    notes: list[str] = []
    reference = None
    if document_id or patent_id:
        reference = invention_text(session, document_id=document_id, patent_id=patent_id)
    elif invention and invention.strip():
        reference = ("Your invention", invention.strip()[:4000])

    outcome = patent_service.search(
        PatentQuery(keywords=keywords, limit=limit),
        rank_by_relevance=True,
        rank_text=reference[1] if reference else keywords,
    )
    failed = [s for s in outcome.sources if s.error]
    if failed and len(failed) == len(outcome.sources):
        raise ValidationFailedError(
            "The patent office could not be reached: " + "; ".join(s.error for s in failed)
        )
    items = [i for i in outcome.results if (i.record.abstract or "").strip()]
    if len(items) < len(outcome.results):
        notes.append(f"{len(outcome.results) - len(items)} results without an abstract left out.")

    points = [
        LandscapePoint(
            key=f"{i.record.source}:{i.record.publication_number}",
            kind="patent",
            label=i.record.publication_number,
            title=i.record.title or i.record.publication_number,
            applicants=i.record.applicants[:3],
            date=i.record.publication_date.isoformat() if i.record.publication_date else None,
            abstract=(i.record.abstract or "")[:600],
            url=i.record.url,
            source=i.record.source,
            full_text_likely=i.full_text_likely,
            in_library=i.imported_id is not None,
        )
        for i in items
    ]
    texts = [record_text(i.record) for i in items]
    vectors = list(embedder.embed_documents(texts)) if texts else []

    if include_library:
        for point, vector in _library_vectors(session, {p.label for p in points}):
            points.append(point)
            vectors.append(list(vector))
            texts.append(point.title)

    patents_found = sum(p.kind == "patent" for p in points)
    if patents_found < MIN_POINTS:
        raise ValidationFailedError(
            f"Only {patents_found} patents with abstracts were found for "
            f'"{keywords}": too few for a map. Try broader keywords.'
        )

    matrix = normalise(np.array(vectors, dtype=float))
    star = None
    if reference:
        star = normalise(np.array([embedder.embed_documents([reference[1]])[0]], dtype=float))[0]
        similarities = matrix @ star
        for point, similarity in zip(points, similarities, strict=True):
            point.similarity = round(float(similarity), 4)
        for index in np.argsort(-similarities)[:CLOSEST]:
            points[int(index)].closest = True

    k = choose_k(len(points))
    labels = kmeans(matrix, k)
    for point, label in zip(points, labels, strict=True):
        point.cluster = int(label)
    names = cluster_names([f"{p.title}. {p.title}. {p.abstract[:300]}" for p in points], labels, k)

    stacked = matrix if star is None else np.vstack([matrix, star])
    coords, method = project_2d(stacked)
    for point, (x, y) in zip(points, coords[: len(points)], strict=True):
        point.x, point.y = round(float(x), 4), round(float(y), 4)

    clusters = [{"id": j, "name": names[j], "size": int((labels == j).sum())} for j in range(k)]
    invention_out = None
    if reference is not None:
        x, y = coords[-1]
        invention_out = {"label": reference[0], "x": round(float(x), 4), "y": round(float(y), 4)}
    return LandscapeResult(
        query=keywords,
        method=method,
        points=points,
        clusters=clusters,
        invention=invention_out,
        found=sum(s.returned for s in outcome.sources),
        notes=notes,
    )
