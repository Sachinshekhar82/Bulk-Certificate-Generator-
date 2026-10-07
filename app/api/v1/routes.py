import io
import math
import os
import zipfile
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Certificate, CertificateJob, JobItem, JobStatus, ItemStatus
from app.schemas import (
    CertificateVerifyResponse,
    CreateJobRequest,
    JobDetailResponse,
    JobSummaryResponse,
    PaginatedJobItemsResponse,
    RecipientJobItemResponse,
)
from app.services.job_processor import process_certificate_job

router = APIRouter(prefix="/certificates", tags=["Certificates"])


def _format_item_response(item: JobItem, base_url: str) -> RecipientJobItemResponse:
    """Helper to convert JobItem to response schema with download link."""
    download_url = (
        f"{base_url}/api/v1/certificates/{item.certificate_id}/download"
        if item.certificate_id and item.status == ItemStatus.GENERATED
        else None
    )
    return RecipientJobItemResponse(
        id=item.id,
        recipient_name=item.recipient_name,
        recipient_email=item.recipient_email,
        recipient_metadata=item.recipient_metadata,
        status=item.status,
        certificate_id=item.certificate_id,
        download_url=download_url,
        error_message=item.error_message,
        created_at=item.created_at,
        processed_at=item.processed_at,
    )


def _format_job_summary(job: CertificateJob, base_url: str) -> JobSummaryResponse:
    """Helper to calculate progress and links for a job."""
    progress = (
        round((job.processed_count / job.total_count) * 100.0, 2)
        if job.total_count > 0
        else 0.0
    )
    status_url = f"{base_url}/api/v1/certificates/jobs/{job.id}"
    download_all_url = (
        f"{base_url}/api/v1/certificates/jobs/{job.id}/download-all"
        if job.success_count > 0
        else None
    )
    return JobSummaryResponse(
        id=job.id,
        event_name=job.event_name,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        template_title=job.template_title,
        description=job.description,
        status=job.status,
        total_count=job.total_count,
        processed_count=job.processed_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        progress_percentage=progress,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        status_url=status_url,
        download_all_url=download_all_url,
    )


@router.post(
    "/jobs",
    response_model=JobSummaryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit bulk certificate generation job",
    description="Accepts a bulk list of recipients and metadata, creates a job, and schedules background processing.",
)
def create_certificate_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    issue_date = request.issue_date or date.today()

    # 1. Create Job record
    job = CertificateJob(
        event_name=request.event_name,
        issuer_name=request.issuer_name,
        issue_date=issue_date,
        template_title=request.template_title or "Certificate of Completion",
        description=request.description,
        status=JobStatus.PENDING,
        total_count=len(request.recipients),
        processed_count=0,
        success_count=0,
        failed_count=0,
    )
    db.add(job)
    db.flush()

    # 2. Bulk insert JobItems
    job_items = [
        JobItem(
            job_id=job.id,
            recipient_name=rec.name,
            recipient_email=rec.email,
            recipient_metadata=rec.metadata,
            status=ItemStatus.PENDING,
        )
        for rec in request.recipients
    ]
    db.bulk_save_objects(job_items)
    db.commit()
    db.refresh(job)

    # 3. Dispatch to background processor
    background_tasks.add_task(process_certificate_job, job.id)

    return _format_job_summary(job, settings.BASE_URL)


@router.get(
    "/jobs/{job_id}",
    response_model=JobDetailResponse,
    summary="Get job status and progress",
    description="Check status, progress percentage, metrics, and itemized results for a certificate generation job.",
)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found")

    summary = _format_job_summary(job, settings.BASE_URL)

    # Fetch items for detailed response
    items = db.query(JobItem).filter(JobItem.job_id == job_id).order_by(JobItem.created_at).all()
    formatted_items = [_format_item_response(it, settings.BASE_URL) for it in items]

    return JobDetailResponse(
        **summary.model_dump(),
        items=formatted_items,
    )


@router.get(
    "/jobs/{job_id}/items",
    response_model=PaginatedJobItemsResponse,
    summary="Get paginated list of recipient items for a job",
    description="Lists recipient items with optional status filter (PENDING, GENERATED, FAILED).",
)
def get_job_items(
    job_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    status_filter: Optional[ItemStatus] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
):
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found")

    query = db.query(JobItem).filter(JobItem.job_id == job_id)
    if status_filter:
        query = query.filter(JobItem.status == status_filter)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(JobItem.created_at).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedJobItemsResponse(
        job_id=job_id,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[_format_item_response(it, settings.BASE_URL) for it in items],
    )


@router.get(
    "/{certificate_id}/download",
    summary="Download an individual certificate PDF",
    description="Retrieves the generated PDF file for a given certificate ID.",
)
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found",
        )

    if not os.path.exists(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Certificate file is missing from storage disk",
        )

    safe_recipient_slug = "".join(c for c in cert.recipient_name if c.isalnum() or c in ("-", "_")).strip() or "certificate"
    filename = f"{cert.id}_{safe_recipient_slug}.pdf"

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/jobs/{job_id}/download-all",
    summary="Download all generated certificates as a ZIP archive",
    description="Bundles all successfully generated PDF certificates for a job into a downloadable ZIP archive.",
)
def download_all_certificates(job_id: str, db: Session = Depends(get_db)):
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found")

    certificates = db.query(Certificate).filter(Certificate.job_id == job_id).all()
    if not certificates:
        if job.status == JobStatus.PENDING or job.status == JobStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Certificates are still being processed. Please retry once processing completes.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No generated certificates available for this job.",
        )

    # Build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for cert in certificates:
            if os.path.exists(cert.file_path):
                safe_name = "".join(c for c in cert.recipient_name if c.isalnum() or c in ("-", "_")).strip() or "cert"
                archive_name = f"{cert.id}_{safe_name}.pdf"
                zf.write(cert.file_path, arcname=archive_name)

    zip_buffer.seek(0)
    zip_filename = f"job_{job_id[:8]}_certificates.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


@router.get(
    "/verify/{certificate_id}",
    response_model=CertificateVerifyResponse,
    summary="Verify certificate authenticity",
    description="Public verification endpoint to validate certificate existence, recipient, and cryptographic hash.",
)
def verify_certificate(certificate_id: str, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' is invalid or does not exist",
        )

    return CertificateVerifyResponse(
        certificate_id=cert.id,
        is_valid=True,
        recipient_name=cert.recipient_name,
        recipient_email=cert.recipient_email,
        event_name=cert.event_name,
        issuer_name=cert.issuer_name,
        issue_date=cert.issue_date,
        file_hash=cert.file_hash,
        created_at=cert.created_at,
        download_url=f"{settings.BASE_URL}/api/v1/certificates/{cert.id}/download",
    )
