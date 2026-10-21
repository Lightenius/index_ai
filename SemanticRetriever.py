
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


class SemanticRetriever:
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        chunk_size: int = 400,
        overlap: int = 60,
        batch_size: int = 8,
        device: str | None = None,
    ):
        """
        Initialize the semantic retriever.

        Args:
            model_name: Sentence Transformers model name.
            chunk_size: Maximum passage length in tokenizer tokens.
            overlap: Number of overlapping tokens between passages.
            batch_size: Number of passages embedded per batch.
            device: "cpu", "cuda", or None for automatic selection.
        """
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive.")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be >= 0 and < chunk_size.")
        if batch_size < 1:
            raise ValueError("batch_size must be positive.")

        self.model = SentenceTransformer(model_name, device=device)
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.batch_size = batch_size

        # Cached passages and their normalized embeddings.
        self._passages: list[dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None

    def _make_passages(
        self,
        pdf_data: list[dict],
    ) -> list[dict[str, Any]]:
        """Split PDF page text into overlapping passages."""
        tokenizer = self.model.tokenizer
        passages = []
        step = self.chunk_size - self.overlap

        for pdf in pdf_data:
            if not isinstance(pdf, dict):
                raise TypeError("Each PDF must be a dictionary.")

            filename = pdf.get("filename")

            if not isinstance(filename, str) or not filename.strip():
                raise ValueError(
                    "Each PDF dictionary needs a non-empty filename."
                )

            for page_key, text in pdf.items():
                if page_key == "filename":
                    continue

                try:
                    page_number = int(page_key)
                except (ValueError, TypeError):
                    continue

                if not isinstance(text, str) or not text.strip():
                    continue

                token_ids = tokenizer.encode(
                    text.strip(),
                    add_special_tokens=False,
                )

                for start in range(0, len(token_ids), step):
                    chunk_ids = token_ids[
                        start : start + self.chunk_size
                    ]

                    content = tokenizer.decode(
                        chunk_ids,
                        skip_special_tokens=True,
                    ).strip()

                    if content:
                        passages.append({
                            "filename": filename,
                            "page_number": page_number,
                            "content": content,
                        })

                    if start + self.chunk_size >= len(token_ids):
                        break

        return passages

    def index(
        self,
        pdf_data: list[dict],
        show_progress_bar: bool = True,
    ) -> int:
        """
        Prepare the PDF passages and cache their embeddings.

        Call this once after loading your PDFs, or again when the
        PDF collection changes.

        Returns:
            Number of passages indexed.
        """
        passages = self._make_passages(pdf_data)

        if not passages:
            self._passages = []
            self._embeddings = None
            return 0

        embeddings = self.model.encode(
            [p["content"] for p in passages],
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=show_progress_bar,
        )

        self._passages = passages
        self._embeddings = embeddings
        return len(passages)

    def retrieve(
        self,
        prompt: str,
        top_k: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Return the top_k passages most semantically related to prompt.

        Each result contains:
            filename
            page_number
            content
            score

        Higher scores indicate greater cosine similarity.
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string.")

        if top_k < 0:
            raise ValueError("top_k cannot be negative.")

        if top_k == 0 or self._embeddings is None:
            return []

        query_vector = self.model.encode(
            [prompt.strip()],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]

        scores = self._embeddings @ query_vector
        k = min(top_k, len(self._passages))

        # Select the highest-scoring passages and sort them.
        indices = np.argpartition(scores, len(scores) - k)[-k:]
        indices = indices[np.argsort(scores[indices])[::-1]]

        results = []

        for i in indices:
            passage = self._passages[int(i)].copy()
            passage["score"] = float(scores[i])
            results.append(passage)

        return results
