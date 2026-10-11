import uuid

from pydantic import BaseModel, Field


class LandscapeRequest(BaseModel):
    keywords: str = Field(min_length=2, max_length=200, description="The technology area")
    invention: str | None = Field(
        default=None, max_length=4000, description="Your invention, described in words"
    )
    document_id: uuid.UUID | None = Field(default=None, description="...or a library document")
    patent_id: uuid.UUID | None = Field(default=None, description="...or an imported patent")
    include_library: bool = True
    limit: int = Field(default=60, ge=10, le=100)


class LandscapePointOut(BaseModel):
    key: str
    kind: str
    label: str
    title: str
    applicants: list[str]
    date: str | None
    abstract: str
    url: str | None
    source: str | None
    full_text_likely: bool
    in_library: bool
    x: float
    y: float
    cluster: int | None
    similarity: float | None
    closest: bool


class LandscapeClusterOut(BaseModel):
    id: int
    name: str
    size: int


class LandscapeInventionOut(BaseModel):
    label: str
    x: float
    y: float


class LandscapeOut(BaseModel):
    query: str
    method: str = Field(description="t-SNE or PCA: how 1,024 dimensions were drawn in two")
    points: list[LandscapePointOut]
    clusters: list[LandscapeClusterOut]
    invention: LandscapeInventionOut | None
    found: int
    notes: list[str]
