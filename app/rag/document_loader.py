import json
from pathlib import Path

from app.core.config import settings
from app.rag.mock_data import MOCK_DOCUMENTS
from app.schemas.documents import WorldCupDocument


def load_documents(path: str = settings.generated_docs_path) -> list[WorldCupDocument]:
    docs_path = Path(path)
    if not docs_path.exists():
        return MOCK_DOCUMENTS

    documents: list[WorldCupDocument] = []
    with docs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            documents.append(WorldCupDocument.model_validate(json.loads(line)))

    return documents or MOCK_DOCUMENTS
