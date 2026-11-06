# Anlam eşleşmesine göre pasajlar puanlanacak, en yüksek puanlı X pasaj döndürülecek.

import sys
import time

import ollama

from logger import Logger
import axxonParser

from typing import List, Dict

from embedding_storage import EmbeddingStorage

# EM = "bge-m3"  # Embedding model to use, can be changed as needed
EM = "qwen3-embedding:8b"  # Embedding model to use, can be changed as needed

def embed_text(text, model=EM):
    """Embed the given text using the specified model."""
    try:
        response = ollama.embed(model=model, input=text)
        vector = response.embeddings[0]
        return vector
    except Exception as e:
        Logger.error(f"Failed to embed text: {e}")
        return None


def embed_pdf(pdf_path, embedding_model = EM, db_path = "data/pdf_data.db", top_k=5, overwrite: bool=False):
    Logger.system(f"Starting embedding process for PDF: {pdf_path}")
    performance_start = time.perf_counter()


    es = EmbeddingStorage(db_path=db_path)

    # Extract pages from the PDF
    pages = axxonParser.get_pages(pdf_path)

    if not pages:
        Logger.error(f"No pages extracted from PDF: {pdf_path}. Aborting embedding process.")
        return False

    # Embed each page and store in the database
    new_pages = 0
    for page in pages:
        if not overwrite and es.check_embedding_exists(page["page_number"]):
            Logger.info(f"Embedding for page {page['page_number']} already exists. Skipping.")
            continue
        new_pages += 1
        page_number = page["page_number"]
        content = page["content"]
        vector = embed_text(content, embedding_model)
        if vector is None:
            Logger.error(f"Embedding failed for page {page_number}. Skipping this page.")
            continue
        es.save_embedding(page_number, vector)

    performance_end = time.perf_counter()
    Logger.info(f"Total new pages embedded: {new_pages}")
    Logger.info(f"Total pages processed: {len(pages)}")
    Logger.perf(f"Embedding process for PDF: {pdf_path} completed in {performance_end - performance_start:.3f} seconds.")
    return True


def query(text: str, n: int = 10) -> List[int]:
    embeded_query = embed_text(text)
    es = EmbeddingStorage()

    results = es.find_embedding(vector=embeded_query, n=n)
    return results

def run_embedding():
    Logger.system("Starting embedding module.")
    start_time = time.perf_counter()

    if not embed_pdf("data/raw_manual.pdf", embedding_model=EM, db_path="data/pdf_data.db", overwrite=True):
        Logger.critical("Embedding process failed.")
        sys.exit(1)

    end_time = time.perf_counter()
    Logger.perf(f"Embedding run completed in {end_time - start_time:.3f} seconds.")
    

if __name__ == "__main__":
    Logger.system("This is a test run of the embedding module.")
    start_time = time.perf_counter()

    if not embed_pdf("data/raw_manual.pdf", embedding_model=EM, db_path="data/pdf_data.db"):
        Logger.critical("Embedding process failed.")
        sys.exit(1)

    query_text = "yüz tanıma sisteminin çalışmama sebepleri neler olabilir"
    results = query(query_text, n=10)
    Logger.info(f"Query results for '{query_text}': {results}")

    end_time = time.perf_counter()
    Logger.perf(f"Embedding module test run completed in {end_time - start_time:.3f} seconds.")

    pages = axxonParser.get_pages("data/raw_manual.pdf")

    
    