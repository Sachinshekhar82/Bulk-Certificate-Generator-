import pytest


def test_create_job_missing_event_name(client):
    """Test validation failure when event_name is missing."""
    payload = {
        "issuer_name": "Acme Org",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}],
    }
    response = client.post("/api/v1/certificates/jobs", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("event_name" in err["loc"] for err in errors)


def test_create_job_empty_event_name_whitespace(client):
    """Test validation failure when event_name is only whitespace."""
    payload = {
        "event_name": "   ",
        "issuer_name": "Acme Org",
        "recipients": [{"name": "John Doe", "email": "john@example.com"}],
    }
    response = client.post("/api/v1/certificates/jobs", json=payload)
    assert response.status_code == 422


def test_create_job_empty_recipients_list(client):
    """Test validation failure when recipients list is empty."""
    payload = {
        "event_name": "Tech Seminar",
        "issuer_name": "Acme Org",
        "recipients": [],
    }
    response = client.post("/api/v1/certificates/jobs", json=payload)
    assert response.status_code == 422


def test_create_job_invalid_recipient_email(client):
    """Test validation failure when recipient has an invalid email format."""
    payload = {
        "event_name": "Tech Seminar",
        "issuer_name": "Acme Org",
        "recipients": [
            {"name": "Valid User", "email": "valid@example.com"},
            {"name": "Invalid User", "email": "not-an-email"},
        ],
    }
    response = client.post("/api/v1/certificates/jobs", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("email" in str(err["loc"]) for err in errors)


def test_create_job_blank_recipient_name(client):
    """Test validation failure when recipient name is whitespace only."""
    payload = {
        "event_name": "Tech Seminar",
        "issuer_name": "Acme Org",
        "recipients": [{"name": "   ", "email": "valid@example.com"}],
    }
    response = client.post("/api/v1/certificates/jobs", json=payload)
    assert response.status_code == 422


def test_create_job_exceeds_max_batch_size(client):
    """Test validation failure when recipient list exceeds batch limit."""
    huge_batch = [
        {"name": f"Recipient {i}", "email": f"user{i}@example.com"}
        for i in range(1001)
    ]
    payload = {
        "event_name": "Big Event",
        "issuer_name": "Acme Org",
        "recipients": huge_batch,
    }
    response = client.post("/api/v1/certificates/jobs", json=payload)
    assert response.status_code == 422
