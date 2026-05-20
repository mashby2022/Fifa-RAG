import csv
import io
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen

from app.schemas.documents import SourceRef, WorldCupDocument

FJELSTUL_BASE = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv"
OPENFOOTBALL_BASE = "https://raw.githubusercontent.com/openfootball/worldcup/master"

FJELSTUL_FILES = {
    "tournaments": f"{FJELSTUL_BASE}/tournaments.csv",
    "matches": f"{FJELSTUL_BASE}/matches.csv",
    "tournament_standings": f"{FJELSTUL_BASE}/tournament_standings.csv",
    "award_winners": f"{FJELSTUL_BASE}/award_winners.csv",
}

OPENFOOTBALL_FILES = {
    "openfootball_2026_cup": f"{OPENFOOTBALL_BASE}/2026--usa/cup.txt",
    "openfootball_2026_finals": f"{OPENFOOTBALL_BASE}/2026--usa/cup_finals.txt",
    "openfootball_2022_cup": f"{OPENFOOTBALL_BASE}/2022--qatar/cup.txt",
}


def build_worldcup_documents(output_path: Path) -> list[WorldCupDocument]:
    tables = {name: _read_csv_url(url) for name, url in FJELSTUL_FILES.items()}
    documents: list[WorldCupDocument] = []

    documents.extend(_build_tournament_docs(tables["tournaments"]))
    documents.extend(_build_match_docs(tables["matches"]))
    documents.extend(_build_standing_docs(tables["tournament_standings"]))
    documents.extend(_build_tournament_standing_summaries(tables["tournament_standings"]))
    documents.extend(_build_award_docs(tables["award_winners"]))
    documents.extend(_build_openfootball_docs())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for doc in documents:
            handle.write(json.dumps(doc.model_dump(), ensure_ascii=True) + "\n")

    return documents


def _read_csv_url(url: str) -> list[dict[str, str]]:
    with urlopen(url, timeout=30) as response:
        text = response.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _read_text_url(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def _competition(row: dict[str, str]) -> str:
    return "women" if "Women's" in row.get("tournament_name", "") else "men"


def _year(row: dict[str, str]) -> int:
    match = re.search(r"\b(19[0-9]{2}|20[0-9]{2})\b", row.get("tournament_name", ""))
    return int(row.get("year") or (match.group(1) if match else "0"))


def _player_name(row: dict[str, str]) -> str:
    given = row.get("given_name", "")
    family = row.get("family_name", "")
    if given == "not applicable":
        given = ""
    return " ".join(part for part in [given, family] if part).strip()


def _build_tournament_docs(rows: list[dict[str, str]]) -> list[WorldCupDocument]:
    documents: list[WorldCupDocument] = []
    for row in rows:
        year = _year(row)
        competition = _competition(row)
        text = (
            f"{row['tournament_name']} was hosted by {row['host_country']} from {row['start_date']} "
            f"to {row['end_date']}. {row['winner']} won the tournament. "
            f"The tournament included {row['count_teams']} teams."
        )
        documents.append(
            WorldCupDocument(
                doc_id=f"fjelstul:tournament:{row['tournament_id']}",
                entity_type="tournament",
                competition=competition,
                tournament_year=year,
                title=f"{row['tournament_name']} Overview",
                text=text,
                metadata={
                    "source": "jfjelstul/worldcup",
                    "host": row["host_country"],
                    "winner": row["winner"],
                    "start_date": row["start_date"],
                    "end_date": row["end_date"],
                },
                source_refs=[SourceRef(table="tournaments", record_id=row["tournament_id"])],
            )
        )
    return documents


def _build_match_docs(rows: list[dict[str, str]]) -> list[WorldCupDocument]:
    documents: list[WorldCupDocument] = []
    for row in rows:
        year = _year(row)
        competition = _competition(row)
        penalties = ""
        if row.get("penalty_shootout") == "1":
            penalties = f" The match was decided on penalties, with penalty score {row.get('score_penalties')}."
        extra_time = " after extra time" if row.get("extra_time") == "1" else ""
        location = ", ".join(part for part in [row.get("stadium_name"), row.get("city_name"), row.get("country_name")] if part)
        text = (
            f"{row['match_name']} was a {row['stage_name']} match at the {row['tournament_name']} "
            f"on {row['match_date']}. The score was {row['score']}{extra_time}: "
            f"{row['home_team_name']} {row['home_team_score']}, {row['away_team_name']} {row['away_team_score']}. "
            f"The result was {row['result']}. It was played at {location}.{penalties}"
        )
        documents.append(
            WorldCupDocument(
                doc_id=f"fjelstul:match:{row['match_id']}",
                entity_type="match",
                competition=competition,
                tournament_year=year,
                title=f"{row['tournament_name']}: {row['match_name']} ({row['stage_name']})",
                text=text,
                metadata={
                    "source": "jfjelstul/worldcup",
                    "stage": row["stage_name"],
                    "teams": [row["home_team_name"], row["away_team_name"]],
                    "score": row["score"],
                    "date": row["match_date"],
                    "stadium": row["stadium_name"],
                    "city": row["city_name"],
                },
                source_refs=[SourceRef(table="matches", record_id=row["match_id"])],
            )
        )
    return documents


def _build_standing_docs(rows: list[dict[str, str]]) -> list[WorldCupDocument]:
    documents: list[WorldCupDocument] = []
    for row in rows:
        year = _year(row)
        competition = _competition(row)
        position = int(row["position"])
        stage = _position_label(position)
        text = f"{row['team_name']} finished {stage} at the {row['tournament_name']}."
        documents.append(
            WorldCupDocument(
                doc_id=f"fjelstul:standing:{row['tournament_id']}:{row['team_id']}",
                entity_type="standing",
                competition=competition,
                tournament_year=year,
                title=f"{row['team_name']} at {row['tournament_name']}",
                text=text,
                metadata={
                    "source": "jfjelstul/worldcup",
                    "team": row["team_name"],
                    "team_code": row["team_code"],
                    "position": position,
                },
                source_refs=[SourceRef(table="tournament_standings", record_id=row["key_id"])],
            )
        )
    return documents


def _build_tournament_standing_summaries(rows: list[dict[str, str]]) -> list[WorldCupDocument]:
    by_tournament: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_tournament[row["tournament_id"]].append(row)

    documents: list[WorldCupDocument] = []
    for tournament_id, tournament_rows in by_tournament.items():
        sorted_rows = sorted(tournament_rows, key=lambda item: int(item["position"]))
        first = sorted_rows[0]
        year = _year(first)
        podium = "; ".join(f"{row['position']}: {row['team_name']}" for row in sorted_rows[:4])
        text = f"Final standings for the {first['tournament_name']}: {podium}."
        documents.append(
            WorldCupDocument(
                doc_id=f"fjelstul:standings-summary:{tournament_id}",
                entity_type="standing",
                competition=_competition(first),
                tournament_year=year,
                title=f"{first['tournament_name']} Final Standings",
                text=text,
                metadata={"source": "jfjelstul/worldcup", "standings": podium},
                source_refs=[SourceRef(table="tournament_standings", record_id=tournament_id)],
            )
        )
    return documents


def _build_award_docs(rows: list[dict[str, str]]) -> list[WorldCupDocument]:
    documents: list[WorldCupDocument] = []
    for row in rows:
        year = _year(row)
        competition = _competition(row)
        player = _player_name(row)
        shared = " shared" if row.get("shared") == "1" else ""
        text = (
            f"{player} of {row['team_name']} won the{shared} {row['award_name']} "
            f"at the {row['tournament_name']}."
        )
        documents.append(
            WorldCupDocument(
                doc_id=f"fjelstul:award:{row['key_id']}",
                entity_type="award",
                competition=competition,
                tournament_year=year,
                title=f"{row['tournament_name']}: {row['award_name']} winner",
                text=text,
                metadata={
                    "source": "jfjelstul/worldcup",
                    "award": row["award_name"],
                    "player": player,
                    "team": row["team_name"],
                },
                source_refs=[SourceRef(table="award_winners", record_id=row["key_id"])],
            )
        )
    return documents


def _build_openfootball_docs() -> list[WorldCupDocument]:
    documents: list[WorldCupDocument] = []
    for name, url in OPENFOOTBALL_FILES.items():
        text = _read_text_url(url)
        year_match = re.search(r"/(\d{4})--", url)
        year = int(year_match.group(1)) if year_match else 0
        chunks = _chunk_football_txt(text)
        for index, chunk in enumerate(chunks, start=1):
            title = f"OpenFootball World Cup {year} fixtures, part {index}"
            documents.append(
                WorldCupDocument(
                    doc_id=f"openfootball:{name}:{index}",
                    entity_type="tournament",
                    competition="men",
                    tournament_year=year,
                    title=title,
                    text=(
                        f"OpenFootball fixture data for the {year} World Cup, source file {url}. "
                        f"Relevant excerpt: {chunk}"
                    ),
                    metadata={"source": "openfootball/worldcup", "source_url": url, "chunk": index},
                    source_refs=[SourceRef(table="openfootball_football_txt", record_id=f"{name}:{index}")],
                )
            )
    return documents


def _chunk_football_txt(text: str, max_chars: int = 1800) -> list[str]:
    clean_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        clean_lines.append(stripped)

    chunks: list[str] = []
    current = ""
    for line in clean_lines:
        next_value = f"{current}\n{line}".strip()
        if len(next_value) > max_chars and current:
            chunks.append(current)
            current = line
        else:
            current = next_value
    if current:
        chunks.append(current)
    return chunks


def _position_label(position: int) -> str:
    if position == 1:
        return "as champion"
    if position == 2:
        return "as runner-up"
    if position == 3:
        return "in third place"
    if position == 4:
        return "in fourth place"
    return f"in position {position}"
