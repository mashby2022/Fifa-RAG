from fastapi import APIRouter

from app.core.config import settings
from app.rag.service import rag_service
from app.schemas.api import ArchitectureResponse, ArchitectureLayer, ArchitectureStep, ChatRequest, ChatResponse, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        app=settings.app_name,
        vector_backend=settings.vector_backend,
        vector_runtime_backend=rag_service.vector_runtime_backend,
        embedding_provider=settings.embedding_provider,
        embedding_runtime_provider=rag_service.embedding_runtime_provider,
        generator_provider=settings.generator_provider,
        generator_runtime="hosted_nvidia_nim" if settings.generator_provider == "nvidia" else "local_extractive",
        generator_model=settings.nvidia_generator_model if settings.generator_provider == "nvidia" else "extractive",
        reranker_provider=settings.reranker_provider,
        nvidia_configured=bool(settings.nvidia_api_key),
        corpus_profile=settings.corpus_profile,
        demo_corpus_max_docs=settings.demo_corpus_max_docs,
        document_count=rag_service.document_count,
        tools=rag_service.tool_status,
    )


@router.get("/demo/questions", response_model=list[str])
def demo_questions() -> list[str]:
    return [
        "Who won the World Cup in 2022?",
        "Who did Argentina play in the 2022 final, and what was the score?",
        "Who refereed the 2022 final, and what other 2022 matches did they officiate?",
        "Create a map of the nations and head-to-head results for the 2022 World Cup.",
        "How did Argentina perform across the 2010, 2014, and 2018 World Cups?",
        "Which table tracks goals and goal scorers?",
    ]


@router.get("/tools")
def tools() -> dict[str, object]:
    return rag_service.tool_status


@router.get("/architecture", response_model=ArchitectureResponse)
def architecture() -> ArchitectureResponse:
    return ArchitectureResponse(
        title="World Cup Intelligence RAG Architecture",
        subtitle="A NeMo Retriever and NVIDIA NIM powered assistant over structured World Cup data.",
        overview=(
            "The bot treats World Cup data as multiple searchable story layers rather than one flat pile of rows. "
            "Structured tables from Fjelstul World Cup and OpenFootball are transformed into human-readable "
            "documents for tournaments, matches, team runs, awards, and story arcs. The retrieval path combines "
            "DuckDB-style exact stats tools, metadata filtering, semantic embeddings, lightweight lexical boosts, "
            "optional Milvus storage, guarded web search fallback, and NVIDIA-hosted generation with citations."
        ),
        pipeline=[
            ArchitectureStep(
                title="1. Structured Data Ingestion",
                description=(
                    "CSV and Football.TXT sources are fetched at build time and normalized into generated RAG "
                    "documents with stable source references."
                ),
                technologies=["Fjelstul World Cup Database", "OpenFootball", "Python document builder"],
            ),
            ArchitectureStep(
                title="2. Story Layer Creation",
                description=(
                    "Rows are converted into richer retrieval units: match narratives, tournament capsules, "
                    "team performance timelines, standings summaries, award cards, and fixture excerpts."
                ),
                technologies=["Typed document schema", "Source lineage", "Entity metadata"],
            ),
            ArchitectureStep(
                title="3. Query Understanding",
                description=(
                    "The API detects years, competition type, invalid tournament years, and club-vs-national-team "
                    "mismatches before retrieval."
                ),
                technologies=["Intent routing", "Metadata filters", "Invalid premise guards"],
            ),
            ArchitectureStep(
                title="4. Hybrid Retrieval",
                description=(
                    "The retriever combines semantic similarity with domain-specific lexical and metadata boosts "
                    "so questions like 'Germany's hero in the 2014 final' land on the right match and player context."
                ),
                technologies=["NeMo Retriever embeddings", "Hybrid scoring", "Milvus-ready vector store"],
            ),
            ArchitectureStep(
                title="5. Agentic Tool Routing",
                description=(
                    "Stats and schema-style questions can route to a DuckDB-backed tool before RAG, while article "
                    "questions can search the article layer and future low-confidence questions can use controlled web search."
                ),
                technologies=["DuckDB stats tool", "Press/article retrieval layer", "Optional web search tool"],
            ),
            ArchitectureStep(
                title="6. Rerank And Ground",
                description=(
                    "The intended production path retrieves a broad candidate set, reranks aggressively for precision, "
                    "then sends only the best grounded evidence to the answer generator."
                ),
                technologies=["NeMo Retriever Reranking NIM", "Top-k evidence selection", "Citation contract"],
            ),
            ArchitectureStep(
                title="7. Generate With Evidence",
                description=(
                    "The generator answers only from retrieved records and returns citations, retrieved context, "
                    "filters, and answer status for the UI."
                ),
                technologies=["NVIDIA NIM chat completions", "FastAPI", "Lovable frontend"],
            ),
        ],
        story_layers=[
            ArchitectureLayer(
                name="Tournament Capsules",
                purpose="Answer host, winner, dates, and tournament overview questions.",
                examples=["Who hosted 2018?", "Who won the 2022 World Cup?"],
            ),
            ArchitectureLayer(
                name="Match Narratives",
                purpose="Answer match-specific questions with score, stage, venue, and outcome.",
                examples=["What happened in the 2014 final?", "Who did Germany beat?"],
            ),
            ArchitectureLayer(
                name="Team Runs",
                purpose="Explain a team's tournament path, record, goals, and stage reached.",
                examples=["How did Argentina perform in 2010, 2014, and 2018?"],
            ),
            ArchitectureLayer(
                name="Awards And Player Signals",
                purpose="Surface Golden Boot, Golden Ball, and notable player records.",
                examples=["Who was the top scorer in 2010?", "Who won the Golden Ball in 2022?"],
            ),
            ArchitectureLayer(
                name="Press Articles",
                purpose="Index local press/article text as a separate article layer for Milvus or in-memory retrieval.",
                examples=["What press coverage do we have about World Cup 2026?"],
            ),
            ArchitectureLayer(
                name="Fixture And Future Context",
                purpose="Use OpenFootball fixture documents for schedule-style and upcoming tournament context.",
                examples=["What 2026 fixture data is available?"],
            ),
        ],
        nvidia_technologies=[
            ArchitectureStep(
                title="NeMo Retriever Embeddings",
                description=(
                    "Transforms questions and World Cup story documents into vectors for semantic retrieval. "
                    "The app uses query/passsage modes so user questions and indexed documents are embedded appropriately."
                ),
                technologies=[settings.nvidia_embedding_model, settings.nvidia_base_url],
            ),
            ArchitectureStep(
                title="NeMo Retriever Reranking NIM",
                description=(
                    "Planned precision layer that reranks retrieved candidate passages by relevance before generation. "
                    "This is the key upgrade from simple vector search to high-trust evidence selection."
                ),
                technologies=["NVIDIA NeMo Retriever Reranking NIM", "Top 25 to top 5 rerank pattern"],
            ),
            ArchitectureStep(
                title="NVIDIA NIM Generation",
                description=(
                    "Produces concise grounded answers from the selected evidence while the API attaches structured citations."
                ),
                technologies=[settings.nvidia_generator_model, "OpenAI-compatible NIM API"],
            ),
            ArchitectureStep(
                title="Milvus-Ready Vector Store",
                description=(
                    "The current hosted demo can run in memory, while the same document schema and metadata fields are ready "
                    "to move into Milvus for scalable vector search."
                ),
                technologies=["Milvus", settings.milvus_collection],
            ),
        ],
        demo_callouts=[
            "This is not generic chat over CSVs; it is layered retrieval over football entities and story arcs.",
            "Invalid years and club-team questions are handled before generation to avoid hallucination.",
            "The right-side UI evidence cards should show which layer each answer came from.",
            "The architecture is reusable: swap World Cup data for another structured customer dataset and keep the same retrieval shell.",
        ],
    )


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return rag_service.answer(request)
