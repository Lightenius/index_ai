from bake_pdf import bake_pdf

bake_pdf(
    pdf_path="data/raw_manual.pdf",
    index_path="data/vector_db.db",
    model="bge-m3",
    chunk_size=1800,
    overlap=250,
    batch_size=32
)