"""Remember a confirmed column mapping so the same file layout is recognised next time."""

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source import MappingProfile
from app.services.ingestion.fields import normalise_header


def fingerprint(headers: list[str]) -> str:
    """Order- and case-insensitive identity of a file layout."""
    norm = sorted({normalise_header(h) for h in headers if h and h.strip()})
    return hashlib.sha256("|".join(norm).encode()).hexdigest()


def find(db: Session, ws: uuid.UUID, headers: list[str]) -> MappingProfile | None:
    return db.scalars(
        select(MappingProfile).where(
            MappingProfile.workspace_id == ws, MappingProfile.fingerprint == fingerprint(headers)
        )
    ).first()


def remember(
    db: Session, ws: uuid.UUID, headers: list[str], mapping: dict[str, Any], name: str
) -> MappingProfile:
    """Save (or update) the mapping for this layout. The caller commits."""
    prof = find(db, ws, headers)
    if prof is None:
        prof = MappingProfile(
            workspace_id=ws, fingerprint=fingerprint(headers), name=name[:200], mapping=mapping
        )
        db.add(prof)
    else:
        prof.mapping = mapping
    return prof


def usable(profile: MappingProfile, headers: list[str]) -> dict[str, Any] | None:
    """The remembered mapping if every column it names is still in the file."""
    fields = profile.mapping.get("fields", {})
    if not fields or any(col not in headers for col in fields.values()):
        return None
    return profile.mapping


def mark_used(profile: MappingProfile) -> None:
    profile.uses += 1
    profile.last_used_at = datetime.now(UTC)
