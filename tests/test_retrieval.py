import io
import zipfile


def test_download_single_certificate(client):
    """Test downloading an individual generated certificate PDF file."""
    payload = {
        "event_name": "API Design Masterclass",
        "issuer_name": "Aereo Tech",
        "recipients": [{"name": "Charlie Chaplin", "email": "charlie@example.com"}],
    }
    create_res = client.post("/api/v1/certificates/jobs", json=payload)
    job_id = create_res.json()["id"]

    # Get certificate ID from job details
    status_res = client.get(f"/api/v1/certificates/jobs/{job_id}")
    items = status_res.json()["items"]
    assert len(items) == 1
    cert_id = items[0]["certificate_id"]
    assert cert_id is not None

    # Download the certificate
    download_res = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert "attachment" in download_res.headers["content-disposition"]
    assert f"{cert_id}" in download_res.headers["content-disposition"]
    assert download_res.content.startswith(b"%PDF")


def test_download_nonexistent_certificate_returns_404(client):
    """Test downloading an unknown certificate returns 404."""
    res = client.get("/api/v1/certificates/CERT-DOES-NOT-EXIST/download")
    assert res.status_code == 404


def test_download_all_certificates_zip(client):
    """Test downloading all certificates for a job bundled in a ZIP archive."""
    payload = {
        "event_name": "Docker & Kubernetes Workshop",
        "issuer_name": "DevOps Org",
        "recipients": [
            {"name": "Participant One", "email": "p1@example.com"},
            {"name": "Participant Two", "email": "p2@example.com"},
        ],
    }
    create_res = client.post("/api/v1/certificates/jobs", json=payload)
    job_id = create_res.json()["id"]

    # Download ZIP bundle
    zip_res = client.get(f"/api/v1/certificates/jobs/{job_id}/download-all")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    assert f"job_{job_id[:8]}" in zip_res.headers["content-disposition"]

    # Inspect ZIP contents
    zip_buffer = io.BytesIO(zip_res.content)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 2
        for filename in namelist:
            assert filename.endswith(".pdf")
            pdf_bytes = zf.read(filename)
            assert pdf_bytes.startswith(b"%PDF")


def test_verify_certificate_endpoint(client):
    """Test the public verification endpoint for an authentic certificate."""
    payload = {
        "event_name": "Cybersecurity Foundations",
        "issuer_name": "Security Institute",
        "recipients": [{"name": "David Miller", "email": "david@example.com"}],
    }
    create_res = client.post("/api/v1/certificates/jobs", json=payload)
    job_id = create_res.json()["id"]

    status_res = client.get(f"/api/v1/certificates/jobs/{job_id}")
    cert_id = status_res.json()["items"][0]["certificate_id"]

    # Verify certificate
    verify_res = client.get(f"/api/v1/certificates/verify/{cert_id}")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()

    assert verify_data["certificate_id"] == cert_id
    assert verify_data["is_valid"] is True
    assert verify_data["recipient_name"] == "David Miller"
    assert verify_data["recipient_email"] == "david@example.com"
    assert verify_data["event_name"] == "Cybersecurity Foundations"
    assert verify_data["issuer_name"] == "Security Institute"
    assert len(verify_data["file_hash"]) == 64  # Valid SHA-256 length


def test_verify_invalid_certificate_returns_404(client):
    """Test verifying a fake or non-existent certificate returns 404."""
    verify_res = client.get("/api/v1/certificates/verify/FAKE-CERT-9999")
    assert verify_res.status_code == 404
    assert "invalid" in verify_res.json()["detail"].lower()
