"""Patent monitoring: saved searches that find newly published patents."""

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import WatchServiceDep
from app.schemas.watches import WatchCheckOut, WatchCreate, WatchHitOut, WatchOut

router = APIRouter(prefix="/watches", tags=["monitoring"])


def _out(service, watch) -> WatchOut:
    return WatchOut.from_model(watch, service.unseen_count(watch.id))


@router.post("", response_model=WatchOut, status_code=status.HTTP_201_CREATED)
def create_watch(body: WatchCreate, service: WatchServiceDep):
    watch = service.create(
        name=body.name,
        keywords=body.keywords,
        cpc=body.cpc,
        reference_document_id=body.reference_document_id,
        import_top=body.import_top,
        lookback_days=body.lookback_days,
    )
    return _out(service, watch)


@router.get("", response_model=list[WatchOut])
def list_watches(service: WatchServiceDep):
    return [_out(service, w) for w in service.list_watches()]


@router.get("/{watch_id}/hits", response_model=list[WatchHitOut])
def watch_hits(watch_id: uuid.UUID, service: WatchServiceDep):
    return [WatchHitOut.from_model(h) for h in service.get(watch_id).hits]


@router.post("/{watch_id}/check", response_model=WatchCheckOut)
def check_watch(watch_id: uuid.UUID, service: WatchServiceDep):
    """Search now for publications since the last check (patent API calls: rate-limited)."""
    o = service.check(watch_id)
    return WatchCheckOut(
        watch_id=o.watch_id, new_hits=o.new_hits, imported=o.imported, error=o.error
    )


@router.post("/{watch_id}/seen", status_code=status.HTTP_204_NO_CONTENT)
def mark_seen(watch_id: uuid.UUID, service: WatchServiceDep):
    service.get(watch_id)
    service.mark_seen(watch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{watch_id}", response_model=WatchOut)
def set_active(watch_id: uuid.UUID, active: bool, service: WatchServiceDep):
    return _out(service, service.set_active(watch_id, active))


@router.delete("/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watch(watch_id: uuid.UUID, service: WatchServiceDep):
    service.delete(watch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
