from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.rag.tools.stats import ToolAnswer


WEB_TERMS = {"latest", "current", "today", "news", "press", "article", "web", "search"}
EXPLICIT_WEB_TERMS = {
    "check the web",
    "web search",
    "run a web search",
    "search the web",
    "look online",
    "confirm online",
}


@dataclass
class WebSearchTool:
    provider: str = settings.web_search_provider
    enabled: bool = settings.web_search_enabled
    api_key: str = settings.web_search_api_key
    url: str = settings.web_search_url
    timeout_seconds: float = settings.nvidia_timeout_seconds
    last_error: str | None = field(default=None)

    @property
    def available(self) -> bool:
        return self.enabled and self.provider == "tavily" and bool(self.api_key)

    def maybe_answer(self, question: str) -> ToolAnswer | None:
        if not self.available or not _looks_like_web_question(question):
            return None
        try:
            return self._tavily_answer(question)
        except Exception as exc:
            self.last_error = str(exc)
            return None

    def answer(self, question: str) -> ToolAnswer | None:
        if not self.available:
            return None
        try:
            return self._tavily_answer(question)
        except Exception as exc:
            self.last_error = str(exc)
            return None

    def _tavily_answer(self, question: str) -> ToolAnswer | None:
        payload: dict[str, Any] = {
            "api_key": self.api_key,
            "query": question,
            "search_depth": "basic",
            "max_results": 3,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self.url, json=payload)
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            return None

        snippets = []
        citations = []
        for index, result in enumerate(results, start=1):
            title = result.get("title") or result.get("url") or f"Web result {index}"
            content = result.get("content") or result.get("snippet") or ""
            url = result.get("url", "")
            snippets.append(f"{title}: {content}")
            citations.append({"table": "web_search", "record_id": url or title})

        return ToolAnswer(
            tool_name="web_search",
            answer="Web search fallback found: " + " ".join(snippets),
            citations=citations,
            diagnostics={"provider": self.provider, "results": len(results)},
        )


def _looks_like_web_question(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in WEB_TERMS)


def is_explicit_web_request(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in EXPLICIT_WEB_TERMS)


web_search_tool = WebSearchTool()
