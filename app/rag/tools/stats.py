import csv
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.rag.corpus.sources import load_table


STATS_TERMS = {
    "how many",
    "count",
    "total",
    "most",
    "least",
    "average",
    "top",
    "rank",
    "place",
    "placed",
    "placement",
    "finish",
    "finished",
    "highest",
    "best",
    "furthest",
    "stats",
    "statistics",
}

PERFORMANCE_RANKS = {
    "final": 8,
    "final round": 7,
    "semi-finals": 6,
    "third-place match": 6,
    "quarter-final": 5,
    "quarter-finals": 5,
    "round of 16": 4,
    "second group stage": 3,
    "group stage": 2,
}

TEAM_ALIASES = {
    "nigerian": "Nigeria",
    "nigerian team": "Nigeria",
    "super eagles": "Nigeria",
}


@dataclass
class ToolAnswer:
    tool_name: str
    answer: str
    citations: list[dict[str, str]]
    diagnostics: dict[str, Any] = field(default_factory=dict)
    worklog: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


class DuckDBStatsTool:
    def __init__(self, db_path: str = settings.duckdb_path, raw_data_dir: str = f"{settings.local_data_dir}/raw"):
        self.db_path = Path(db_path)
        self.raw_data_dir = Path(raw_data_dir)
        self._duckdb_available = self._has_duckdb()

    @property
    def available(self) -> bool:
        return settings.enable_duckdb_tool

    @property
    def backend(self) -> str:
        if self._duckdb_available and self.db_path.exists():
            return "duckdb"
        if self.raw_data_dir.exists():
            return "csv-fallback"
        return "github-fallback"

    def maybe_answer(self, question: str) -> ToolAnswer | None:
        if not self.available or not _looks_like_stats_question(question):
            return None

        lowered = question.lower()
        if "schema" in lowered or "table" in lowered or "column" in lowered:
            return self.schema_answer()
        if _looks_like_team_finish_question(lowered):
            return self.team_best_finish_answer(question)
        if "top scorer" in lowered or "golden boot" in lowered:
            return self.top_scorer_answer(question)
        if "how many goals" in lowered or ("total" in lowered and "goal" in lowered):
            return self.goal_count_answer(question)
        if "how many matches" in lowered or ("count" in lowered and "match" in lowered):
            return self.match_count_answer(question)
        if "most goals" in lowered and "team" in lowered:
            return self.team_goals_answer(question)
        return None

    def team_best_finish_answer(self, question: str) -> ToolAnswer | None:
        team = self._team_from_question(question)
        if not team:
            return None

        rows = [
            row
            for row in self._table_rows("qualified_teams")
            if row.get("team_name", "").casefold() == team.casefold()
        ]
        lowered = question.lower()
        if "women" in lowered:
            rows = [row for row in rows if "Women's World Cup" in row.get("tournament_name", "")]
            scope = "women's"
        elif _asks_overall_competition(lowered):
            scope = "overall"
        else:
            rows = [row for row in rows if "Men's World Cup" in row.get("tournament_name", "")]
            scope = "men's"

        ranked = [
            (PERFORMANCE_RANKS.get(row.get("performance", "").lower(), 0), _row_year(row) or 0, row)
            for row in rows
        ]
        ranked = [item for item in ranked if item[0] > 0]
        if not ranked:
            return None

        best_rank = max(rank for rank, _, _ in ranked)
        best_rows = [row for rank, _, row in ranked if rank == best_rank]
        best_rows.sort(key=lambda row: _row_year(row) or 0)
        performance = best_rows[0].get("performance", "best finish")
        tournaments = ", ".join(row.get("tournament_name", "") for row in best_rows)

        answer = f"{team}'s highest World Cup finish"
        if scope in {"men's", "women's"}:
            answer += f" in the {scope} tournament"
        answer += f" was {performance}, reached at {tournaments}."

        if scope == "overall":
            mens_rows = [row for _, _, row in ranked if "Men's World Cup" in row.get("tournament_name", "")]
            mens_best = self._best_performance_rows(mens_rows)
            if mens_best and mens_best[0].get("performance") != performance:
                mens_tournaments = ", ".join(row.get("tournament_name", "") for row in mens_best)
                answer += (
                    f" In the men's tournament, {team}'s best finish was "
                    f"{mens_best[0].get('performance')}, reached at {mens_tournaments}."
                )

        return ToolAnswer(
            tool_name="duckdb_stats",
            answer=answer,
            citations=[{"table": "qualified_teams", "record_id": row.get("key_id", "")} for row in best_rows[:8]],
            diagnostics={
                "backend": self.backend,
                "rows_scanned": len(rows),
                "operation": "team_best_finish",
                "team": team,
                "scope": scope,
            },
            worklog=["Selected DuckDB", "Schema context ready", "Querying qualified_teams for team finish"],
        )

    def schema_answer(self) -> ToolAnswer | None:
        datasets = self._csv_rows("codebook/datasets")
        if not datasets:
            return None
        table_bits = [
            f"{row.get('dataset')}: {row.get('count_variables', '?')} columns, {row.get('count_observations', '?')} rows"
            for row in datasets[:12]
        ]
        return ToolAnswer(
            tool_name="duckdb_schema",
            answer="DuckDB schema/codebook highlights: " + "; ".join(table_bits) + ".",
            citations=[{"table": "codebook/datasets", "record_id": row.get("dataset_id", "")} for row in datasets[:12]],
            diagnostics={"backend": self.backend, "tables_returned": min(len(datasets), 12)},
        )

    def top_scorer_answer(self, question: str) -> ToolAnswer | None:
        year = _first_year(question)
        goals = self._table_rows("goals")
        if year:
            goals = [row for row in goals if _row_year(row) == year]
        goals = [row for row in goals if row.get("own_goal") != "1"]
        if not goals:
            return None

        counts: Counter[tuple[str, str]] = Counter()
        for row in goals:
            player = _player_name(row)
            team = row.get("team_name") or row.get("player_team_name", "")
            if player:
                counts[(player, team)] += 1
        leaders = counts.most_common(5)
        leader_text = "; ".join(f"{player} ({team}) with {count} goals" for (player, team), count in leaders)
        scope = f" in {year}" if year else ""
        return ToolAnswer(
            tool_name="duckdb_stats",
            answer=f"Top World Cup goal scorers{scope}: {leader_text}.",
            citations=[{"table": "goals", "record_id": f"computed-top-scorers-{year or 'all'}"}],
            diagnostics={"backend": self.backend, "rows_scanned": len(goals), "operation": "group_by_player_goals"},
        )

    def goal_count_answer(self, question: str) -> ToolAnswer | None:
        year = _first_year(question)
        goals = self._table_rows("goals")
        if year:
            goals = [row for row in goals if _row_year(row) == year]
        count = sum(1 for row in goals if row.get("own_goal") != "1")
        scope = f" in {year}" if year else " in the loaded World Cup data"
        return ToolAnswer(
            tool_name="duckdb_stats",
            answer=f"There were {count} non-own-goal goals{scope}.",
            citations=[{"table": "goals", "record_id": f"computed-goal-count-{year or 'all'}"}],
            diagnostics={"backend": self.backend, "rows_scanned": len(goals), "operation": "count_goals"},
        )

    def match_count_answer(self, question: str) -> ToolAnswer | None:
        year = _first_year(question)
        matches = self._table_rows("matches")
        if year:
            matches = [row for row in matches if _row_year(row) == year]
        scope = f" in {year}" if year else " in the loaded World Cup data"
        return ToolAnswer(
            tool_name="duckdb_stats",
            answer=f"There were {len(matches)} matches{scope}.",
            citations=[{"table": "matches", "record_id": f"computed-match-count-{year or 'all'}"}],
            diagnostics={"backend": self.backend, "rows_scanned": len(matches), "operation": "count_matches"},
        )

    def team_goals_answer(self, question: str) -> ToolAnswer | None:
        year = _first_year(question)
        goals = self._table_rows("goals")
        if year:
            goals = [row for row in goals if _row_year(row) == year]
        goals = [row for row in goals if row.get("own_goal") != "1"]
        counts = Counter(row.get("team_name", "") for row in goals if row.get("team_name"))
        leaders = counts.most_common(5)
        if not leaders:
            return None
        leader_text = "; ".join(f"{team} with {count} goals" for team, count in leaders)
        scope = f" in {year}" if year else " in the loaded World Cup data"
        return ToolAnswer(
            tool_name="duckdb_stats",
            answer=f"Teams with the most goals{scope}: {leader_text}.",
            citations=[{"table": "goals", "record_id": f"computed-team-goals-{year or 'all'}"}],
            diagnostics={"backend": self.backend, "rows_scanned": len(goals), "operation": "group_by_team_goals"},
        )

    def _table_rows(self, table: str) -> list[dict[str, str]]:
        if self._duckdb_available and self.db_path.exists():
            rows = self._duckdb_rows(table)
            if rows:
                return rows
        rows = self._csv_rows(table)
        if rows:
            return rows
        return load_table(table, settings.local_data_dir)

    def _duckdb_rows(self, table: str) -> list[dict[str, str]]:
        try:
            import duckdb
        except ImportError:
            return []

        with duckdb.connect(str(self.db_path), read_only=True) as connection:
            result = connection.execute(f"SELECT * FROM {table}")
            columns = [column[0] for column in result.description]
            rows = result.fetchall()
        return [
            {str(key): _stringify(value) for key, value in zip(columns, row)}
            for row in rows
        ]

    def _csv_rows(self, table: str) -> list[dict[str, str]]:
        path = self.raw_data_dir / f"{table}.csv"
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _team_from_question(self, question: str) -> str | None:
        lowered = _normalized(question)
        for alias, team in TEAM_ALIASES.items():
            if _contains_normalized(lowered, alias):
                return team
        teams = self._table_rows("teams") or self._table_rows("qualified_teams")
        aliases = [
            (row.get("team_name", ""), row.get("team_code", ""))
            for row in teams
            if row.get("team_name")
        ]
        aliases.sort(key=lambda item: len(item[0]), reverse=True)
        for name, code in aliases:
            if _contains_normalized(lowered, name) or (code and _contains_normalized(lowered, code)):
                return name
        return None

    @staticmethod
    def _best_performance_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
        ranked = [
            (PERFORMANCE_RANKS.get(row.get("performance", "").lower(), 0), _row_year(row) or 0, row)
            for row in rows
        ]
        ranked = [item for item in ranked if item[0] > 0]
        if not ranked:
            return []
        best_rank = max(rank for rank, _, _ in ranked)
        best_rows = [row for rank, _, row in ranked if rank == best_rank]
        return sorted(best_rows, key=lambda row: _row_year(row) or 0)

    @staticmethod
    def _has_duckdb() -> bool:
        try:
            import duckdb  # noqa: F401
        except ImportError:
            return False
        return True


def _looks_like_stats_question(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in STATS_TERMS)


def _looks_like_team_finish_question(lowered: str) -> bool:
    finish_terms = ("highest", "best", "furthest", "place", "placed", "placement", "finish", "finished")
    return any(term in lowered for term in finish_terms) and "world cup" in lowered


def _asks_overall_competition(lowered: str) -> bool:
    return any(
        phrase in lowered
        for phrase in (
            "overall",
            "across all",
            "all world cups",
            "men and women",
            "men's and women's",
            "mens and womens",
        )
    )


def _first_year(text: str) -> int | None:
    match = re.search(r"\b(19[3-9][0-9]|20[0-9][0-9])\b", text)
    return int(match.group(1)) if match else None


def _row_year(row: dict[str, str]) -> int | None:
    if row.get("year"):
        return int(row["year"])
    match = re.search(r"\b(19[3-9][0-9]|20[0-9][0-9])\b", row.get("tournament_name", ""))
    return int(match.group(1)) if match else None


def _player_name(row: dict[str, str]) -> str:
    given = row.get("given_name", "")
    family = row.get("family_name", "")
    if given == "not applicable":
        given = ""
    return " ".join(part for part in [given, family] if part).strip()


def _normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _contains_normalized(haystack: str, needle: str) -> bool:
    normalized_needle = _normalized(needle)
    if not normalized_needle:
        return False
    return re.search(rf"(?:^|\s){re.escape(normalized_needle)}(?:\s|$)", haystack) is not None


def _stringify(value: object) -> str:
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


stats_tool = DuckDBStatsTool()
