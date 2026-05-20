import json
from pathlib import Path

from app.core.config import settings
from app.rag.corpus import (
    build_award_docs,
    build_codebook_docs,
    build_goal_story_docs,
    build_match_docs,
    build_openfootball_docs,
    build_press_article_docs,
    build_player_profile_docs,
    build_standing_docs,
    build_team_performance_docs,
    build_tournament_docs,
    build_tournament_standing_summaries,
    load_fjelstul_tables,
)
from app.rag.corpus.curation import select_demo_documents
from app.schemas.documents import WorldCupDocument


def build_worldcup_documents(output_path: Path) -> list[WorldCupDocument]:
    tables = load_fjelstul_tables(settings.local_data_dir)
    documents = build_document_corpus(tables)
    documents = apply_corpus_profile(documents)
    write_documents(output_path, documents)
    return documents


def apply_corpus_profile(documents: list[WorldCupDocument]) -> list[WorldCupDocument]:
    if settings.corpus_profile.lower() == "full":
        return documents
    return select_demo_documents(documents, settings.demo_corpus_max_docs)


def build_document_corpus(tables: dict[str, list[dict[str, str]]]) -> list[WorldCupDocument]:
    documents: list[WorldCupDocument] = []
    documents.extend(build_tournament_docs(tables["tournaments"]))
    documents.extend(build_match_docs(tables["matches"], tables["goals"]))

    team_tournament_docs, team_timeline_docs = build_team_performance_docs(
        tables["team_appearances"], tables["tournament_standings"], tables["qualified_teams"]
    )
    documents.extend(team_tournament_docs)
    documents.extend(team_timeline_docs)

    documents.extend(build_standing_docs(tables["tournament_standings"]))
    documents.extend(build_tournament_standing_summaries(tables["tournament_standings"]))
    documents.extend(build_award_docs(tables["award_winners"]))
    documents.extend(
        build_player_profile_docs(
            tables["players"],
            tables["player_appearances"],
            tables["goals"],
            tables["squads"],
            tables["award_winners"],
        )
    )
    documents.extend(build_goal_story_docs(tables["goals"], tables["award_winners"]))
    documents.extend(build_codebook_docs(tables["codebook_datasets"], tables["codebook_variables"]))

    if settings.include_openfootball_docs:
        documents.extend(build_openfootball_docs())
    documents.extend(build_press_article_docs())

    return documents


def write_documents(output_path: Path, documents: list[WorldCupDocument]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for doc in documents:
            handle.write(json.dumps(doc.model_dump(), ensure_ascii=True) + "\n")
