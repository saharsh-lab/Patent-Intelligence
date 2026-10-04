"""Patent search (external sources) and imported-patent management."""

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import PatentServiceDep, SettingsDep
from app.patents.base import PatentQuery
from app.patents.registry import source_statuses
from app.schemas.patents import (
    PatentImportRequest,
    PatentImportResponse,
    PatentOut,
    PatentResultOut,
    PatentSearchRequest,
    PatentSearchResponse,
    SourceOutcomeOut,
    SourceStatusOut,
)

router = APIRouter(prefix="/patents", tags=["patents"])


@router.get("/sources", response_model=list[SourceStatusOut])
def list_sources(settings: SettingsDep) -> list[SourceStatusOut]:
    return [SourceStatusOut(**vars(s)) for s in source_statuses(settings)]


@router.post("/search", response_model=PatentSearchResponse)
def search_patents(body: PatentSearchRequest, service: PatentServiceDep) -> PatentSearchResponse:
    query = PatentQuery(
        keywords=body.keywords,
        cpc=body.cpc,
        applicant=body.applicant,
        date_from=body.date_from,
        date_to=body.date_to,
        limit=body.limit,
    )
    outcome = service.search(
        query,
        body.sources,
        dedup=body.dedup,
        reference_document_id=body.rank_against_document_id,
        reference_patent_id=body.rank_against_patent_id,
    )
    return PatentSearchResponse(
        results=[PatentResultOut.from_item(item) for item in outcome.results],
        sources=[SourceOutcomeOut(**vars(s)) for s in outcome.sources],
        deduplicated=outcome.deduplicated,
        reference_label=outcome.reference_label,
    )


@router.post("/import", response_model=PatentImportResponse, status_code=status.HTTP_201_CREATED)
def import_patent(
    body: PatentImportRequest, service: PatentServiceDep, response: Response
) -> PatentImportResponse:
    patent, created = service.import_patent(body.source, body.publication_number)
    if not created:
        response.status_code = status.HTTP_200_OK
    return PatentImportResponse(patent=PatentOut.from_model(patent), already_imported=not created)


@router.get("", response_model=list[PatentOut])
def list_imported(service: PatentServiceDep) -> list[PatentOut]:
    return [PatentOut.from_model(p) for p in service.list_imported()]


@router.get("/{patent_id}", response_model=PatentOut)
def get_patent(patent_id: uuid.UUID, service: PatentServiceDep) -> PatentOut:
    return PatentOut.from_model(service.get(patent_id))


@router.delete("/{patent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patent(patent_id: uuid.UUID, service: PatentServiceDep) -> None:
    service.delete(patent_id)
