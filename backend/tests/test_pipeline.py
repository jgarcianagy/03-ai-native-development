def test_get_pipeline_returns_stages_in_order(client):
    response = client.get("/api/pipeline")
    assert response.status_code == 200
    assert response.json()["stages"] == [
        "Lead",
        "Qualified",
        "Proposal",
        "Negotiation",
        "Won",
        "Lost",
    ]
