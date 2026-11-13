import math
import re
import unicodedata
from collections import Counter


TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)
STOP_WORDS = {
    "acaba", "ama", "bu", "da", "daha", "de", "diye", "en", "gibi",
    "icin", "ile", "mi", "mu", "ne", "neden", "nasil", "nicin",
    "ve", "veya", "ya", "yok", "the", "a", "an", "and", "are",
    "for", "is", "of", "or", "to", "what", "why",
}


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    ).replace("ı", "i")
    return [
        token for token in TOKEN_PATTERN.findall(normalized)
        if token not in STOP_WORDS and len(token) > 1
    ]


def rank_pages(query: str, pages: list[dict], n: int = 10) -> list[int]:
    """Rank page numbers using weighted Turkish/English term overlap."""
    query_tokens = _tokens(query)
    if not query_tokens or n <= 0:
        return []

    page_tokens = [
        _tokens(str(page.get("content", "")))
        for page in pages
    ]
    document_frequencies = Counter(
        token
        for tokens in page_tokens
        for token in set(tokens)
    )
    query_terms = set(query_tokens)
    query_phrase = " ".join(query_tokens)
    ranked = []

    for page, tokens in zip(pages, page_tokens):
        counts = Counter(tokens)
        score = 0.0
        for token in query_terms:
            frequency = counts[token]
            if frequency:
                inverse_frequency = math.log(
                    1 + (len(pages) + 1) / (document_frequencies[token] + 1)
                )
                score += inverse_frequency * (1 + math.log(frequency))

        page_phrase = " ".join(tokens)
        if query_phrase and query_phrase in page_phrase:
            score += 2.0

        if score > 0:
            ranked.append((int(page["page_number"]), score))

    ranked.sort(key=lambda result: result[1], reverse=True)
    return [page_number for page_number, _ in ranked[:n]]
