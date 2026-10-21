"""Multilingual semantic retrieval for PDF text parsed page by page."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass(frozen=True)
class Passage:
    filename: str
    page_number: int
    content: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "page_number": self.page_number,
            "content": self.content,
        }


def _page_key(key: Any) -> int | None:
    """Convert a page key such as 1 or '1' to an integer; ignore filename."""
    if isinstance(key, bool):
        return None
    if isinstance(key, int):
        return key
    if isinstance(key, str):
        stripped = key.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _iter_pages(pdf_data: Sequence[Mapping[Any, Any]]) -> Iterable[tuple[str, int, str]]:
    """Read dictionaries shaped like {'filename': 'x.pdf', 1: '...', 2: '...'}."""
    if not isinstance(pdf_data, (list, tuple)):
        raise TypeError("pdf_data must be a list of dictionaries.")

    for file_index, pdf in enumerate(pdf_data):
        if not isinstance(pdf, Mapping):
            raise TypeError(f"pdf_data[{file_index}] must be a dictionary.")

        filename = pdf.get("filename")
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError(
                f"pdf_data[{file_index}] must contain a non-empty 'filename' string."
            )

        pages = []
        for key, value in pdf.items():
            number = _page_key(key)
            if number is None:
                continue
            if not isinstance(value, str):
                raise TypeError(
                    f"Page {key!r} in {filename!r} must have string content."
                )
            if value.strip():
                pages.append((number, value.strip()))

        for page_number, content in sorted(pages, key=lambda item: item[0]):
            yield filename, page_number, content


class SemanticRetriever:
    """
    Semantic retrieval using BAAI/bge-m3.

    The model is loaded once per instance. Call retrieve() repeatedly for
    different prompts; document embeddings are currently rebuilt per call.
    Persistent embedding caching is intentionally not included yet.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        chunk_tokens: int = 400,
        overlap_tokens: int = 60,
        batch_size: int = 8,
        device: str | None = None,
    ) -> None:
        if chunk_tokens < 1:
            raise ValueError("chunk_tokens must be >= 1.")
        if overlap_tokens < 0 or overlap_tokens >= chunk_tokens:
            raise ValueError("overlap_tokens must be >= 0 and smaller than chunk_tokens.")
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1.")

        self.model_name = model_name
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name, device=device)

    def _chunk_page(self, filename: str, page_number: int, text: str) -> list[Passage]:
        tokenizer = self.model.tokenizer
        token_ids = tokenizer.encode(text, add_special_tokens=False)

        if not token_ids:
            return []

        step = self.chunk_tokens - self.overlap_tokens
        passages: list[Passage] = []

        for start in range(0, len(token_ids), step):
            part_ids = token_ids[start : start + self.chunk_tokens]
            content = tokenizer.decode(
                part_ids, skip_special_tokens=True
            ).strip()

            if content:
                passages.append(
                    Passage(
                        filename=filename,
                        page_number=page_number,
                        content=content,
                    )
                )

            if start + self.chunk_tokens >= len(token_ids):
                break

        return passages

    def _make_passages(
        self, pdf_data: Sequence[Mapping[Any, Any]]
    ) -> list[Passage]:
        passages: list[Passage] = []
        for filename, page_number, content in _iter_pages(pdf_data):
            passages.extend(self._chunk_page(filename, page_number, content))
        return passages

    def retrieve(
        self,
        pdf_data: Sequence[Mapping[Any, Any]],
        prompt: str,
        top_k: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Return up to top_k passages, ranked by cosine similarity.

        Output entries have exactly these keys:
          - filename: original PDF filename
          - page_number: original PDF page number
          - content: retrieved passage text
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string.")
        if top_k < 0:
            raise ValueError("top_k must be >= 0.")
        if top_k == 0:
            return []

        passages = self._make_passages(pdf_data)
        if not passages:
            return []

        texts = [passage.content for passage in passages]

        # BGE-M3 supports multilingual dense embeddings. Normalize vectors so
        # their dot product is cosine similarity.
        document_vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype(np.float32, copy=False)

        query_vector = self.model.encode(
            [prompt.strip()],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0].astype(np.float32, copy=False)

        scores = document_vectors @ query_vector
        count = min(top_k, len(passages))

        # argpartition avoids sorting every candidate when only top_k are needed.
        selected = np.argpartition(scores, len(scores) - count)[-count:]
        selected = selected[np.argsort(scores[selected])[::-1]]

        return [passages[int(i)].as_dict() for i in selected]


def retrieve_passages(
    pdf_data: Sequence[Mapping[Any, Any]],
    prompt: str,
    *,
    top_k: int = 50,
    retriever: SemanticRetriever | None = None,
) -> list[dict[str, Any]]:
    """
    Convenience function for one-off retrieval.

    For repeated calls, create SemanticRetriever once and call its retrieve()
    method, or pass that instance as `retriever` to avoid reloading the model.
    """
    engine = retriever or SemanticRetriever()
    return engine.retrieve(pdf_data, prompt, top_k=top_k)
