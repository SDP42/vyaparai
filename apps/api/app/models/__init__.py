"""Import every model here so Alembic autogenerate and ``Base.metadata`` see them."""

from app.models.audit import AuditLog
from app.models.commerce import Customer, Order, OrderItem, OrderStatus, Product
from app.models.dataset import Dataset, DatasetStatus, Job, JobStatus, JobType
from app.models.user import User
from app.models.workspace import Membership, Workspace, WorkspaceRole

__all__ = [
    "AuditLog",
    "Customer",
    "Dataset",
    "DatasetStatus",
    "Job",
    "JobStatus",
    "JobType",
    "Membership",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Product",
    "User",
    "Workspace",
    "WorkspaceRole",
]
