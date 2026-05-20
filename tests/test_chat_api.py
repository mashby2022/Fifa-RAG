from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_architecture_endpoint_describes_nvidia_stack() -> None:
    response = client.get("/api/architecture")
    payload = response.json()
    assert response.status_code == 200
    assert "World Cup Intelligence" in payload["title"]
    assert payload["pipeline"]
    assert payload["story_layers"]
    assert any("NeMo Retriever" in item["title"] for item in payload["nvidia_technologies"])


def test_grounded_2014_final_answer_has_citation() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Who won the men's World Cup in 2014, and who did they beat in the final?"},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "grounded"
    assert "Germany" in payload["answer"]
    assert payload["citations"]
    assert payload["citations"][0]["source_refs"]
    assert payload["intent"]
    assert payload["layers_searched"]
    assert "initial_retrieved" in payload["retrieval_diagnostics"]


def test_query_mode_schema_routes_to_codebook_layer() -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Which table tracks goals and goal scorers?", "query_mode": "schema"},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["intent"] == "schema_question"
    assert payload["layers_searched"] == ["schema"]


def test_invalid_world_cup_year_does_not_retrieve() -> None:
    response = client.post("/api/chat", json={"message": "Who won the World Cup in 2000?"})
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "invalid_premise"
    assert "no men's FIFA World Cup tournament in 2000" in payload["answer"]
    assert payload["citations"] == []


def test_club_team_question_is_clarified() -> None:
    response = client.post("/api/chat", json={"message": "How did FC Barcelona perform in the 2014 World Cup?"})
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "invalid_premise"
    assert "club team" in payload["answer"]
