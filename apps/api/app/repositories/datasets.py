from app.models.audit import AuditLog
from app.models.dataset import Dataset, Job
from app.repositories.base import WorkspaceScopedRepository


class DatasetRepository(WorkspaceScopedRepository[Dataset]):
    model = Dataset


class JobRepository(WorkspaceScopedRepository[Job]):
    model = Job


class AuditLogRepository(WorkspaceScopedRepository[AuditLog]):
    model = AuditLog
