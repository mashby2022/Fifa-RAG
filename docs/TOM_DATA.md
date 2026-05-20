# Tom Data Bundle

Tom's bundle is now the preferred local ingestion source for Phase 1 and Phase 2.

## Files

Expected local layout:

```text
data/
  raw/
    tournaments.csv
    matches.csv
    team_appearances.csv
    player_appearances.csv
    players.csv
    goals.csv
    squads.csv
    award_winners.csv
    qualified_teams.csv
    codebook/
      datasets.csv
      variables.csv
  processed/
    tournaments.parquet
    matches.parquet
    ...
  indexes/
    worldcup_milvus_lite.db/
```

The raw and processed folders are ignored by Git so the repo stays light.

## Ingestion Priority

The document builder now loads tables in this order:

```text
1. data/processed/{table}.parquet, when readable
2. data/raw/{table}.csv
3. GitHub fallback from jfjelstul/worldcup
4. mock fallback only if no generated corpus exists
```

Codebook documents are loaded from:

```text
data/raw/codebook/datasets.csv
data/raw/codebook/variables.csv
```

## Generated Document Families

Phase 1 keeps the app API unchanged while swapping the ingestion source.

Phase 2 adds richer searchable document families:

- `tournament`: tournament capsules with host, dates, winner, team count.
- `match`: match narratives enriched with goal scorers.
- `team`: team tournament runs and full team performance timelines.
- `player`: player profiles from players, squads, appearances, goals, and awards.
- `goal`: scorer stories and tournament goal-leader summaries.
- `award`: award winner cards.
- `schema`: codebook dataset and variable descriptions.

## Local Commands

Extract Tom's files:

```bash
unzip -qo ~/Downloads/raw.zip -d data
unzip -qo ~/Downloads/processed.zip -d data
unzip -qo ~/Downloads/indexes.zip -d data
```

Generate RAG documents:

```bash
python scripts/ingest_dataset.py
```

Expected local result with Tom's data:

```text
Wrote 6611 generated documents to data/generated_docs/worldcup_docs.jsonl
```

Check API health:

```bash
python -c "from fastapi.testclient import TestClient; from app.main import app; print(TestClient(app).get('/api/health').json())"
```

