import hashlib
import os
from datetime import date
from pathlib import Path
from app.services.certificate_service import CertificateGenerator


def test_certificate_generator_generates_valid_pdf(tmp_path):
    """Test that CertificateGenerator produces a valid PDF file with proper cryptographic hash."""
    generator = CertificateGenerator(storage_dir=tmp_path)

    cert_id, file_path, file_hash, verify_url = generator.generate(
        recipient_name="Alice Smith",
        recipient_email="alice@example.com",
        event_name="Cloud Architecture Bootcamp",
        issuer_name="Tech Academy",
        issue_date=date(2026, 10, 7),
        template_title="Certificate of Achievement",
        description="for demonstrated excellence in cloud systems",
        metadata={"Grade": "Distinction", "Cohort": "2026-Q4"},
    )

    # Assertions on identifiers and paths
    assert cert_id.startswith("CERT-")
    assert os.path.exists(file_path)
    assert file_path.endswith(".pdf")
    assert verify_url.endswith(f"/api/v1/certificates/verify/{cert_id}")

    # Check file size and PDF magic bytes
    file_size = os.path.getsize(file_path)
    assert file_size > 1000  # Non-trivial PDF size

    with open(file_path, "rb") as f:
        content = f.read()

    assert content.startswith(b"%PDF")  # Valid PDF header

    # Verify SHA-256 integrity
    computed_hash = hashlib.sha256(content).hexdigest()
    assert computed_hash == file_hash


def test_certificate_generator_unique_ids(tmp_path):
    """Test that generated certificate IDs are unique."""
    generator = CertificateGenerator(storage_dir=tmp_path)
    ids = {generator.generate_certificate_id() for _ in range(100)}
    assert len(ids) == 100


def test_certificate_generator_custom_id(tmp_path):
    """Test generating a certificate with an explicit custom ID."""
    generator = CertificateGenerator(storage_dir=tmp_path)
    custom_id = "CERT-CUSTOM-9999"

    cert_id, file_path, file_hash, verify_url = generator.generate(
        recipient_name="Bob Builder",
        recipient_email="bob@example.com",
        event_name="DevOps 101",
        issuer_name="DevOps Guild",
        issue_date=date(2026, 1, 1),
        custom_cert_id=custom_id,
    )

    assert cert_id == custom_id
    assert custom_id in file_path
