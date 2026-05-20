import csv
import io
from pathlib import Path
from urllib.request import urlopen


FJELSTUL_BASE = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv"
OPENFOOTBALL_BASE = "https://raw.githubusercontent.com/openfootball/worldcup/master"

FJELSTUL_FILES = {
    "tournaments": f"{FJELSTUL_BASE}/tournaments.csv",
    "matches": f"{FJELSTUL_BASE}/matches.csv",
    "team_appearances": f"{FJELSTUL_BASE}/team_appearances.csv",
    "tournament_standings": f"{FJELSTUL_BASE}/tournament_standings.csv",
    "award_winners": f"{FJELSTUL_BASE}/award_winners.csv",
    "players": f"{FJELSTUL_BASE}/players.csv",
    "player_appearances": f"{FJELSTUL_BASE}/player_appearances.csv",
    "goals": f"{FJELSTUL_BASE}/goals.csv",
    "squads": f"{FJELSTUL_BASE}/squads.csv",
    "qualified_teams": f"{FJELSTUL_BASE}/qualified_teams.csv",
}

OPENFOOTBALL_FILES = {
    "openfootball_2026_cup": f"{OPENFOOTBALL_BASE}/2026--usa/cup.txt",
    "openfootball_2026_finals": f"{OPENFOOTBALL_BASE}/2026--usa/cup_finals.txt",
    "openfootball_2022_cup": f"{OPENFOOTBALL_BASE}/2022--qatar/cup.txt",
}

CODEBOOK_TABLES = {
    "codebook_datasets": Path("raw/codebook/datasets.csv"),
    "codebook_variables": Path("raw/codebook/variables.csv"),
}


def load_fjelstul_tables(local_data_dir: str) -> dict[str, list[dict[str, str]]]:
    """Load all source tables, preferring Tom's local parquet/csv data over GitHub."""
    table_names = [*FJELSTUL_FILES, *CODEBOOK_TABLES]
    return {name: load_table(name, local_data_dir) for name in table_names}


def load_table(name: str, local_data_dir: str) -> list[dict[str, str]]:
    data_dir = Path(local_data_dir)
    if name in CODEBOOK_TABLES:
        local_csv = data_dir / CODEBOOK_TABLES[name]
        return read_csv_path(local_csv) if local_csv.exists() else []

    local_parquet = data_dir / "processed" / f"{name}.parquet"
    if local_parquet.exists():
        parquet_rows = read_parquet_path(local_parquet)
        if parquet_rows:
            return parquet_rows

    local_csv = data_dir / "raw" / f"{name}.csv"
    if local_csv.exists():
        return read_csv_path(local_csv)

    url = FJELSTUL_FILES.get(name)
    return read_csv_url(url) if url else []


def read_csv_path(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_parquet_path(path: Path) -> list[dict[str, str]]:
    try:
        import pandas as pd
    except ImportError:
        return []

    frame = pd.read_parquet(path)
    frame = frame.fillna("")
    return [
        {str(key): stringify_value(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def stringify_value(value: object) -> str:
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def read_csv_url(url: str) -> list[dict[str, str]]:
    with urlopen(url, timeout=30) as response:
        text = response.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def read_text_url(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")
