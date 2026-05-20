from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.document_builder import build_worldcup_documents


OUTPUT_PATH = Path("data/generated_docs/worldcup_docs.jsonl")


def main() -> None:
    documents = build_worldcup_documents(OUTPUT_PATH)
    print(f"Wrote {len(documents)} generated documents to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
