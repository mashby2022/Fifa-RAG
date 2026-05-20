from app.rag.service import RagService
from app.rag.tools.stats import ToolAnswer
from app.rag.tools import web_search as web_search_module
from app.schemas.api import ChatRequest


def test_explicit_web_check_routes_to_web_tool_with_previous_context(monkeypatch) -> None:
    service = RagService()
    service.last_user_message = "Who won the World Cup in 2022?"
    service.last_answer = "Argentina won the 2022 FIFA World Cup."
    seen: dict[str, str] = {}

    def fake_answer(question: str) -> ToolAnswer:
        seen["question"] = question
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
    assert response.retrieval_diagnostics["tool_route"] == "web_search"
