import re
from collections import defaultdict
from pathlib import Path

from app.schemas.documents import SourceRef, WorldCupDocument
from app.core.config import settings
from app.rag.corpus.sources import OPENFOOTBALL_FILES, read_text_url as _read_text_url
from app.rag.corpus.utils import (
    chunk_football_txt as _chunk_football_txt,
    competition as _competition,
    empty_player_stat as _empty_player_stat,
    is_notable_player as _is_notable_player,
    merge_player_stats as _merge_player_stats,
    player_name as _player_name,
    position_label as _position_label,
    stage_reached as _stage_reached,
    year as _year,
)


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


def _build_match_docs(rows: list[dict[str, str]], goals: list[dict[str, str]]) -> list[WorldCupDocument]:
    goals_by_match: dict[str, list[dict[str, str]]] = defaultdict(list)
    for goal in goals:
        goals_by_match[goal["match_id"]].append(goal)

    documents: list[WorldCupDocument] = []
    for row in rows:
        year = _year(row)
        competition = _competition(row)
        penalties = ""
        if row.get("penalty_shootout") == "1":
            penalties = f" The match was decided on penalties, with penalty score {row.get('score_penalties')}."
        extra_time = " after extra time" if row.get("extra_time") == "1" else ""
        location = ", ".join(part for part in [row.get("stadium_name"), row.get("city_name"), row.get("country_name")] if part)
        winner_sentence = ""
        if row.get("home_team_win") == "1":
            winner_sentence = f" {row['home_team_name']} won the match against {row['away_team_name']}."
        elif row.get("away_team_win") == "1":
            winner_sentence = f" {row['away_team_name']} won the match against {row['home_team_name']}."
        elif row.get("draw") == "1":
            winner_sentence = " The match was recorded as a draw."
        scorer_sentence = _match_scorer_sentence(goals_by_match.get(row["match_id"], []))
        text = (
            f"{row['match_name']} was a {row['stage_name']} match at the {row['tournament_name']} "
            f"on {row['match_date']}. The score was {row['score']}{extra_time}: "
            f"{row['home_team_name']} {row['home_team_score']}, {row['away_team_name']} {row['away_team_score']}. "
            f"The result was {row['result']}.{winner_sentence}{scorer_sentence} "
            f"It was played at {location}.{penalties}"
        )
        source_refs = [SourceRef(table="matches", record_id=row["match_id"])]
        source_refs.extend(
            SourceRef(table="goals", record_id=goal["goal_id"])
            for goal in goals_by_match.get(row["match_id"], [])[:12]
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
                    "scorers": [_player_name(goal) for goal in goals_by_match.get(row["match_id"], [])],
                },
                source_refs=source_refs,
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


def _match_scorer_sentence(goals: list[dict[str, str]]) -> str:
    if not goals:
        return ""
    scorer_bits = []
    for goal in goals:
        player = _player_name(goal)
        minute = goal.get("minute_label", "")
        team = goal.get("team_name", "")
        qualifier = " own goal" if goal.get("own_goal") == "1" else ""
        qualifier = " penalty" if goal.get("penalty") == "1" else qualifier
        scorer_bits.append(f"{player} ({team}, {minute}{qualifier})")
    return f" Goals were scored by: {'; '.join(scorer_bits)}."


def _build_team_performance_docs(
    appearances: list[dict[str, str]], standings: list[dict[str, str]], qualified_teams: list[dict[str, str]]
) -> tuple[list[WorldCupDocument], list[WorldCupDocument]]:
    standing_positions = {
        (row["tournament_id"], row["team_id"]): int(row["position"]) for row in standings
    }
    performances = {
        (row["tournament_id"], row["team_id"]): row["performance"] for row in qualified_teams
    }
    by_team_tournament: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in appearances:
        by_team_tournament[(row["team_id"], row["tournament_id"])].append(row)

    tournament_docs: list[WorldCupDocument] = []
    summaries_by_team: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)

    for (team_id, tournament_id), rows in by_team_tournament.items():
        first = rows[0]
        year = _year(first)
        competition = _competition(first)
        wins = sum(int(row["win"]) for row in rows)
        losses = sum(int(row["lose"]) for row in rows)
        draws = sum(int(row["draw"]) for row in rows)
        goals_for = sum(int(row["goals_for"]) for row in rows)
        goals_against = sum(int(row["goals_against"]) for row in rows)
        stage_reached = performances.get((tournament_id, team_id)) or _stage_reached(row["stage_name"] for row in rows)
        position = standing_positions.get((tournament_id, team_id))
        placement = f" and finished {_position_label(position)}" if position else ""
        text = (
            f"{first['team_name']} at the {first['tournament_name']}: reached the {stage_reached}{placement}. "
            f"Record: {wins} wins, {draws} draws, {losses} losses. "
            f"Goals: {goals_for} for and {goals_against} against."
        )
        tournament_docs.append(
            WorldCupDocument(
                doc_id=f"fjelstul:team-performance:{tournament_id}:{team_id}",
                entity_type="team",
                competition=competition,
                tournament_year=year,
                title=f"{first['team_name']} at {first['tournament_name']}",
                text=text,
                metadata={
                    "source": "jfjelstul/worldcup",
                    "team": first["team_name"],
                    "team_code": first["team_code"],
                    "stage_reached": stage_reached,
                    "wins": wins,
                    "draws": draws,
                    "losses": losses,
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    "position": position,
                },
                source_refs=[SourceRef(table="team_appearances", record_id=row["key_id"]) for row in rows[:20]],
            )
        )
        summaries_by_team[(first["team_name"], competition)].append(
            {
                "year": year,
                "text": (
                    f"{year}: reached the {stage_reached}"
                    f"{placement}; {wins}W-{draws}D-{losses}L; goals {goals_for}-{goals_against}"
                ),
                "record_ids": [row["key_id"] for row in rows[:20]],
            }
        )

    timeline_docs: list[WorldCupDocument] = []
    for (team_name, competition), summaries in summaries_by_team.items():
        sorted_summaries = sorted(summaries, key=lambda item: int(item["year"]))
        if len(sorted_summaries) < 2:
            continue
        years = [int(item["year"]) for item in sorted_summaries]
        timeline = "; ".join(str(item["text"]) for item in sorted_summaries)
        timeline_docs.append(
            WorldCupDocument(
                doc_id=f"fjelstul:team-timeline:{competition}:{team_name.lower().replace(' ', '-')}",
                entity_type="team",
                competition=competition,
                tournament_year=max(years),
                title=f"{team_name} World Cup performance timeline",
                text=f"{team_name}'s {competition}'s World Cup performance timeline: {timeline}.",
                metadata={"source": "jfjelstul/worldcup", "team": team_name, "years": years},
                source_refs=[
                    SourceRef(table="team_appearances", record_id=record_id)
                    for item in sorted_summaries
                    for record_id in item["record_ids"][:2]
                ],
            )
        )

    return tournament_docs, timeline_docs


def _build_player_profile_docs(
    players: list[dict[str, str]],
    appearances: list[dict[str, str]],
    goals: list[dict[str, str]],
    squads: list[dict[str, str]],
    awards: list[dict[str, str]],
) -> list[WorldCupDocument]:
    player_names: dict[str, str] = {}
    player_tournament_lists: dict[str, str] = {}
    player_female: dict[str, bool] = {}
    for row in players:
        player_names[row["player_id"]] = _player_name(row)
        player_tournament_lists[row["player_id"]] = row.get("list_tournaments", "")
        player_female[row["player_id"]] = row.get("female") == "1"

    appearance_stats: dict[str, dict[str, object]] = defaultdict(lambda: _empty_player_stat())
    for row in appearances:
        stat = appearance_stats[row["player_id"]]
        stat["appearances"] = int(stat["appearances"]) + 1
        stat["starts"] = int(stat["starts"]) + int(row.get("starter", "0") or 0)
        stat["substitutes"] = int(stat["substitutes"]) + int(row.get("substitute", "0") or 0)
        stat["teams"].add(row["team_name"])
        stat["tournaments"].add(_year(row))
        stat["source_refs"].append(SourceRef(table="player_appearances", record_id=row["key_id"]))
        player_names.setdefault(row["player_id"], _player_name(row))

    squad_stats: dict[str, dict[str, object]] = defaultdict(lambda: _empty_player_stat())
    for row in squads:
        stat = squad_stats[row["player_id"]]
        stat["teams"].add(row["team_name"])
        stat["tournaments"].add(_year(row))
        stat["positions"].add(row.get("position_name", ""))
        stat["source_refs"].append(SourceRef(table="squads", record_id=row["key_id"]))
        player_names.setdefault(row["player_id"], _player_name(row))

    goal_stats: dict[str, dict[str, object]] = defaultdict(lambda: _empty_player_stat())
    for row in goals:
        stat = goal_stats[row["player_id"]]
        if row.get("own_goal") != "1":
            stat["goals"] = int(stat["goals"]) + 1
        if row.get("penalty") == "1":
            stat["penalty_goals"] = int(stat["penalty_goals"]) + 1
        stat["teams"].add(row.get("player_team_name") or row.get("team_name", ""))
        stat["tournaments"].add(_year(row))
        stat["source_refs"].append(SourceRef(table="goals", record_id=row["goal_id"]))
        player_names.setdefault(row["player_id"], _player_name(row))

    award_stats: dict[str, dict[str, object]] = defaultdict(lambda: _empty_player_stat())
    for row in awards:
        stat = award_stats[row["player_id"]]
        stat["awards"].append(f"{row['award_name']} ({_year(row)})")
        stat["teams"].add(row["team_name"])
        stat["tournaments"].add(_year(row))
        stat["source_refs"].append(SourceRef(table="award_winners", record_id=row["key_id"]))
        player_names.setdefault(row["player_id"], _player_name(row))

    documents: list[WorldCupDocument] = []
    for player_id, player in player_names.items():
        stat = _merge_player_stats(
            appearance_stats.get(player_id),
            squad_stats.get(player_id),
            goal_stats.get(player_id),
            award_stats.get(player_id),
        )
        appearances_count = int(stat["appearances"])
        goals_count = int(stat["goals"])
        awards_list = list(stat["awards"])
        tournaments = sorted(int(year) for year in stat["tournaments"] if int(year) > 0)
        listed_tournaments = player_tournament_lists.get(player_id)
        if not _is_notable_player(appearances_count, goals_count, awards_list, tournaments, listed_tournaments):
            continue

        teams = sorted(str(team) for team in stat["teams"] if team)
        positions = sorted(str(position) for position in stat["positions"] if position and position != "not applicable")
        tournament_text = ", ".join(str(year) for year in tournaments) or listed_tournaments or "not available"
        award_text = "; ".join(awards_list) if awards_list else "no individual awards in the award winners table"
        text = (
            f"{player} World Cup profile: tournaments {tournament_text}. "
            f"Teams represented: {', '.join(teams) if teams else 'not available'}. "
            f"Recorded appearances since 1970: {appearances_count}, including {stat['starts']} starts "
            f"and {stat['substitutes']} substitute appearances. "
            f"Recorded goals: {goals_count}. Awards: {award_text}."
        )
        if positions:
            text += f" Listed squad positions include {', '.join(positions)}."

        documents.append(
            WorldCupDocument(
                doc_id=f"fjelstul:player-profile:{player_id}",
                entity_type="player",
                competition="women" if player_female.get(player_id, False) else "men",
                tournament_year=max(tournaments) if tournaments else 0,
                title=f"{player} World Cup Profile",
                text=text,
                metadata={
                    "source": "tom-local-fjelstul",
                    "player": player,
                    "teams": teams,
                    "years": tournaments,
                    "goals": goals_count,
                    "appearances": appearances_count,
                    "awards": awards_list,
                },
                source_refs=list(stat["source_refs"])[:30],
            )
        )
    return documents


def _build_goal_story_docs(goals: list[dict[str, str]], awards: list[dict[str, str]]) -> list[WorldCupDocument]:
    documents: list[WorldCupDocument] = []
    goals_by_tournament_player: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for goal in goals:
        if goal.get("own_goal") == "1":
            continue
        goals_by_tournament_player[(goal["tournament_id"], goal["player_id"])].append(goal)

    golden_boots = {
        (row["tournament_id"], row["player_id"])
        for row in awards
        if row.get("award_name") == "Golden Boot"
    }
    leaders_by_tournament: dict[str, list[tuple[str, int, str, str]]] = defaultdict(list)
    for (tournament_id, player_id), player_goals in goals_by_tournament_player.items():
        first = player_goals[0]
        player = _player_name(first)
        count_goals = len(player_goals)
        leaders_by_tournament[tournament_id].append((player, count_goals, first["team_name"], first["tournament_name"]))
        if count_goals < 3 and (tournament_id, player_id) not in golden_boots:
            continue
        text = (
            f"{player} scored {count_goals} goals for {first['team_name']} at the {first['tournament_name']}. "
            f"Goal minutes: {', '.join(goal['minute_label'] for goal in player_goals[:20])}."
        )
        if (tournament_id, player_id) in golden_boots:
            text += " This player is listed as a Golden Boot winner in the award winners table."
        documents.append(
            WorldCupDocument(
                doc_id=f"fjelstul:goal-story:{tournament_id}:{player_id}",
                entity_type="goal",
                competition=_competition(first),
                tournament_year=_year(first),
                title=f"{player} goals at {first['tournament_name']}",
                text=text,
                metadata={
                    "source": "tom-local-fjelstul",
                    "player": player,
                    "team": first["team_name"],
                    "goals": count_goals,
                    "award_signal": "Golden Boot" if (tournament_id, player_id) in golden_boots else "",
                },
                source_refs=[SourceRef(table="goals", record_id=goal["goal_id"]) for goal in player_goals[:20]],
            )
        )

    for tournament_id, leaders in leaders_by_tournament.items():
        if not leaders:
            continue
        sorted_leaders = sorted(leaders, key=lambda item: item[1], reverse=True)[:8]
        tournament_name = sorted_leaders[0][3]
        year = int(tournament_id.replace("WC-", ""))
        text = "Top goal scorers in the " + tournament_name + ": " + "; ".join(
            f"{player} ({team}) with {count_goals} goals" for player, count_goals, team, _ in sorted_leaders
        ) + "."
        documents.append(
            WorldCupDocument(
                doc_id=f"fjelstul:goal-leaders:{tournament_id}",
                entity_type="goal",
                competition="women" if "Women's" in tournament_name else "men",
                tournament_year=year,
                title=f"{tournament_name} Goal Leaders",
                text=text,
                metadata={"source": "tom-local-fjelstul", "leaders": [leader[0] for leader in sorted_leaders]},
                source_refs=[SourceRef(table="goals", record_id=tournament_id)],
            )
        )
    return documents


def _build_codebook_docs(
    datasets: list[dict[str, str]], variables: list[dict[str, str]]
) -> list[WorldCupDocument]:
    documents: list[WorldCupDocument] = []
    dataset_labels = {row["dataset_id"]: row.get("dataset", "") for row in datasets}
    for row in datasets:
        dataset = row["dataset"]
        text = f"Dataset: {dataset}. Label: {row.get('label', dataset)}. Description: {row['description']}"
        documents.append(
            WorldCupDocument(
                doc_id=f"tom-codebook:dataset:{dataset}",
                entity_type="schema",
                competition="men",
                tournament_year=0,
                title=f"Codebook Dataset: {dataset}",
                text=text,
                metadata={
                    "source": "tom-codebook",
                    "doc_type": "dataset",
                    "dataset": dataset,
                    "label": row.get("label", dataset),
                    "count_variables": row.get("count_variables", ""),
                    "count_observations": row.get("count_observations", ""),
                },
                source_refs=[SourceRef(table="codebook/datasets", record_id=row["dataset_id"])],
            )
        )

    for row in variables:
        dataset = dataset_labels.get(row["dataset_id"], row["dataset_id"])
        variable = row["variable"]
        text = (
            f"Variable: {variable}. Dataset: {dataset}. Type: {row['type']}. "
            f"Description: {row['description']}"
        )
        documents.append(
            WorldCupDocument(
                doc_id=f"tom-codebook:variable:{dataset}:{variable}",
                entity_type="schema",
                competition="men",
                tournament_year=0,
                title=f"Codebook Variable: {dataset}.{variable}",
                text=text,
                metadata={
                    "source": "tom-codebook",
                    "doc_type": "variable",
                    "dataset": dataset,
                    "variable": variable,
                    "type": row["type"],
                },
                source_refs=[SourceRef(table="codebook/variables", record_id=f"{row['dataset_id']}:{row['variable_id']}")],
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


def _build_press_article_docs() -> list[WorldCupDocument]:
    articles_dir = Path(settings.press_articles_dir)
    if not articles_dir.exists():
        return []

    documents: list[WorldCupDocument] = []
    paths = sorted(
        path
        for path in articles_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".md"}
    )
    for index, path in enumerate(paths, start=1):
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        year_match = re.search(r"\b(19[3-9][0-9]|20[0-9][0-9])\b", text)
        year = int(year_match.group(1)) if year_match else 0
        title = path.stem.replace("_", " ").replace("-", " ").title()
        documents.append(
            WorldCupDocument(
                doc_id=f"press:article:{index}:{path.stem}",
                entity_type="article",
                competition="women" if "women" in text.lower() else "men",
                tournament_year=year,
                title=title,
                text=text[:5000],
                metadata={"source": "local-press", "path": str(path), "filename": path.name},
                source_refs=[SourceRef(table="press_articles", record_id=str(path))],
            )
        )
    return documents


build_tournament_docs = _build_tournament_docs
build_match_docs = _build_match_docs
build_standing_docs = _build_standing_docs
build_tournament_standing_summaries = _build_tournament_standing_summaries
build_team_performance_docs = _build_team_performance_docs
build_player_profile_docs = _build_player_profile_docs
build_goal_story_docs = _build_goal_story_docs
build_codebook_docs = _build_codebook_docs
build_award_docs = _build_award_docs
build_openfootball_docs = _build_openfootball_docs
build_press_article_docs = _build_press_article_docs
