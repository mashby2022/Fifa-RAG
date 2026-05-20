from app.schemas.documents import WorldCupDocument


KNOCKOUT_STAGE_PRIORITIES = {
    "final": 980,
    "semi-finals": 840,
    "semi-final": 840,
    "quarter-finals": 790,
    "quarter-final": 790,
    "round of 16": 750,
    "third-place match": 730,
}

FEATURED_TEAMS = {
    "Argentina",
    "Brazil",
    "Croatia",
    "England",
    "France",
    "Germany",
    "Italy",
    "Japan",
    "Mexico",
    "Netherlands",
    "Portugal",
    "Spain",
    "United States",
    "Uruguay",
}

FEATURED_PLAYERS = {
    "Cristiano Ronaldo",
    "Kylian Mbappe",
    "Kylian Mbappé",
    "Lionel Messi",
    "Marta",
    "Megan Rapinoe",
    "Mia Hamm",
    "Miroslav Klose",
    "Mario Götze",
    "Pele",
    "Pelé",
    "Ronaldo",
    "Thomas Müller",
    "Zinedine Zidane",
}

CORE_SCHEMA_DATASETS = {
    "award_winners",
    "goals",
    "matches",
    "player_appearances",
    "players",
    "qualified_teams",
    "squads",
    "team_appearances",
    "tournament_standings",
    "tournaments",
}


def select_demo_documents(
    documents: list[WorldCupDocument],
    max_docs: int,
) -> list[WorldCupDocument]:
    ranked = [(demo_priority(doc), index, doc) for index, doc in enumerate(documents)]
    selected = [item for item in ranked if item[0] > 0]
    selected.sort(key=lambda item: (-item[0], item[1]))
    return [doc for _, _, doc in selected[:max_docs]]


def demo_priority(doc: WorldCupDocument) -> int:
    if doc.entity_type == "tournament":
        return 1000 + doc.tournament_year
    if doc.entity_type == "schema":
        return schema_priority(doc)
    if doc.entity_type == "standing":
        return standing_priority(doc)
    if doc.entity_type == "team":
        return team_priority(doc)
    if doc.entity_type == "match":
        return match_priority(doc)
    if doc.entity_type == "award":
        return award_priority(doc)
    if doc.entity_type == "goal":
        return goal_priority(doc)
    if doc.entity_type == "player":
        return player_priority(doc)
    return 0


def schema_priority(doc: WorldCupDocument) -> int:
    if doc.metadata.get("doc_type") == "dataset":
        return 960
    if doc.metadata.get("dataset") in CORE_SCHEMA_DATASETS:
        return 820
    return 0


def standing_priority(doc: WorldCupDocument) -> int:
    if "standings-summary" in doc.doc_id:
        return 900 + doc.tournament_year
    position = doc.metadata.get("position")
    return 860 if isinstance(position, int) and position <= 4 else 0


def team_priority(doc: WorldCupDocument) -> int:
    team = doc.metadata.get("team")
    if "timeline" in doc.doc_id:
        return 950
    if isinstance(team, str) and team in FEATURED_TEAMS and doc.tournament_year >= 1990:
        return 830 + doc.tournament_year
    return 0


def match_priority(doc: WorldCupDocument) -> int:
    stage = str(doc.metadata.get("stage", "")).lower()
    if stage in KNOCKOUT_STAGE_PRIORITIES:
        return KNOCKOUT_STAGE_PRIORITIES[stage] + doc.tournament_year

    teams = doc.metadata.get("teams")
    if doc.tournament_year >= 2010 and isinstance(teams, list):
        if any(isinstance(team, str) and team in FEATURED_TEAMS for team in teams):
            return 650 + doc.tournament_year
    return 0


def award_priority(doc: WorldCupDocument) -> int:
    award = str(doc.metadata.get("award", ""))
    if award in {"Golden Boot", "Golden Ball", "Golden Glove"}:
        return 880 + doc.tournament_year
    return 760 + doc.tournament_year


def goal_priority(doc: WorldCupDocument) -> int:
    if "goal-leaders" in doc.doc_id:
        return 900 + doc.tournament_year
    if doc.metadata.get("award_signal") == "Golden Boot":
        return 880 + doc.tournament_year
    if int(doc.metadata.get("goals", 0) or 0) >= 4:
        return 850 + doc.tournament_year
    player = doc.metadata.get("player")
    if isinstance(player, str) and player in FEATURED_PLAYERS:
        return 830 + doc.tournament_year
    return 0


def player_priority(doc: WorldCupDocument) -> int:
    player = doc.metadata.get("player")
    if isinstance(player, str) and player in FEATURED_PLAYERS:
        return 890 + doc.tournament_year
    if doc.metadata.get("awards"):
        return 860 + doc.tournament_year
    if int(doc.metadata.get("goals", 0) or 0) >= 4:
        return 830 + doc.tournament_year
    if int(doc.metadata.get("appearances", 0) or 0) >= 15:
        return 790 + doc.tournament_year
    return 0
