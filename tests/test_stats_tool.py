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
