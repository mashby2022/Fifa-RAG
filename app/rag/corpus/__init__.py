"""Corpus construction helpers for the World Cup RAG index."""

from app.rag.corpus.builders import (
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
)
from app.rag.corpus.curation import select_demo_documents
from app.rag.corpus.sources import load_fjelstul_tables

__all__ = [
    "build_award_docs",
    "build_codebook_docs",
    "build_goal_story_docs",
    "build_match_docs",
    "build_openfootball_docs",
    "build_press_article_docs",
    "build_player_profile_docs",
    "build_standing_docs",
    "build_team_performance_docs",
    "build_tournament_docs",
    "build_tournament_standing_summaries",
    "load_fjelstul_tables",
    "select_demo_documents",
]
