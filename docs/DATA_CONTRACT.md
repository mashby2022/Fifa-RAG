# Partner Data Contract

The RAG shell expects trusted tabular data to be normalized into generated documents with source lineage.

## Required Properties

Every source row should have:

- Stable primary key.
- Table name.
- Tournament year.
- Competition: `men` or `women`.
- Human-readable labels.
- Foreign keys needed for joins.

## Target Tables

- `tournaments`
- `matches`
- `teams`
- `players`
- `squads`
- `goals`
- `standings`
- `awards`

## Generated Document Shape

```json
{
  "doc_id": "match:2014:final:germany-argentina",
  "entity_type": "match",
  "competition": "men",
  "tournament_year": 2014,
  "title": "2014 FIFA World Cup Final: Germany vs Argentina",
  "text": "Germany defeated Argentina 1-0...",
  "metadata": {
    "stage": "final",
    "teams": ["Germany", "Argentina"]
  },
  "source_refs": [
    {
      "table": "matches",
      "record_id": "..."
    }
  ]
}
```

