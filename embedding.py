# Anlam eşleşmesine göre pasajlar puanlanacak, en yüksek puanlı X pasaj döndürülecek.

import time

import ollama

from logger import Logger
import axxonParser

from embedding_storage import EmbeddingStorage

def embed_text(text, model="bge-m3"):
    """Embed the given text using the specified model."""
    try:
        response = ollama.embed(model=model, text=text)
        vector = response['embedding']
        return vector
    except Exception as e:
        Logger.error(f"Failed to embed text: {e}")
        return None


def embed_pdf(pdf_path, embedding_model = "bge-m3", db_path = "data/pdf_data.db", top_k=5):
    Logger.system(f"Starting embedding process for PDF: {pdf_path}")
    performance_start = time.perf_counter()


    es = EmbeddingStorage(db_path=db_path)

    # Extract pages from the PDF
    pages = axxonParser.get_pages(pdf_path)

    # Embed each page and store in the database
    for page in pages:
        page_number = page["page_number"]
        content = page["content"]
        vector = embed_text(content, embedding_model)
        es.save_embedding(page_number, vector)


def query(text: str, n: int) {
    embed
}