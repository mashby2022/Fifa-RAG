from app.rag.service import RagService
from app.rag.tools.stats import ToolAnswer
from app.rag.tools import web_search as web_search_module
from app.schemas.api import ChatRequest


def test_explicit_web_check_routes_to_web_tool_with_previous_context(monkeypatch) -> None:
    service = RagService()
    service.last_user_message = "Who won the World Cup in 2022?"
    service.last_answer = "Argentina won the 2022 FIFA World Cup."
    seen: dict[str, str] = {}

    def fake_answer(question: str, expected_answer: str | None = None) -> ToolAnswer:
        seen["question"] = question
        seen["expected_answer"] = expected_answer or ""
        return ToolAnswer(
            tool_name="web_search",
            answer="Web confirms Argentina won the 2022 FIFA World Cup.",
            citations=[{"table": "web_search", "record_id": "https://example.com"}],
            diagnostics={"provider": "test", "results": 1},
        )

    monkeypatch.setattr(web_search_module.web_search_tool, "answer", fake_answer)

    response = service.answer(ChatRequest(message="run a web search and check"))

    assert response.tool_calls[0]["name"] == "web_search"
    assert "Argentina won the 2022 FIFA World Cup" in seen["question"]
    assert "Argentina won the 2022 FIFA World Cup" in seen["expected_answer"]
    assert response.retrieval_diagnostics["tool_route"] == "web_search"


def test_low_information_web_followup_builds_verification_query(monkeypatch) -> None:
    service = RagService()
    service.last_user_message = "which world cup did Nigeria place the highest"
    service.last_answer = (
        "Nigeria's highest World Cup finish in the men's tournament was round of 16, "
        "reached at 1994 FIFA Men's World Cup, 1998 FIFA Men's World Cup, 2014 FIFA Men's World Cup."
    )
    seen: dict[str, str] = {}

    def fake_answer(question: str, expected_answer: str | None = None) -> ToolAnswer:
        seen["question"] = question
        seen["expected_answer"] = expected_answer or ""
        return ToolAnswer(
            tool_name="web_search",
            answer="Web confirms Nigeria reached the round of 16 in 1994, 1998, and 2014.",
            citations=[{"table": "web_search", "record_id": "https://example.com"}],
            diagnostics={"provider": "test", "results": 1},
        )

    monkeypatch.setattr(web_search_module.web_search_tool, "answer", fake_answer)

    response = service.answer(ChatRequest(message="do a web search and find out"))

    assert response.tool_calls[0]["name"] == "web_search"
    assert "Nigeria" in seen["question"]
    assert "round of 16" in seen["question"]
    assert "1994 1998 2014" in seen["question"]
    assert "national football team FIFA World Cup record" in seen["question"]
    assert "Nigeria's highest World Cup finish" in seen["expected_answer"]
