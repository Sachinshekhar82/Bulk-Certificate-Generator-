def test_individual_failure_isolation(client):
    """
    Verify that an individual recipient failure does NOT prevent other valid
    certificates from being generated, and that job status reflects PARTIAL_SUCCESS.
    """
    payload = {
        "event_name": "Resilient Systems Workshop",
        "issuer_name": "Aereo Tech",
        "recipients": [
            {
                "name": "First Valid Student",
                "email": "student1@example.com",
                "metadata": {"score": 90},
            },
            {
                "name": "Faulty Recipient",
                "email": "faulty@example.com",
                "metadata": {"_simulate_failure": True},  # Injected failure
            },
            {
                "name": "Second Valid Student",
                "email": "student2@example.com",
                "metadata": {"score": 95},
            },
        ],
    }

    create_res = client.post("/api/v1/certificates/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["id"]

    # Retrieve job status after processing
    status_res = client.get(f"/api/v1/certificates/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()

    # The overall job must be marked PARTIAL_SUCCESS
    assert job_data["status"] == "PARTIAL_SUCCESS"
    assert job_data["total_count"] == 3
    assert job_data["processed_count"] == 3
    assert job_data["success_count"] == 2
    assert job_data["failed_count"] == 1

    items = {item["recipient_email"]: item for item in job_data["items"]}

    # Verify first recipient succeeded
    assert items["student1@example.com"]["status"] == "GENERATED"
    assert items["student1@example.com"]["certificate_id"] is not None
    assert items["student1@example.com"]["error_message"] is None

    # Verify faulty recipient failed with logged error message
    assert items["faulty@example.com"]["status"] == "FAILED"
    assert items["faulty@example.com"]["certificate_id"] is None
    assert "Simulated recipient generation failure" in items["faulty@example.com"]["error_message"]

    # Verify third recipient succeeded despite the previous error
    assert items["student2@example.com"]["status"] == "GENERATED"
    assert items["student2@example.com"]["certificate_id"] is not None
    assert items["student2@example.com"]["error_message"] is None


def test_filter_job_items_by_status(client):
    """Test filtering job items by status query parameter."""
    payload = {
        "event_name": "Filter Test Event",
        "issuer_name": "Acme Org",
        "recipients": [
            {"name": "Pass User", "email": "pass@example.com"},
            {"name": "Fail User", "email": "fail@example.com", "metadata": {"_simulate_failure": True}},
        ],
    }

    create_res = client.post("/api/v1/certificates/jobs", json=payload)
    job_id = create_res.json()["id"]

    # Query only FAILED items
    failed_res = client.get(f"/api/v1/certificates/jobs/{job_id}/items?status=FAILED")
    assert failed_res.status_code == 200
    failed_items = failed_res.json()["items"]
    assert len(failed_items) == 1
    assert failed_items[0]["recipient_email"] == "fail@example.com"
    assert failed_items[0]["status"] == "FAILED"

    # Query only GENERATED items
    success_res = client.get(f"/api/v1/certificates/jobs/{job_id}/items?status=GENERATED")
    assert success_res.status_code == 200
    success_items = success_res.json()["items"]
    assert len(success_items) == 1
    assert success_items[0]["recipient_email"] == "pass@example.com"
    assert success_items[0]["status"] == "GENERATED"


def test_all_recipients_failed_status(client):
    """Test that when all recipients fail, the job status is FAILED."""
    payload = {
        "event_name": "All Fail Event",
        "issuer_name": "Acme Org",
        "recipients": [
            {"name": "Fail 1", "email": "fail1@example.com", "metadata": {"_simulate_failure": True}},
            {"name": "Fail 2", "email": "fail2@example.com", "metadata": {"_simulate_failure": True}},
        ],
    }

    create_res = client.post("/api/v1/certificates/jobs", json=payload)
    job_id = create_res.json()["id"]

    status_res = client.get(f"/api/v1/certificates/jobs/{job_id}")
    job_data = status_res.json()

    assert job_data["status"] == "FAILED"
    assert job_data["success_count"] == 0
    assert job_data["failed_count"] == 2
