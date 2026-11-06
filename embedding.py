# Anlam eşleşmesine göre pasajlar puanlanacak, en yüksek puanlı X pasaj döndürülecek.

import time

from logger import Logger
import sqlite3
import axxonParser

def embed_pdf(pdf_path, embedding_model = "bge-m3", db_path = "data/pdf_data.db", top_k=5):
    Logger.system(f"Starting embedding process for PDF: {pdf_path}")
    performance_start = time.perf_counter()

    # Connect to the SQLite database
    db = sqlite3.connect(db_path)
    cursor = db.cursor()

    # Extract pages from the PDF
    pages = axxonParser.get_pages(pdf_path)
