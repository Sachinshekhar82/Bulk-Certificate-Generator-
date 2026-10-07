import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Date,
    DateTime,
    Text,
    Enum as SAEnum,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from app.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class ItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    FAILED = "FAILED"


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CertificateJob(Base):
    """Represents a bulk certificate generation request job."""
    __tablename__ = "certificate_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_name = Column(String(255), nullable=False)
    issuer_name = Column(String(255), nullable=False)
    issue_date = Column(Date, nullable=False)
    template_title = Column(String(255), default="Certificate of Completion", nullable=False)
    description = Column(Text, nullable=True)

    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    total_count = Column(Integer, default=0, nullable=False)
    processed_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    items = relationship("JobItem", back_populates="job", cascade="all, delete-orphan", order_by="JobItem.created_at")
    certificates = relationship("Certificate", back_populates="job", cascade="all, delete-orphan")


class JobItem(Base):
    """Represents an individual recipient task within a bulk job."""
    __tablename__ = "job_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("certificate_jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_metadata = Column(JSON, nullable=True)

    status = Column(SAEnum(ItemStatus), default=ItemStatus.PENDING, nullable=False, index=True)
    certificate_id = Column(String(64), nullable=True, unique=True, index=True)
    file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    job = relationship("CertificateJob", back_populates="items")
    certificate = relationship("Certificate", back_populates="job_item", uselist=False)


class Certificate(Base):
    """Represents a generated certificate with verification credentials."""
    __tablename__ = "certificates"

    id = Column(String(64), primary_key=True)  # Formatted ID e.g. CERT-2026-XXXX
    job_id = Column(String(36), ForeignKey("certificate_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    job_item_id = Column(String(36), ForeignKey("job_items.id", ondelete="SET NULL"), nullable=True, unique=True)

    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    event_name = Column(String(255), nullable=False)
    issuer_name = Column(String(255), nullable=False)
    issue_date = Column(Date, nullable=False)

    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA256 integrity hash
    verification_url = Column(String(500), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("CertificateJob", back_populates="certificates")
    job_item = relationship("JobItem", back_populates="certificate")
