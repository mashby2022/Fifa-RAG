import json

import httpx

from app.core.config import settings
from app.rag.query_parser import ParsedQuery
from app.schemas.documents import RetrievedDocument


class NvidiaGenerator:
    def __init__(
        self,
        api_key: str = settings.nvidia_api_key,
        model: str = settings.nvidia_generator_model,
        base_url: str = settings.nvidia_base_url,
        timeout_seconds: float = settings.nvidia_timeout_seconds,
    ):
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is required when GENERATOR_PROVIDER=nvidia.")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def answer(self, parsed: ParsedQuery, retrieved: list[RetrievedDocument]) -> str:
        contexts = [
            {
                "doc_id": item.doc.doc_id,
                "title": item.doc.title,
                "entity_type": item.doc.entity_type,
                "competition": item.doc.competition,
                "tournament_year": item.doc.tournament_year,
                "text": item.doc.text,
                "source_refs": [ref.model_dump() for ref in item.doc.source_refs],
            }
            for item in retrieved
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a World Cup assistant for an internal enterprise RAG demo. "
                    "Answer only from the provided context records. If the context does not "
                    "support the answer, say that the current corpus does not contain enough "
                    "information. Be concise and factual. Do not invent citations; citations "
                    "are attached by the API separately."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": parsed.text,
                        "filters": parsed.filters,
                        "context_records": contexts,
                    },
                    ensure_ascii=True,
                ),
            },
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 350,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        response.raise_for_status()
        body = response.json()
        return body["choices"][0]["message"]["content"].strip()
