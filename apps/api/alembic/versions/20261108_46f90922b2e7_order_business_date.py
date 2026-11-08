"""order business date

Adds ``orders.business_date`` (the calendar day in the workspace timezone) and backfills it.

Before this migration, imported wall-clock times were stored labelled as UTC. The backfill
treats the stored value as the shopkeeper's wall-clock time: ``business_date`` is its date, and
``order_date`` is corrected to the true UTC instant using the workspace's timezone.

Revision ID: 46f90922b2e7
Revises: 56799aeb0cfc
Create Date: 2026-11-08 12:50:16.933265
"""

from collections.abc import Sequence
from datetime import UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from alembic import op

revision: str = "46f90922b2e7"
down_revision: str | None = "56799aeb0cfc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BATCH = 2000


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def upgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(sa.Column("business_date", sa.Date(), nullable=True))

    bind = op.get_bind()
    orders = sa.table(
        "orders",
        sa.column("id", sa.Uuid()),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("order_date", sa.DateTime(timezone=True)),
        sa.column("business_date", sa.Date()),
    )
    workspaces = sa.table("workspaces", sa.column("id", sa.Uuid()), sa.column("timezone", sa.String()))
    zones = {row.id: _zone(row.timezone) for row in bind.execute(sa.select(workspaces))}

    rows = bind.execute(sa.select(orders.c.id, orders.c.workspace_id, orders.c.order_date)).all()
    for i in range(0, len(rows), _BATCH):
        for row in rows[i : i + _BATCH]:
            wall = row.order_date.replace(tzinfo=None)
            zone = zones.get(row.workspace_id, ZoneInfo("UTC"))
            utc = wall.replace(tzinfo=zone).astimezone(UTC)
            bind.execute(
                orders.update()
                .where(orders.c.id == row.id)
                .values(business_date=wall.date(), order_date=utc)
            )

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.alter_column("business_date", existing_type=sa.Date(), nullable=False)
        batch_op.create_index(
            "ix_orders_workspace_id_business_date", ["workspace_id", "business_date"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_index("ix_orders_workspace_id_business_date")
        batch_op.drop_column("business_date")


