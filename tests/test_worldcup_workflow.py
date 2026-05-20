from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_2022_followup_workflow_tracks_final_and_referee_context() -> None:
    winner = client.post("/api/chat", json={"message": "Who won the World Cup in 2022?"}).json()
    opponent = client.post("/api/chat", json={"message": "Who did they play against?"}).json()
    score = client.post("/api/chat", json={"message": "What was the score?"}).json()
    referee = client.post("/api/chat", json={"message": "Who was the referee?"}).json()
    other_matches = client.post(
        "/api/chat",
        json={"message": "Has that referee refereed any other match during that world cup?"},
    ).json()

    assert "Argentina won" in winner["answer"]
    assert "France" in opponent["answer"]
    assert "3–3" in score["answer"]
    assert "4–2 on penalties" in score["answer"]
    assert "Szymon Marciniak" in referee["answer"]
    assert "France vs Denmark" in other_matches["answer"]
    assert "Argentina vs Australia" in other_matches["answer"]
    assert winner["agent_worklog"]


def test_2022_map_workflow_returns_artifact() -> None:
    client.post("/api/chat", json={"message": "Who won the World Cup in 2022?"})
    response = client.post(
        "/api/chat",
        json={
            "message": (
                "Can you create a map of all the nations represented during this world cup "
                "with a link between the head-to-head nations and overlay the result?"
            )
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["artifacts"]
    artifact = payload["artifacts"][0]
    assert artifact["type"] == "worldcup_match_map"
    assert len(artifact["nodes"]) == 32
    assert len(artifact["edges"]) == 64
