import json
import re

import llm_manager
from logger import Logger


RERANKER_MODEL = "qwen3:4b"


def _parse_results(response: str, candidates: list[dict]) -> list[dict]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", response.strip())
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Reranker returned invalid JSON: {error}") from error

    if isinstance(parsed, dict):
        parsed = parsed.get("results")
    if not isinstance(parsed, list):
        raise RuntimeError("Reranker response must contain a results list.")

    allowed_pages = {int(page["page_number"]): page for page in candidates}
    ranked = []
    seen_pages = set()
    for result in parsed:
        if not isinstance(result, dict):
            continue
        try:
            page_number = int(result["page_number"])
            relevance = float(result["relevance"])
        except (KeyError, TypeError, ValueError):
            continue
        if (
            page_number not in allowed_pages
            or page_number in seen_pages
            or not 0 <= relevance <= 100
        ):
            continue
        seen_pages.add(page_number)
        ranked.append({
            **allowed_pages[page_number],
            "relevance": relevance,
        })

    ranked.sort(key=lambda page: page["relevance"], reverse=True)
    return ranked


async def rerank(query: str, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    compact_candidates = [
        {
            "page_number": int(page["page_number"]),
            "content": page["content"],
        }
        for page in candidates
    ]
    prompt = f"""Rank the source pages by how directly they answer the user's question.
Return only JSON in this format: {{"results":[{{"page_number":1,"relevance":92}}]}}.
Include only supplied page numbers. Relevance is an integer from 0 to 100 and measures answer relevance, not keyword overlap. Do not invent page numbers.

Question: {query}
Candidate pages: {json.dumps(compact_candidates, ensure_ascii=False)}"""
    response = await llm_manager.ask_direct_llm_async(
        prompt,
        llm_name=RERANKER_MODEL,
        benchmark=False,
    )
    ranked = _parse_results(response, compact_candidates)
    Logger.info(
        f"Reranked {len(candidates)} source pages; "
        f"{sum(page['relevance'] >= 85 for page in ranked)} meet the relevance threshold."
    )
    return ranked
