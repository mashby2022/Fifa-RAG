import re
from dataclasses import dataclass, field


YEAR_RE = re.compile(r"\b(19[3-9][0-9]|20[0-9][0-9])\b")
KNOWN_CLUBS = {"fc barcelona", "barcelona", "real madrid", "manchester city", "psg"}
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


def parse_query(message: str) -> ParsedQuery:
    lowered = message.lower()
    years = [int(year) for year in YEAR_RE.findall(lowered)]
    competition = "women" if "women" in lowered or "women's" in lowered else "men"
    filters: dict[str, object] = {"competition": competition}
    if len(years) == 1:
        filters["tournament_year"] = years[0]

    invalid_reason = None
    if any(club in lowered for club in KNOWN_CLUBS):
        invalid_reason = "club_team"
    elif years and competition == "men" and all(year not in VALID_MEN_YEARS for year in years):
        invalid_reason = "invalid_tournament_year"

    return ParsedQuery(
        text=message,
        years=years,
        competition=competition,
        filters=filters,
        invalid_reason=invalid_reason,
    )
