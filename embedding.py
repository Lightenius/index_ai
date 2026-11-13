import sys
import threading
import time
from pathlib import Path
from typing import List

import ollama

import axxonParser
from embedding_storage import EmbeddingStorage
from logger import Logger


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_PDF = PROJECT_DIR / "data" / "raw_manual.pdf"
DATABASE_PATH = PROJECT_DIR / "data" / "pdf_data.db"
EM = "qwen3-embedding:8b"
EMBEDDING_BATCH_SIZE = 16
_INDEX_LOCK = threading.Lock()


def embed_texts(texts: list[str], model: str = EM) -> list[list[float]]:
    """Embed a batch of texts with the configured Ollama model."""
    if not texts:
        return []
    try:
        response = ollama.embed(model=model, input=texts)
    except Exception as error:
        Logger.error(f"Failed to embed text: {error}")
        raise RuntimeError(f"Embedding failed using model {model}.") from error

    if len(response.embeddings) != len(texts):
        raise RuntimeError(f"Embedding model {model} returned an incomplete batch.")
    return response.embeddings


def embed_text(text: str, model: str = EM) -> list[float]:
    """Embed one text with the configured Ollama embedding model."""
    return embed_texts([text], model)[0]


def embed_pdf(
    pdf_path: str | Path,
    embedding_model: str = EM,
    db_path: str | Path = DATABASE_PATH,
    top_k: int = 5,
    overwrite: bool = False,
) -> bool:
    del top_k
    Logger.system(f"Starting embedding process for PDF: {pdf_path}")
    performance_start = time.perf_counter()
    pages = axxonParser.get_pages(str(pdf_path))
    if not pages:
        raise RuntimeError(f"No pages extracted from PDF: {pdf_path}")

    missing_pages = []
    with EmbeddingStorage(db_path=str(db_path)) as store:
        for page in pages:
            page_number = int(page["page_number"])
            if not overwrite and store.check_embedding_exists(page_number):
                continue
            missing_pages.append(page)

        for offset in range(0, len(missing_pages), EMBEDDING_BATCH_SIZE):
            batch = missing_pages[offset:offset + EMBEDDING_BATCH_SIZE]
            vectors = embed_texts(
                [str(page["content"]) for page in batch],
                embedding_model,
            )
            for page, vector in zip(batch, vectors):
                store.save_embedding(int(page["page_number"]), vector)

    elapsed = time.perf_counter() - performance_start
    Logger.info(
        f"New pages embedded: {len(missing_pages)}; total pages: {len(pages)}"
    )
    Logger.perf(f"Embedding process completed in {elapsed:.3f} seconds.")
    return True


def query(text: str, n: int = 10) -> List[int]:
    if not text.strip():
        return []

    with _INDEX_LOCK:
        pages = axxonParser.get_pages(str(SOURCE_PDF))
        if not pages:
            raise RuntimeError(f"No pages extracted from PDF: {SOURCE_PDF}")

        with EmbeddingStorage(db_path=str(DATABASE_PATH)) as store:
            missing_pages = [
                page for page in pages
                if not store.check_embedding_exists(int(page["page_number"]))
            ]
            for offset in range(0, len(missing_pages), EMBEDDING_BATCH_SIZE):
                batch = missing_pages[offset:offset + EMBEDDING_BATCH_SIZE]
                vectors = embed_texts(
                    [str(page["content"]) for page in batch]
                )
                for page, vector in zip(batch, vectors):
                    store.save_embedding(int(page["page_number"]), vector)

            query_vector = embed_text(text)
            return store.find_embedding(vector=query_vector, n=n)


def run_embedding() -> None:
    Logger.system("Starting embedding module.")
    start_time = time.perf_counter()
    embed_pdf(SOURCE_PDF, db_path=DATABASE_PATH, overwrite=True)
    Logger.perf(
        f"Embedding run completed in {time.perf_counter() - start_time:.3f} seconds."
    )


if __name__ == "__main__":
    Logger.system("This is a test run of the embedding module.")
    try:
        embed_pdf(SOURCE_PDF, db_path=DATABASE_PATH)
        query_text = "yüz tanıma sisteminin çalışmama sebepleri neler olabilir"
        Logger.info(f"Query results for '{query_text}': {query(query_text, n=10)}")
    except Exception as error:
        Logger.critical(f"Embedding process failed: {error}", exc_info=True)
        sys.exit(1)
