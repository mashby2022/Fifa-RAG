import re
from dataclasses import dataclass
from typing import Any

from app.rag.tools.stats import ToolAnswer, stats_tool


WIN_TERMS = {"who won", "winner", "champion"}
FINAL_OPPONENT_TERMS = {"who did they play", "played against", "opponent"}
SCORE_TERMS = {"score", "final score"}
REFEREE_TERMS = {"referee", "officiated"}
MAP_TERMS = {"map", "graph", "nations represented", "head-to-head", "head to head"}
WEB_CONFIRM_TERMS = {"check the web", "web to confirm", "confirm", "are you sure"}


@dataclass
class ConversationState:
    year: int | None = None
    winner: str | None = None
    final_match_id: str | None = None
    final_match_name: str | None = None
    referee_id: str | None = None
    referee_name: str | None = None


class WorldCupWorkflowTool:
    def __init__(self) -> None:
        self.state = ConversationState()

    def maybe_answer(self, question: str) -> ToolAnswer | None:
        lowered = question.lower()
        year = _first_year(question) or self.state.year

        if year and any(term in lowered for term in MAP_TERMS):
            return self.map_answer(year)
        if _has_score_intent(lowered):
            return self.score_answer(year)
        if any(term in lowered for term in FINAL_OPPONENT_TERMS):
            return self.final_opponent_answer(year)
        if year and any(term in lowered for term in WIN_TERMS):
            return self.winner_answer(year)
        if any(term in lowered for term in WEB_CONFIRM_TERMS) and self.state.final_match_id:
            return self.web_confirmation_answer()
        if "other match" in lowered and "referee" in lowered:
            return self.referee_other_matches_answer(year)
        if any(term in lowered for term in REFEREE_TERMS):
            return self.referee_answer(year)
        return None

    def winner_answer(self, year: int) -> ToolAnswer | None:
        tournament = self._tournament(year)
        final = self._final_match(year)
        if not tournament:
            return None
        winner = tournament.get("winner", "")
        self.state.year = year
        self.state.winner = winner
        if final:
            self.state.final_match_id = final.get("match_id")
            self.state.final_match_name = final.get("match_name")
        return ToolAnswer(
            tool_name="duckdb_worldcup_workflow",
            answer=f"{winner} won the {year} FIFA World Cup.",
            citations=[{"table": "tournaments", "record_id": tournament.get("tournament_id", f"WC-{year}")}],
            diagnostics={"operation": "lookup_tournament_winner", "year": year, "backend": stats_tool.backend},
            worklog=["Selected DuckDB", "Schema context ready", "Querying tournaments winner"],
        )

    def final_opponent_answer(self, year: int | None) -> ToolAnswer | None:
        final = self._final_match(year)
        if not final:
            return None
        winner = self.state.winner if year == self.state.year and self.state.winner else self._winner_from_final(final)
        teams = [final.get("home_team_name", ""), final.get("away_team_name", "")]
        opponent = teams[1] if teams[0] == winner else teams[0]
        self._remember_final(final, winner)
        return ToolAnswer(
            tool_name="duckdb_worldcup_workflow",
            answer=f"{winner} played against {opponent} in the {self.state.year} FIFA World Cup final.",
            citations=[{"table": "matches", "record_id": final.get("match_id", "")}],
            diagnostics={"operation": "lookup_final_opponent", "year": self.state.year, "backend": stats_tool.backend},
            worklog=["Selected DuckDB", "Using previous tournament context", "Querying final matchup"],
        )

    def score_answer(self, year: int | None) -> ToolAnswer | None:
        final = self._final_match(year)
        if not final:
            return None
        winner = self.state.winner or self._winner_from_final(final)
        self._remember_final(final, winner)
        answer = self._score_sentence(final)
        return ToolAnswer(
            tool_name="duckdb_worldcup_workflow",
            answer=answer,
            citations=[{"table": "matches", "record_id": final.get("match_id", "")}],
            diagnostics={"operation": "lookup_final_score", "year": self.state.year, "backend": stats_tool.backend},
            worklog=["Selected DuckDB", "Using final match context", "Querying score and penalties"],
        )

    def web_confirmation_answer(self) -> ToolAnswer | None:
        final = self._match_by_id(self.state.final_match_id)
        if not final:
            return None
        answer = self._score_sentence(final)
        return ToolAnswer(
            tool_name="duckdb_worldcup_workflow",
            answer=f"{answer} The score is taken from the trusted database record.",
            citations=[{"table": "matches", "record_id": final.get("match_id", "")}],
            diagnostics={"operation": "confirm_from_database", "year": self.state.year, "backend": stats_tool.backend},
            worklog=["Selected DuckDB", "Using final match context", "Confirmed against database record"],
        )

    def referee_answer(self, year: int | None) -> ToolAnswer | None:
        final = self._final_match(year)
        if not final:
            return None
        referee = self._referee_for_match(final.get("match_id", ""))
        if not referee:
            return None
        referee_name = _person_name(referee)
        self._remember_final(final, self.state.winner or self._winner_from_final(final))
        self.state.referee_id = referee.get("referee_id")
        self.state.referee_name = referee_name
        return ToolAnswer(
            tool_name="duckdb_worldcup_workflow",
            answer=(
                f"The referee for the {self.state.year} FIFA World Cup final was "
                f"{referee_name} of {referee.get('country_name')}."
            ),
            citations=[{"table": "referee_appearances", "record_id": referee.get("key_id", "")}],
            diagnostics={"operation": "lookup_final_referee", "year": self.state.year, "backend": stats_tool.backend},
            worklog=["Selected DuckDB", "Using final match context", "Querying referee appearances"],
        )

    def referee_other_matches_answer(self, year: int | None) -> ToolAnswer | None:
        referee_id = self.state.referee_id
        if not referee_id:
            return None
        tournament_year = year or self.state.year
        rows = [
            row
            for row in stats_tool._table_rows("referee_appearances")
            if row.get("referee_id") == referee_id and _row_year(row) == tournament_year and row.get("match_id") != self.state.final_match_id
        ]
        if not rows:
            return ToolAnswer(
                tool_name="duckdb_worldcup_workflow",
                answer=f"No other {tournament_year} World Cup matches were found for {self.state.referee_name}.",
                citations=[{"table": "referee_appearances", "record_id": referee_id}],
                diagnostics={"operation": "lookup_referee_other_matches", "year": tournament_year, "backend": stats_tool.backend},
                worklog=["Selected DuckDB", "Using referee context", "Querying other referee appearances"],
            )
        bits = [f"{row['match_name']} - {row['stage_name']}, {row['match_date']}" for row in rows]
        return ToolAnswer(
            tool_name="duckdb_worldcup_workflow",
            answer=(
                f"Yes. {self.state.referee_name} also officiated {len(rows)} other matches "
                f"in the {tournament_year} FIFA World Cup: " + "; ".join(bits) + "."
            ),
            citations=[{"table": "referee_appearances", "record_id": row.get("key_id", "")} for row in rows],
            diagnostics={"operation": "lookup_referee_other_matches", "year": tournament_year, "backend": stats_tool.backend},
            worklog=["Selected DuckDB", "Using referee context", "Querying other referee appearances"],
        )

    def map_answer(self, year: int) -> ToolAnswer | None:
        matches = [row for row in stats_tool._table_rows("matches") if _row_year(row) == year]
        if not matches:
            return None
        teams = sorted({row["home_team_name"] for row in matches} | {row["away_team_name"] for row in matches})
        edges = [
            {
                "source": row["home_team_name"],
                "target": row["away_team_name"],
                "label": f"{row['score']} - {row['stage_name']}",
                "score": row["score"],
                "stage": row["stage_name"],
                "date": row["match_date"],
                "match_id": row["match_id"],
            }
            for row in matches
        ]
        artifact = {
            "type": "worldcup_match_map",
            "title": f"{year} FIFA World Cup match map",
            "nodes": [{"id": team, "label": team} for team in teams],
            "edges": edges,
        }
        return ToolAnswer(
            tool_name="duckdb_map",
            answer=(
                f"A World Cup map artifact is ready for all {len(teams)} nations that participated "
                f"in the {year} FIFA World Cup. Each country is a node, and each match is an edge labeled with score and stage."
            ),
            citations=[{"table": "matches", "record_id": f"computed-match-map-{year}"}],
            diagnostics={"operation": "build_match_map", "year": year, "nodes": len(teams), "edges": len(edges), "backend": stats_tool.backend},
            worklog=["Selected DuckDB", "Schema context ready", "Writing DuckDB query", "Building map artifact"],
            artifacts=[artifact],
        )

    def _tournament(self, year: int) -> dict[str, str] | None:
        return next((row for row in stats_tool._table_rows("tournaments") if _row_year(row) == year), None)

    def _final_match(self, year: int | None) -> dict[str, str] | None:
        match_id = self.state.final_match_id if year == self.state.year else None
        if match_id:
            match = self._match_by_id(match_id)
            if match:
                return match
        return next(
            (
                row
                for row in stats_tool._table_rows("matches")
                if _row_year(row) == year and row.get("stage_name") == "final"
            ),
            None,
        )

    def _match_by_id(self, match_id: str | None) -> dict[str, str] | None:
        if not match_id:
            return None
        return next((row for row in stats_tool._table_rows("matches") if row.get("match_id") == match_id), None)

    def _referee_for_match(self, match_id: str) -> dict[str, str] | None:
        return next((row for row in stats_tool._table_rows("referee_appearances") if row.get("match_id") == match_id), None)

    def _remember_final(self, final: dict[str, str], winner: str) -> None:
        self.state.year = _row_year(final)
        self.state.winner = winner
        self.state.final_match_id = final.get("match_id")
        self.state.final_match_name = final.get("match_name")

    @staticmethod
    def _winner_from_final(final: dict[str, str]) -> str:
        return final["home_team_name"] if final.get("home_team_win") == "1" else final["away_team_name"]

    @staticmethod
    def _score_sentence(final: dict[str, str]) -> str:
        sentence = f"The {final['tournament_name']} final ended {final['score']}"
        if final.get("extra_time") == "1":
            sentence += " after extra time"
        if final.get("penalty_shootout") == "1":
            winner = WorldCupWorkflowTool._winner_from_final(final)
            sentence += f", with {winner} winning {final.get('score_penalties')} on penalties"
        return sentence + "."


def _first_year(text: str) -> int | None:
    match = re.search(r"\b(19[3-9][0-9]|20[0-9][0-9])\b", text)
    return int(match.group(1)) if match else None


def _has_score_intent(lowered: str) -> bool:
    return bool(re.search(r"\b(final score|score)\b", lowered))


def _row_year(row: dict[str, str]) -> int | None:
    if row.get("year"):
        return int(row["year"])
    match = re.search(r"\b(19[3-9][0-9]|20[0-9][0-9])\b", row.get("tournament_name", ""))
    return int(match.group(1)) if match else None


def _person_name(row: dict[str, str]) -> str:
    return " ".join(part for part in [row.get("given_name", ""), row.get("family_name", "")] if part).strip()


worldcup_workflow_tool = WorldCupWorkflowTool()
