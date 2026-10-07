def test_root_endpoint(client):
    """Test the root endpoint returns API information and documentation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs" in data
    assert "version" in data
    assert data["app"] == "Bulk Certificate Generator API"


def test_health_check_endpoint(client):
    """Test the health check endpoint returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
