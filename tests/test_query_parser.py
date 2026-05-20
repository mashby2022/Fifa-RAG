from app.rag.query_parser import parse_query


def test_extracts_single_year_filter() -> None:
    parsed = parse_query("Who hosted the 2018 World Cup?")
    assert parsed.years == [2018]
    assert parsed.filters["tournament_year"] == 2018


def test_detects_invalid_mens_year() -> None:
    parsed = parse_query("Who won the World Cup in 2000?")
    assert parsed.invalid_reason == "invalid_tournament_year"


def test_detects_womens_competition() -> None:
    parsed = parse_query("Who won the women's World Cup in 2019?")
    assert parsed.competition == "women"
    assert parsed.invalid_reason is None

