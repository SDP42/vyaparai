"""Import every model here so Alembic autogenerate and ``Base.metadata`` see them."""

from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.commerce import Customer, Order, OrderItem, OrderStatus, Product
from app.models.dataset import Dataset, DatasetStatus, Job, JobStatus, JobType
from app.models.digest import Digest, DigestSettings
from app.models.forecast import ForecastRun, ForecastSeries
from app.models.user import User
from app.models.weather import WeatherDaily
from app.models.workspace import Membership, Workspace, WorkspaceRole

__all__ = [
    "Alert",
    "AuditLog",
    "Customer",
    "Dataset",
    "DatasetStatus",
    "Digest",
    "DigestSettings",
    "ForecastRun",
    "ForecastSeries",
    "Job",
    "JobStatus",
    "JobType",
    "Membership",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Product",
    "User",
    "WeatherDaily",
    "Workspace",
    "WorkspaceRole",
]
