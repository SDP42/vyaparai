"""Import every model here so Alembic autogenerate and ``Base.metadata`` see them."""

from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.commerce import Customer, Order, OrderItem, OrderStatus, Product
from app.models.dataset import Dataset, DatasetStatus, Job, JobStatus, JobType
from app.models.digest import Digest, DigestSettings
from app.models.forecast import ForecastRun, ForecastSeries
from app.models.inventory import InventorySetting, StockSnapshot
from app.models.review import Review
from app.models.session import Invitation, RefreshToken
from app.models.source import ImportSource, MappingProfile, SourceRun
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
    "ImportSource",
    "InventorySetting",
    "Invitation",
    "Job",
    "JobStatus",
    "JobType",
    "MappingProfile",
    "Membership",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Product",
    "RefreshToken",
    "Review",
    "SourceRun",
    "StockSnapshot",
    "User",
    "WeatherDaily",
    "Workspace",
    "WorkspaceRole",
]
