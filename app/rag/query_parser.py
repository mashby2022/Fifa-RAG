import re
from dataclasses import dataclass, field


YEAR_RE = re.compile(r"\b(19[3-9][0-9]|20[0-9][0-9])\b")
KNOWN_CLUBS = {"fc barcelona", "barcelona", "real madrid", "manchester city", "psg"}
SCHEMA_TERMS = {"table", "dataset", "field", "column", "schema", "codebook", "variable"}
HOST_TERMS = {"host", "hosted", "hosting"}
SCORER_TERMS = {"scorer", "scored", "goals", "golden boot", "top scorer"}
MATCH_TERMS = {"match", "final", "semi-final", "quarter-final", "hero", "winner", "winning goal"}
TEAM_ARC_TERMS = {"perform", "performance", "arc", "run", "timeline", "across", "compare"}
VALID_MEN_YEARS = {
    1930,
    1934,
    1938,
    1950,
    1954,
    1958,
    1962,
    1966,
    1970,
    1974,
    1978,
    1982,
    1986,
    1990,
    1994,
    1998,
    2002,
    2006,
    2010,
    2014,
    2018,
    2022,
    2026,
}


@dataclass
class ParsedQuery:
    text: str
    years: list[int] = field(default_factory=list)
    competition: str = "men"
    filters: dict[str, object] = field(default_factory=dict)
    invalid_reason: str | None = None
    intent: str = "factual_lookup"
    query_rewrite: str | None = None
    layers: list[str] = field(default_factory=list)


def parse_query(message: str, query_mode: str = "auto") -> ParsedQuery:
    lowered = message.lower()
    years = [int(year) for year in YEAR_RE.findall(lowered)]
    competition = "women" if "women" in lowered or "women's" in lowered else "men"
    filters: dict[str, object] = {"competition": competition}
    if len(years) == 1:
        filters["tournament_year"] = years[0]

    invalid_reason = None
    intent = "factual_lookup"
    layers = ["tournament", "match", "team", "standing", "award", "goal", "player"]
    query_rewrite = _rewrite_query(message, years)

    if any(club in lowered for club in KNOWN_CLUBS):
        invalid_reason = "club_team"
    elif years and competition == "men" and all(year not in VALID_MEN_YEARS for year in years):
        invalid_reason = "invalid_tournament_year"
    elif query_mode != "auto":
        intent, layers = _mode_intent(query_mode)
    elif any(term in lowered for term in SCHEMA_TERMS):
        intent = "schema_question"
        layers = ["schema"]
    elif len(years) > 1 or any(term in lowered for term in TEAM_ARC_TERMS):
        intent = "team_arc"
        layers = ["team", "match", "standing"]
    elif any(term in lowered for term in MATCH_TERMS):
        intent = "match_lookup"
        layers = ["match", "goal", "player", "award", "team"]
    elif any(term in lowered for term in SCORER_TERMS):
        intent = "player_or_goal_lookup"
        layers = ["goal", "award", "player", "match"]
    elif any(term in lowered for term in HOST_TERMS):
        intent = "tournament_lookup"
        layers = ["tournament"]

    filters["entity_types"] = layers

    return ParsedQuery(
        text=message,
        years=years,
        competition=competition,
        filters=filters,
        invalid_reason=invalid_reason,
        intent=intent,
        query_rewrite=query_rewrite,
        layers=layers,
    )


def _mode_intent(query_mode: str) -> tuple[str, list[str]]:
    modes = {
        "matches": ("match_lookup", ["match", "goal"]),
        "teams": ("team_arc", ["team", "standing", "match"]),
        "players": ("player_or_goal_lookup", ["player", "goal", "award"]),
        "tournaments": ("tournament_lookup", ["tournament", "standing"]),
        "schema": ("schema_question", ["schema"]),
        "compare_eras": ("comparison", ["team", "tournament", "standing", "goal", "award"]),
    }
    return modes.get(query_mode, ("factual_lookup", ["tournament", "match", "team", "standing", "award", "goal", "player"]))


def _rewrite_query(message: str, years: list[int]) -> str:
    lowered = message.lower()
    additions: list[str] = []
    if "best scorer" in lowered or "top scorer" in lowered:
        additions.extend(["Golden Boot", "goals", "goal leaders"])
    if "hero" in lowered or "winning goal" in lowered:
        additions.extend(["final", "winning goal", "goal scorer", "match narrative"])
    if len(years) > 1:
        additions.extend(["team performance timeline", "stage reached", "record", "goals for against"])
    if any(term in lowered for term in SCHEMA_TERMS):
        additions.extend(["codebook", "dataset description", "variable description"])
    if not additions:
        return message
    return f"{message} {' '.join(additions)}"
