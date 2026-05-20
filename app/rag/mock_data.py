from app.schemas.documents import SourceRef, WorldCupDocument


MOCK_DOCUMENTS: list[WorldCupDocument] = [
    WorldCupDocument(
        doc_id="match:2014:final:germany-argentina",
        entity_type="match",
        competition="men",
        tournament_year=2014,
        title="2014 FIFA World Cup Final: Germany vs Argentina",
        text=(
            "Germany won the 2014 men's FIFA World Cup by defeating Argentina 1-0 "
            "in the final at the Maracana in Rio de Janeiro. Mario Gotze scored "
            "the winning goal in extra time."
        ),
        metadata={"stage": "final", "teams": ["Germany", "Argentina"], "score": "1-0"},
        source_refs=[SourceRef(table="matches", record_id="mock-match-2014-final")],
    ),
    WorldCupDocument(
        doc_id="tournament:2018:men",
        entity_type="tournament",
        competition="men",
        tournament_year=2018,
        title="2018 FIFA World Cup Overview",
        text=(
            "The 2018 men's FIFA World Cup was hosted by Russia. France won the "
            "tournament, defeating Croatia in the final."
        ),
        metadata={"host": "Russia", "winner": "France", "runner_up": "Croatia"},
        source_refs=[SourceRef(table="tournaments", record_id="mock-tournament-2018")],
    ),
    WorldCupDocument(
        doc_id="player:2010:top-scorer:thomas-muller",
        entity_type="player",
        competition="men",
        tournament_year=2010,
        title="2010 FIFA World Cup Top Scorer",
        text=(
            "Thomas Muller was one of the top scorers at the 2010 men's FIFA World Cup "
            "and won the Golden Boot on tiebreakers."
        ),
        metadata={"player": "Thomas Muller", "award": "Golden Boot", "goals": 5},
        source_refs=[SourceRef(table="awards", record_id="mock-award-2010-golden-boot")],
    ),
    WorldCupDocument(
        doc_id="team:argentina:2010-2018-summary",
        entity_type="team",
        competition="men",
        tournament_year=2018,
        title="Argentina Performance Summary, 2010 to 2018",
        text=(
            "Argentina reached the quarter-finals in 2010, finished as runner-up in "
            "2014 after losing the final to Germany, and reached the round of 16 in 2018."
        ),
        metadata={"team": "Argentina", "years": [2010, 2014, 2018]},
        source_refs=[
            SourceRef(table="standings", record_id="mock-argentina-2010"),
            SourceRef(table="standings", record_id="mock-argentina-2014"),
            SourceRef(table="standings", record_id="mock-argentina-2018"),
        ],
    ),
    WorldCupDocument(
        doc_id="team:brazil:semifinals:since-1990",
        entity_type="team",
        competition="men",
        tournament_year=2014,
        title="Brazil Semi-Final Appearances Since 1990",
        text=(
            "Brazil reached the semi-finals of the men's FIFA World Cup in 1994, "
            "1998, 2002, and 2014."
        ),
        metadata={"team": "Brazil", "semifinal_years": [1994, 1998, 2002, 2014]},
        source_refs=[SourceRef(table="standings", record_id="mock-brazil-semifinals")],
    ),
]

