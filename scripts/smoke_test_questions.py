import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


QUESTIONS = [
    "Who won the men's World Cup in 2014, and who did they beat in the final?",
    "Which country hosted the 2018 World Cup?",
    "How did Argentina perform across the 2010, 2014, and 2018 World Cups?",
    "Who won the World Cup in 2000?",
    "How did FC Barcelona perform in the 2014 World Cup?",
]


def main() -> None:
    client = TestClient(app)
    for question in QUESTIONS:
        response = client.post("/api/chat", json={"message": question})
        response.raise_for_status()
        payload = response.json()
        print(json.dumps({"question": question, "status": payload["status"], "answer": payload["answer"]}, indent=2))


if __name__ == "__main__":
    main()
