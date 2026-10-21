import os
import pickle
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
        db_path: str = "semantic_db.pkl",
    ):
        """
        Initialize the semantic retriever.

        Args:
            model_name: Sentence Transformers model name.
            chunk_size: Maximum passage length in tokenizer tokens.
            overlap: Number of overlapping tokens between passages.
            batch_size: Number of passages embedded per batch.
            device: "cpu", "cuda", or None for automatic selection.
            db_path: Path to save and load the indexed data.
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
        self.db_path = db_path

        # Cached passages and their normalized embeddings.
        self._passages: list[dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None

    def _load_db(self, target_filenames: set[str]) -> tuple[list[dict], np.ndarray | None]:
        """
        Loads the database from disk and filters out files that are no longer present.
        """
        if not os.path.exists(self.db_path):
            return [], None
        
        try:
            with open(self.db_path, "rb") as f:
                data = pickle.load(f)
                db_passages = data.get("passages", [])
                db_embeddings = data.get("embeddings", None)
        except Exception as e:
            print(f"Warning: Failed to load semantic DB ({e}). Starting fresh.")
            return [], None

        # Filter out passages for files that were removed
        kept_indices = [
            i for i, p in enumerate(db_passages) 
            if p.get("filename") in target_filenames
        ]
        
        kept_passages = [db_passages[i] for i in kept_indices]
        
        if db_embeddings is not None and len(kept_indices) > 0:
            kept_embeddings = db_embeddings[kept_indices]
        else:
            kept_embeddings = None
            
        return kept_passages, kept_embeddings

    def _save_db(self) -> None:
        """
        Overwrites the database on disk with the current passages and embeddings.
        """
        with open(self.db_path, "wb") as f:
            pickle.dump({
                "passages": self._passages,
                "embeddings": self._embeddings
            }, f)

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
        target_filenames = set()
        for pdf in pdf_data:
            fname = pdf.get("filename")
            if isinstance(fname, str) and fname.strip():
                target_filenames.add(fname)

        # Load existing data, omitting anything no longer in target_filenames
        kept_passages, kept_embeddings = self._load_db(target_filenames)

        # Identify files that need to be processed (not present in the loaded cache)
        existing_filenames = set(p.get("filename") for p in kept_passages)
        new_pdfs = [
            pdf for pdf in pdf_data 
            if pdf.get("filename") in target_filenames and pdf.get("filename") not in existing_filenames
        ]

        # Generate passages and embeddings for new files
        new_passages = self._make_passages(new_pdfs)
        new_embeddings = None

        if new_passages:
            new_embeddings = self.model.encode(
                [p["content"] for p in new_passages],
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=show_progress_bar,
            )

        # Merge old and new data
        self._passages = kept_passages + new_passages

        if kept_embeddings is not None and new_embeddings is not None:
            self._embeddings = np.vstack([kept_embeddings, new_embeddings])
        elif kept_embeddings is not None:
            self._embeddings = kept_embeddings
        elif new_embeddings is not None:
            self._embeddings = new_embeddings
        else:
            self._embeddings = None

        # Save back to disk
        self._save_db()

        return len(self._passages)

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