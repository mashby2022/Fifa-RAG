from pathlib import Path

from app.rag.tools.stats import DuckDBStatsTool


def test_stats_tool_counts_matches_from_csv_fallback(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "matches.csv").write_text(
        "match_id,tournament_name\n"
        "m1,2014 FIFA Men's World Cup\n"
        "m2,2014 FIFA Men's World Cup\n"
        "m3,2018 FIFA Men's World Cup\n",
        encoding="utf-8",
    )

    tool = DuckDBStatsTool(db_path=str(tmp_path / "missing.duckdb"), raw_data_dir=str(raw))
    answer = tool.maybe_answer("How many matches were in the 2014 World Cup?")

    assert answer is not None
    assert "2 matches in 2014" in answer.answer
    assert answer.diagnostics["backend"] == "csv-fallback"


def test_stats_tool_identifies_top_scorer_from_csv_fallback(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "goals.csv").write_text(
        "goal_id,tournament_name,given_name,family_name,team_name,own_goal\n"
        "g1,2010 FIFA Men's World Cup,Thomas,Müller,Germany,0\n"
        "g2,2010 FIFA Men's World Cup,Thomas,Müller,Germany,0\n"
        "g3,2010 FIFA Men's World Cup,David,Villa,Spain,0\n",
        encoding="utf-8",
    )

    tool = DuckDBStatsTool(db_path=str(tmp_path / "missing.duckdb"), raw_data_dir=str(raw))
    answer = tool.maybe_answer("Who was the top scorer in 2010?")

    assert answer is not None
    assert "Thomas Müller (Germany) with 2 goals" in answer.answer


def test_stats_tool_answers_team_best_finish_from_qualified_teams(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "qualified_teams.csv").write_text(
        "key_id,tournament_id,tournament_name,team_id,team_name,team_code,count_matches,performance\n"
        "267,WC-1994,1994 FIFA Men's World Cup,T-50,Nigeria,NGA,4,round of 16\n"
        "332,WC-1999,1999 FIFA Women's World Cup,T-50,Nigeria,NGA,4,quarter-final\n"
        "506,WC-2014,2014 FIFA Men's World Cup,T-50,Nigeria,NGA,4,round of 16\n",
        encoding="utf-8",
    )

    tool = DuckDBStatsTool(db_path=str(tmp_path / "missing.duckdb"), raw_data_dir=str(raw))
    answer = tool.maybe_answer("which world cup did Nigeria place the highest")
    demonym_answer = tool.maybe_answer("which world cup did the nigerian team place the highest")

    assert answer is not None
    assert demonym_answer is not None
    assert "round of 16" in answer.answer
    assert "round of 16" in demonym_answer.answer
    assert "1994 FIFA Men's World Cup" in answer.answer
    assert "1999 FIFA Women's World Cup" not in answer.answer
    assert answer.diagnostics["operation"] == "team_best_finish"

    overall = tool.maybe_answer("overall, which world cup did Nigeria place the highest across all world cups")

    assert overall is not None
    assert "1999 FIFA Women's World Cup" in overall.answer
    assert "men's tournament" in overall.answer
