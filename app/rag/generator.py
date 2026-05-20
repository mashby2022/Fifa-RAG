from app.rag.query_parser import ParsedQuery
from app.schemas.api import ChatResponse, Citation
from app.schemas.documents import RetrievedDocument


def generate_answer(parsed: ParsedQuery, retrieved: list[RetrievedDocument]) -> ChatResponse:
    if parsed.invalid_reason == "club_team":
        return ChatResponse(
            answer=(
                "FC Barcelona is a club team, not a national team in the FIFA World Cup. "
                "This dataset is organized around national-team World Cup tournaments."
            ),
            status="invalid_premise",
            confidence="high",
            citations=[],
            retrieved_context=[],
            filters=parsed.filters,
        )

    if parsed.invalid_reason == "invalid_tournament_year":
        years = ", ".join(str(year) for year in parsed.years)
        return ChatResponse(
            answer=(
                f"There was no men's FIFA World Cup tournament in {years}. "
                "The men's tournament is generally held every four years, so that year does not correspond to a tournament in the dataset."
            ),
            status="invalid_premise",
            confidence="high",
            citations=[],
            retrieved_context=[],
            filters=parsed.filters,
        )

    if not retrieved:
        return ChatResponse(
            answer="I do not have enough grounded World Cup data to answer that from the current corpus.",
            status="no_answer",
            confidence="low",
            citations=[],
            retrieved_context=[],
            filters=parsed.filters,
        )

    used = retrieved[:1]
    for item in used:
        item.used = True

    answer = _compose_extractive_answer(used)
    citations = [
        Citation(doc_id=item.doc.doc_id, title=item.doc.title, source_refs=item.doc.source_refs)
        for item in used
    ]
    return ChatResponse(
        answer=answer,
        status="grounded",
        confidence="medium",
        citations=citations,
        retrieved_context=retrieved,
        filters=parsed.filters,
    )


def _compose_extractive_answer(retrieved: list[RetrievedDocument]) -> str:
    if len(retrieved) == 1:
        return retrieved[0].doc.text
    facts = " ".join(item.doc.text for item in retrieved)
    return facts
