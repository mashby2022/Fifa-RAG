import re
import unicodedata
from typing import Any

from app.schemas.documents import WorldCupDocument


TOKEN_RE = re.compile(r"[a-z0-9]+")
WIN_TOKENS = {"win", "winner", "won", "champion", "champions"}
HOST_TOKENS = {"host", "hosted", "hosting"}
FINAL_TOKENS = {"final", "finals"}
SCORER_TOKENS = {"scorer", "scored", "goals", "golden", "boot"}
SCHEMA_TOKENS = {"table", "dataset", "field", "column", "schema", "codebook", "variable"}
HERO_TOKENS = {"hero", "winner", "winning", "decisive"}


def lexical_score(query: str, doc: WorldCupDocument) -> float:
    normalized_query = normalize_text(query)
    query_tokens = set(TOKEN_RE.findall(normalized_query))
    doc_text = normalize_text(" ".join([doc.title, doc.text, metadata_text(doc.metadata)]))
    doc_tokens = set(TOKEN_RE.findall(doc_text))
    score = len(query_tokens & doc_tokens) * 0.08

    score += year_score(query, doc)
    score += intent_score(query_tokens, doc)
    score += multi_year_score(query, doc)
    score += entity_name_score(normalized_query, doc)
    return score


def year_score(query: str, doc: WorldCupDocument) -> float:
    return 0.75 if str(doc.tournament_year) in query else 0.0


def intent_score(query_tokens: set[str], doc: WorldCupDocument) -> float:
    score = 0.0
    if WIN_TOKENS & query_tokens:
        if doc.entity_type == "tournament":
            score += 0.45
        if doc.entity_type == "standing" and doc.metadata.get("position") == 1:
            score += 0.55
        if doc.entity_type == "match" and "won the match" in doc.text.lower():
            score += 0.25
    if HOST_TOKENS & query_tokens and doc.entity_type == "tournament":
        score += 0.7
    if FINAL_TOKENS & query_tokens:
        if doc.metadata.get("stage") == "final":
            score += 2.0
        if "final standings" in doc.title.lower():
            score += 0.4
    if HERO_TOKENS & query_tokens and doc.entity_type == "match" and doc.metadata.get("stage") == "final":
        score += 2.0
    if HERO_TOKENS & query_tokens and doc.entity_type == "award":
        score -= 0.4
    if SCORER_TOKENS & query_tokens and doc.entity_type == "award":
        score += 0.8
    if SCORER_TOKENS & query_tokens and doc.entity_type in {"goal", "player"}:
        score += 0.7
    if SCHEMA_TOKENS & query_tokens and doc.entity_type == "schema":
        score += 1.2
        if doc.metadata.get("doc_type") == "dataset":
            score += 1.4
        if doc.metadata.get("doc_type") == "variable":
            score -= 0.2
    return score


def multi_year_score(query: str, doc: WorldCupDocument) -> float:
    query_years = {int(year) for year in re.findall(r"\b(19[0-9]{2}|20[0-9]{2})\b", query)}
    if doc.entity_type == "team" and any(str(year) in query for year in doc.metadata.get("years", [])):
        score = 0.8
    else:
        score = 0.0

    doc_years = set(doc.metadata.get("years", [])) if isinstance(doc.metadata.get("years"), list) else {doc.tournament_year}
    if len(query_years) > 1:
        score += 1.5 if doc.entity_type == "team" else -0.5
        if query_years.issubset(doc_years):
            score += 2.0
    return score


def entity_name_score(normalized_query: str, doc: WorldCupDocument) -> float:
    score = 0.0
    for key in ["team", "player"]:
        value = doc.metadata.get(key)
        if isinstance(value, str) and normalize_text(value) in normalized_query:
            score += 2.0

    dataset = doc.metadata.get("dataset")
    if isinstance(dataset, str) and normalize_text(dataset) in normalized_query:
        score += 3.0 if doc.metadata.get("doc_type") == "dataset" else 1.5

    variable = doc.metadata.get("variable")
    if isinstance(variable, str) and normalize_text(variable) in normalized_query:
        score += 1.5

    teams = doc.metadata.get("teams")
    if isinstance(teams, list):
        score += sum(
            0.45
            for team_name in teams
            if isinstance(team_name, str) and normalize_text(team_name) in normalized_query
        )
    return score


def metadata_text(metadata: dict[str, Any]) -> str:
    values: list[str] = []
    for value in metadata.values():
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value))
    return " ".join(values)


def normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))
