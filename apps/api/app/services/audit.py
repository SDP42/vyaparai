import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import request_id_ctx
from app.models.audit import AuditLog


def record(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | None,
    workspace_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Add an audit entry to the current transaction (caller commits)."""
    entry = AuditLog(
        action=action,
        actor_user_id=actor_user_id,
        workspace_id=workspace_id,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details,
        request_id=request_id_ctx.get(),
    )
    db.add(entry)
    return entry
