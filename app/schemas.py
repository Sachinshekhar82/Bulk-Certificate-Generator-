from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.models import JobStatus, ItemStatus


class RecipientInput(BaseModel):
    """Schema for individual recipient input."""
    name: str = Field(..., min_length=1, max_length=200, description="Recipient full name")
    email: EmailStr = Field(..., description="Recipient valid email address")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional custom metadata (score, grade, etc.)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Recipient name cannot be empty or only whitespace")
        return stripped


class CreateJobRequest(BaseModel):
    """Schema for creating a bulk certificate generation job."""
    event_name: str = Field(..., min_length=2, max_length=255, description="Name of the course, workshop, or event")
    issuer_name: str = Field(..., min_length=2, max_length=255, description="Name of issuing institution or organization")
    issue_date: Optional[date] = Field(default=None, description="Date of issuance (defaults to today if omitted)")
    template_title: Optional[str] = Field(default="Certificate of Completion", max_length=255, description="Certificate title")
    description: Optional[str] = Field(
        default="has successfully participated in and completed",
        max_length=500,
        description="Reason/achievement text displayed below recipient name",
    )
    recipients: List[RecipientInput] = Field(
        ...,
        min_length=1,
        description="List of recipients to generate certificates for",
    )

    @field_validator("event_name", "issuer_name")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or only whitespace")
        return stripped

    @field_validator("recipients")
    @classmethod
    def validate_recipients_batch(cls, v: List[RecipientInput]) -> List[RecipientInput]:
        if not v:
            raise ValueError("At least one recipient must be provided")
        if len(v) > 1000:
            raise ValueError("Batch exceeds maximum allowed limit of 1000 recipients")
        return v


class RecipientJobItemResponse(BaseModel):
    """Schema for itemized recipient status inside a job."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    recipient_name: str
    recipient_email: str
    recipient_metadata: Optional[Dict[str, Any]] = None
    status: ItemStatus
    certificate_id: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None


class JobSummaryResponse(BaseModel):
    """Summary representation of a generation job."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_name: str
    issuer_name: str
    issue_date: date
    template_title: str
    description: Optional[str] = None
    status: JobStatus
    total_count: int
    processed_count: int
    success_count: int
    failed_count: int
    progress_percentage: float = 0.0
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    status_url: str
    download_all_url: Optional[str] = None


class JobDetailResponse(JobSummaryResponse):
    """Detailed job status including recent/preview items."""
    items: List[RecipientJobItemResponse] = []


class PaginatedJobItemsResponse(BaseModel):
    """Paginated list of recipient items for a job."""
    job_id: str
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[RecipientJobItemResponse]


class CertificateVerifyResponse(BaseModel):
    """Response returned upon certificate verification."""
    certificate_id: str
    is_valid: bool
    recipient_name: str
    recipient_email: str
    event_name: str
    issuer_name: str
    issue_date: date
    file_hash: str
    created_at: datetime
    download_url: str


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    app: str
    version: str
    timestamp: datetime
