from fastapi import APIRouter

from app.core.config import settings
from app.rag.service import rag_service
from app.schemas.api import ChatRequest, ChatResponse, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        app=settings.app_name,
        vector_backend=settings.vector_backend,
        embedding_provider=settings.embedding_provider,
        generator_provider=settings.generator_provider,
        nvidia_configured=bool(settings.nvidia_api_key),
    )


@router.get("/demo/questions", response_model=list[str])
def demo_questions() -> list[str]:
    return [
        "Who won the men's World Cup in 2014, and who did they beat in the final?",
        "Which country hosted the 2018 World Cup?",
        "How did Argentina perform across the 2010, 2014, and 2018 World Cups?",
        "Who won the World Cup in 2000?",
        "How did FC Barcelona perform in the 2014 World Cup?",
    ]


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return rag_service.answer(request)
