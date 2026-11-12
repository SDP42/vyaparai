"""Import every model here so Alembic autogenerate and ``Base.metadata`` see them."""

from app.models.agent import AgentRun, AgentSchedule, AgentStep
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.bill import PurchaseBill, PurchaseBillLine
from app.models.campaign import Campaign, CampaignRecipient, CustomerContact
from app.models.commerce import Customer, Order, OrderItem, OrderStatus, Product
from app.models.credit import CreditEntry
from app.models.daily import DayClose, Expense, ExpiryItem
from app.models.dataset import Dataset, DatasetStatus, Job, JobStatus, JobType
from app.models.digest import Digest, DigestSettings
from app.models.document import Document, DocumentChunk
from app.models.forecast import ForecastRun, ForecastSeries
from app.models.goal import Goal
from app.models.inventory import InventorySetting, StockSnapshot
from app.models.recommendation import Recommendation
from app.models.report import SavedReport
from app.models.review import Review
from app.models.session import Invitation, RefreshToken
from app.models.source import ImportSource, MappingProfile, SourceRun
from app.models.user import User
from app.models.weather import WeatherDaily
from app.models.workspace import Membership, Workspace, WorkspaceRole

__all__ = [
    "AgentRun",
    "AgentSchedule",
    "AgentStep",
    "Alert",
    "AuditLog",
    "Campaign",
    "CampaignRecipient",
    "CreditEntry",
    "Customer",
    "CustomerContact",
    "Dataset",
    "DatasetStatus",
    "DayClose",
    "Digest",
    "DigestSettings",
    "Document",
    "DocumentChunk",
    "Expense",
    "ExpiryItem",
    "ForecastRun",
    "ForecastSeries",
    "Goal",
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
    "PurchaseBill",
    "PurchaseBillLine",
    "Recommendation",
    "RefreshToken",
    "Review",
    "SavedReport",
    "SourceRun",
    "StockSnapshot",
    "User",
    "WeatherDaily",
    "Workspace",
    "WorkspaceRole",
]
