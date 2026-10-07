def test_create_and_track_job(client):
    """Test creating a generation job and tracking its status/progress."""
    payload = {
        "event_name": "Python Advanced Architecture",
        "issuer_name": "Aereo Academy",
        "issue_date": "2026-10-07",
        "template_title": "Certificate of Mastery",
        "description": "for mastering modern asynchronous architecture",
        "recipients": [
            {"name": "Alice Green", "email": "alice.green@example.com", "metadata": {"Score": "99%"}},
            {"name": "Bob Blue", "email": "bob.blue@example.com", "metadata": {"Score": "95%"}},
        ],
    }

    # 1. Submit job (returns 202 Accepted)
    create_res = client.post("/api/v1/certificates/jobs", json=payload)
    assert create_res.status_code == 202
    job_data = create_res.json()

    job_id = job_data["id"]
    assert job_id is not None
    assert job_data["total_count"] == 2
    assert "status_url" in job_data

    # 2. Track Job Progress (Background task executed synchronously in TestClient)
    status_res = client.get(f"/api/v1/certificates/jobs/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()

    assert status_data["id"] == job_id
    assert status_data["status"] == "COMPLETED"
    assert status_data["total_count"] == 2
    assert status_data["processed_count"] == 2
    assert status_data["success_count"] == 2
    assert status_data["failed_count"] == 0
    assert status_data["progress_percentage"] == 100.0
    assert len(status_data["items"]) == 2

    # Check item details
    for item in status_data["items"]:
        assert item["status"] == "GENERATED"
        assert item["certificate_id"] is not None
        assert item["download_url"] is not None
        assert item["error_message"] is None


def test_get_nonexistent_job_returns_404(client):
    """Test that requesting an unknown job returns 404."""
    response = client.get("/api/v1/certificates/jobs/unknown-uuid-0000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_paginated_job_items(client):
    """Test retrieving paginated job items with pagination controls."""
    recipients = [
        {"name": f"User {i}", "email": f"user{i}@example.com"}
        for i in range(1, 6)
    ]
    payload = {
        "event_name": "Webinar Series",
        "issuer_name": "Dev Community",
        "recipients": recipients,
    }

    create_res = client.post("/api/v1/certificates/jobs", json=payload)
    job_id = create_res.json()["id"]

    # Query page 1 with page_size=2
    page1_res = client.get(f"/api/v1/certificates/jobs/{job_id}/items?page=1&page_size=2")
    assert page1_res.status_code == 200
    p1_data = page1_res.json()
    assert p1_data["total"] == 5
    assert p1_data["page"] == 1
    assert p1_data["page_size"] == 2
    assert p1_data["total_pages"] == 3
    assert len(p1_data["items"]) == 2

    # Query page 3 with page_size=2
    page3_res = client.get(f"/api/v1/certificates/jobs/{job_id}/items?page=3&page_size=2")
    assert page3_res.status_code == 200
    p3_data = page3_res.json()
    assert len(p3_data["items"]) == 1
