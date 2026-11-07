"""Workspace-scoped data access.

Every query for business-owned data goes through ``WorkspaceScopedRepository`` so the
``workspace_id`` filter can never be forgotten in a route handler.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base


class WorkspaceScopedRepository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, db: Session, workspace_id: uuid.UUID) -> None:
        self.db = db
        self.workspace_id = workspace_id

    def _scoped(self) -> Any:
        return select(self.model).where(self.model.workspace_id == self.workspace_id)  # type: ignore[attr-defined]

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        stmt = self._scoped().where(self.model.id == entity_id)  # type: ignore[attr-defined]
        result: ModelT | None = self.db.scalars(stmt).one_or_none()
        return result

    def list(self, *, limit: int = 50, offset: int = 0) -> Sequence[ModelT]:
        stmt = (
            self._scoped()
            .order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return self.db.scalars(stmt).all()

    def count(self) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.workspace_id == self.workspace_id)  # type: ignore[attr-defined]
        )
        return int(self.db.scalar(stmt) or 0)
