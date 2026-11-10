"""A shop's own documents (policies, supplier terms, SOPs) split into searchable passages."""

import uuid

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class Document(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(8))  # pdf | docx | text
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    pages: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    embed_model: Mapped[str] = mapped_column(String(100), default="")
    # Who may read it. Search filters on this BEFORE ranking, so a restricted passage is never scored.
    min_role: Mapped[str] = mapped_column(String(10), default="viewer")
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.position"
    )


class DocumentChunk(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, Base):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[bytes] = mapped_column(LargeBinary)  # float32, unit length

    document: Mapped[Document] = relationship(back_populates="chunks")
