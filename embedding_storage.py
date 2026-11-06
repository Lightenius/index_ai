
import sqlite3
import struct
import time
import numpy as np

from logger import Logger


class EmbeddingStorage:

    def __init__(self, db_path="./data/pdf_data.db"):
        self.db = sqlite3.connect(db_path)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS bs (
                page_number INTEGER PRIMARY KEY,
                vector BLOB NOT NULL
            )
        """)

        self.db.commit()

    def save_embedding(self, page_number, vector):
        """Save or update a page embedding."""

        vector = np.asarray(vector, dtype=np.float32)
        blob = struct.pack(f"{len(vector)}f", *vector)

        self.db.execute("""
            INSERT OR REPLACE INTO bs (page_number, vector)
            VALUES (?, ?)
        """, (page_number, blob))

        self.db.commit()

    def find_embedding(self, vector, n):
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

    def close(self):
        self.db.close()
