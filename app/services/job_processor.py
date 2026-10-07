import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Certificate, CertificateJob, JobItem, JobStatus, ItemStatus
from app.services.certificate_service import certificate_generator

logger = logging.getLogger("certificate_generator.job_processor")


def process_certificate_job(job_id: str, session_factory=None) -> None:
    """
    Background worker function that processes a bulk certificate generation job.
    Isolates per-item failures so a failure in generating one certificate does not
    halt or prevent generation of other certificates in the batch.
    """
    factory = session_factory or SessionLocal
    db: Session = factory()
    try:
        job: Optional[CertificateJob] = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found for processing")
            return

        # Mark job as actively processing
        job.status = JobStatus.PROCESSING
        db.commit()

        items = db.query(JobItem).filter(JobItem.job_id == job_id).all()

        for item in items:
            # Skip if already generated (supports re-runs / idempotency)
            if item.status == ItemStatus.GENERATED:
                continue

            try:
                # Failure injection support for testing/QA via metadata flag
                if item.recipient_metadata and item.recipient_metadata.get("_simulate_failure") is True:
                    raise RuntimeError("Simulated recipient generation failure for testing")

                # Generate the certificate PDF
                cert_id, file_path, file_hash, verification_url = certificate_generator.generate(
                    recipient_name=item.recipient_name,
                    recipient_email=item.recipient_email,
                    event_name=job.event_name,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                    template_title=job.template_title,
                    description=job.description,
                    metadata=item.recipient_metadata,
                )

                # Persist Certificate record
                certificate_record = Certificate(
                    id=cert_id,
                    job_id=job.id,
                    job_item_id=item.id,
                    recipient_name=item.recipient_name,
                    recipient_email=item.recipient_email,
                    event_name=job.event_name,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                    file_path=file_path,
                    file_hash=file_hash,
                    verification_url=verification_url,
                )
                db.add(certificate_record)

                # Update Item status to GENERATED
                item.status = ItemStatus.GENERATED
                item.certificate_id = cert_id
                item.file_path = file_path
                item.error_message = None
                item.processed_at = datetime.now(timezone.utc)

                job.success_count += 1
                job.processed_count += 1
                db.commit()

            except Exception as exc:
                db.rollback()
                logger.warning(
                    f"Failed to generate certificate for recipient {item.recipient_email} in job {job_id}: {exc}"
                )

                # Update Item status to FAILED with error message
                item.status = ItemStatus.FAILED
                item.error_message = str(exc)
                item.processed_at = datetime.now(timezone.utc)

                job.failed_count += 1
                job.processed_count += 1
                db.commit()

        # Refresh counts and finalize job status
        job.completed_at = datetime.now(timezone.utc)
        if job.failed_count == 0 and job.success_count > 0:
            job.status = JobStatus.COMPLETED
        elif job.success_count > 0 and job.failed_count > 0:
            job.status = JobStatus.PARTIAL_SUCCESS
        elif job.total_count == 0:
            job.status = JobStatus.COMPLETED
        else:
            job.status = JobStatus.FAILED

        db.commit()
        logger.info(
            f"Job {job_id} finished: {job.status.value} (Success: {job.success_count}, Failed: {job.failed_count})"
        )

    except Exception as e:
        logger.exception(f"Fatal error processing job {job_id}: {e}")
        try:
            job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
