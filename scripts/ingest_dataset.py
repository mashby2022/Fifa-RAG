"""Placeholder ingestion entrypoint.

The real partner dataset loader should normalize tables into generated WorldCupDocument
JSONL records, then upsert those records into Milvus. This placeholder gives the repo a
stable command target before the final tabular files arrive.
"""

import json
from pathlib import Path

from app.rag.mock_data import MOCK_DOCUMENTS


OUTPUT_PATH = Path("data/generated_docs/mock_worldcup_docs.jsonl")


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        for doc in MOCK_DOCUMENTS:
            handle.write(json.dumps(doc.model_dump(), ensure_ascii=True) + "\n")
    print(f"Wrote {len(MOCK_DOCUMENTS)} generated documents to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

