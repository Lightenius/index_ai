
import sqlite3
import struct
import time
from typing import List

import numpy as np
import numpy.typing as npt

from logger import Logger


class EmbeddingStorage:

    def __init__(self, db_path: str = "./data/pdf_data.db") -> None:
        self.db: sqlite3.Connection = sqlite3.connect(db_path)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS bs (
                page_number INTEGER PRIMARY KEY,
                vector BLOB NOT NULL
            )
        """)

        

        self.db.commit()

    def save_embedding(self, page_number: int, vector: npt.ArrayLike) -> None:
        """Save or update a page embedding."""

        vector = np.asarray(vector, dtype=np.float32)
        blob = struct.pack(f"{len(vector)}f", *vector)

        self.db.execute("""
            INSERT OR REPLACE INTO bs (page_number, vector)
            VALUES (?, ?)
        """, (page_number, blob))

        self.db.commit()

    def find_embedding(self, vector: npt.ArrayLike, n: int) -> List[int]:
        """Return page numbers of the n closest embeddings."""
        Logger.system(f"Finding {n} closest embeddings for the given vector.")
        start = time.perf_counter()

        vector = np.asarray(vector, dtype=np.float32)
        norm = np.linalg.norm(vector)

        if norm == 0:
            raise ValueError("Query vector cannot be zero.")

        rows = self.db.execute("""
            SELECT page_number, vector FROM bs
        """).fetchall()

        results = []

        for page_number, blob in rows:
            stored = np.frombuffer(blob, dtype=np.float32)

            if stored.shape != vector.shape:
                continue

            stored_norm = np.linalg.norm(stored)

            if stored_norm == 0:
                continue

            similarity = np.dot(vector, stored) / (
                norm * stored_norm
            )

            results.append((page_number, similarity))

        results.sort(key=lambda x: x[1], reverse=True)

        matches = [page for page, _ in results[:n]]

        elapsed = time.perf_counter() - start
        Logger.perf(
            f"Time it took to find {n} closest embeddings: {elapsed:.4f}s"
        )

        return matches

    def check_embedding_exists(self, page_number: int) -> bool:
        """Check if an embedding for the given page number exists."""
        cursor = self.db.execute("""
            SELECT 1 FROM bs WHERE page_number = ?
        """, (page_number,))
        return cursor.fetchone() is not None

    def close(self) -> None:
        self.db.close()
