import re


def competition(row: dict[str, str]) -> str:
    return "women" if "Women's" in row.get("tournament_name", "") else "men"


def year(row: dict[str, str]) -> int:
    match = re.search(r"\b(19[0-9]{2}|20[0-9]{2})\b", row.get("tournament_name", ""))
    return int(row.get("year") or (match.group(1) if match else "0"))


def player_name(row: dict[str, str]) -> str:
    given = row.get("given_name", "")
    family = row.get("family_name", "")
    if given == "not applicable":
        given = ""
    return " ".join(part for part in [given, family] if part).strip()


def position_label(position: int) -> str:
    if position == 1:
        return "as champion"
    if position == 2:
        return "as runner-up"
    if position == 3:
        return "in third place"
    if position == 4:
        return "in fourth place"
    return f"in position {position}"


def stage_reached(stages: object) -> str:
    stage_order = {
        "group stage": 1,
        "first group stage": 1,
        "second group stage": 2,
        "round of 16": 3,
        "quarter-finals": 4,
        "semi-finals": 5,
        "third-place match": 6,
        "final": 7,
    }
    best_stage = "group stage"
    best_score = 0
    for stage in stages:
        score = stage_order.get(str(stage), 0)
        if score > best_score:
            best_stage = str(stage)
            best_score = score
    return best_stage


def chunk_football_txt(text: str, max_chars: int = 1800) -> list[str]:
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


def empty_player_stat() -> dict[str, object]:
    return {
        "appearances": 0,
        "starts": 0,
        "substitutes": 0,
        "goals": 0,
        "penalty_goals": 0,
        "teams": set(),
        "tournaments": set(),
        "positions": set(),
        "awards": [],
        "source_refs": [],
    }


def merge_player_stats(*stats: dict[str, object] | None) -> dict[str, object]:
    merged = empty_player_stat()
    for stat in stats:
        if not stat:
            continue
        for key in ["appearances", "starts", "substitutes", "goals", "penalty_goals"]:
            merged[key] = int(merged[key]) + int(stat[key])
        for key in ["teams", "tournaments", "positions"]:
            merged[key].update(stat[key])
        merged["awards"].extend(stat["awards"])
        merged["source_refs"].extend(stat["source_refs"])
    return merged


def is_notable_player(
    appearances: int,
    goals: int,
    awards: list[str],
    tournaments: list[int],
    listed_tournaments: str | None,
) -> bool:
    listed_count = len([item for item in (listed_tournaments or "").split(",") if item.strip()])
    return bool(awards) or goals > 0 or appearances >= 8 or len(tournaments) >= 2 or listed_count >= 2
