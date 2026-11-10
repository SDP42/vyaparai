"""Documents: upload policies, terms and procedures, then search them with cited passages."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status
from pydantic import BaseModel, Field

from app.api.deps import AdminCtx, AnalystCtx, DbSession, ViewerCtx
from app.core.errors import PermissionDeniedError
from app.models.document import Document
from app.models.workspace import WorkspaceRole
from app.services.docs import extract, service

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    k: int = Field(default=4, ge=1, le=10)


def _doc(d: Document) -> dict[str, Any]:
    return {
        "id": str(d.id), "title": d.title, "filename": d.filename, "kind": d.kind, "pages": d.pages,
        "chunks": d.chunk_count, "min_role": d.min_role, "created_at": d.created_at.isoformat(),
    }  # fmt: skip


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload(
    ctx: AnalystCtx,
    db: DbSession,
    file: Annotated[UploadFile, File()],
    min_role: Annotated[str, Form()] = "viewer",
) -> dict[str, Any]:
    if min_role not in {r.value for r in WorkspaceRole} or not ctx.role.at_least(
        WorkspaceRole(min_role)
    ):
        raise PermissionDeniedError("You cannot set an access level above your own")
    content = await file.read(extract.MAX_BYTES + 1)
    doc = service.add_document(
        db, ctx.workspace_id, ctx.user.id, file.filename or "document", content, min_role
    )
    return _doc(doc)


@router.get("")
def list_documents(ctx: ViewerCtx, db: DbSession) -> list[dict[str, Any]]:
    return [_doc(d) for d in service.listing(db, ctx.workspace_id, ctx.role)]


@router.post("/search")
def search(data: SearchIn, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return service.search(db, ctx.workspace_id, ctx.role, data.query, data.k)


@router.get("/{doc_id}")
def get_document(
    doc_id: uuid.UUID,
    ctx: ViewerCtx,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    d = service.get(db, ctx.workspace_id, doc_id, ctx.role)
    return {
        **_doc(d),
        "passages": [
            {"page": c.page, "section": c.section, "text": c.text} for c in d.chunks[:limit]
        ],
    }


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: uuid.UUID, ctx: AdminCtx, db: DbSession) -> Response:
    service.remove(db, service.get(db, ctx.workspace_id, doc_id, ctx.role), ctx.user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
