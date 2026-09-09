def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_grounded_answer_has_citations(client):
    response = client.post("/api/chat", json={"message": "How long do I have to return an unused item?"})
    body = response.json()
    assert response.status_code == 200
    assert body["confidence"] in {"high", "medium"}
    assert body["citations"]
    assert body["escalated"] is False
    assert "30" in body["answer"]


def test_unknown_question_escalates(client):
    response = client.post("/api/chat", json={"message": "Can you diagnose my headache?"})
    body = response.json()
    assert response.status_code == 200
    assert body["confidence"] == "low"
    assert body["escalated"] is True


def test_admin_route_requires_key(client):
    response = client.get("/api/admin/documents")
    assert response.status_code == 401


def test_admin_route_accepts_valid_key(client):
    assert client.get("/api/admin/documents").status_code == 401
    response = client.get("/api/admin/documents", headers={"X-Admin-Key": "test-admin-key"})
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_feedback_flow(client):
    chat = client.post("/api/chat", json={"message": "How do I reset my password?"}).json()
    response = client.post("/api/feedback", json={"message_id": chat["message_id"], "helpful": True})
    assert response.status_code == 201
