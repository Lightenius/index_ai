
from pathlib import Path
import hashlib
import json
import os
import sqlite3

import numpy as np
import ollama
import pymupdf


DEFAULT_MODEL = "bge-m3"
DEFAULT_CHUNK_SIZE = 1800
DEFAULT_OVERLAP = 250
DEFAULT_BATCH_SIZE = 32


def _file_hash(file_path: Path) -> str:
    """PDF dosyasının SHA256 hash değerini hesaplar."""

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(block)

    return sha256.hexdigest()


def _split_text(
    text: str,
    chunk_size: int,
    overlap: int
) -> list[str]:
    """
    Metni örtüşen pasajlara böler.
    Mümkün olduğunca kelime sınırlarını korur.
    """

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Kelimenin ortasında bölünmemeye çalış.
        if end < len(text):
            boundary = text.rfind(" ", start + int(chunk_size * 0.8), end)

            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        next_start = end - overlap

        # Sonsuz döngüyü önle.
        start = max(next_start, start + 1)

    return chunks


def _read_metadata(db_path: Path) -> dict:
    """Mevcut index'in metadata bilgilerini okur."""

    with sqlite3.connect(str(db_path)) as connection:
        rows = connection.execute(
            "SELECT key, value FROM metadata"
        ).fetchall()

    return {key: value for key, value in rows}


def bake_pdf(
    pdf_path: str | Path,
    index_path: str | Path,
    model: str = DEFAULT_MODEL,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    batch_size: int = DEFAULT_BATCH_SIZE,
    force: bool = False
) -> None:
    """
    PDF dosyasının embedding index'ini oluşturur ve kaydeder.

    Args:
        pdf_path: Kaynak PDF dosyası.
        index_path: Oluşturulacak SQLite dosyası.
        model: Ollama embedding modeli.
        chunk_size: Pasaj uzunluğu (karakter).
        overlap: Pasajlar arasındaki örtüşme (karakter).
        batch_size: Tek seferde işlenecek pasaj sayısı.
        force: Mevcut index'i yeniden oluşturur.

    Raises:
        FileNotFoundError: PDF bulunamazsa.
        ValueError: Parametreler geçersizse.
        FileExistsError: Farklı bir index zaten mevcutsa.
        RuntimeError: Embedding işlemi başarısız olursa.
    """

    pdf_path = Path(pdf_path)
    index_path = Path(index_path)

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF bulunamadı: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Dosya PDF formatında olmalıdır.")

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Chunk ve overlap değerleri geçersiz.")

    if batch_size <= 0:
        raise ValueError("Batch size pozitif olmalıdır.")

    index_path.parent.mkdir(parents=True, exist_ok=True)

    source_hash = _file_hash(pdf_path)

    # Aynı PDF ve aynı ayarlarla oluşturulmuş index varsa tekrar hesaplama.
    if index_path.exists() and not force:
        metadata = _read_metadata(index_path)

        if (
            metadata.get("source_hash") == source_hash
            and metadata.get("model") == model
            and metadata.get("chunk_size") == str(chunk_size)
            and metadata.get("overlap") == str(overlap)
        ):
            return

        raise FileExistsError(
            "Farklı bir index mevcut. Yeniden oluşturmak için force=True kullanın."
        )

    # Geçici dosya kullanarak yarım index oluşmasını önle.
    temp_path = index_path.with_name(index_path.name + ".tmp")

    if temp_path.exists():
        temp_path.unlink()

    connection = None

    try:
        connection = sqlite3.connect(str(temp_path))

        connection.execute("""
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL
            )
        """)

        connection.execute("""
            CREATE INDEX idx_chunks_page
            ON chunks(page)
        """)

        # PDF sayfalarını oku ve pasajları oluştur.
        passages = []

        with pymupdf.open(str(pdf_path)) as document:
            for page_number, page in enumerate(document, start=1):

                page_text = page.get_text("text").strip()

                if not page_text:
                    continue

                chunks = _split_text(
                    page_text,
                    chunk_size,
                    overlap
                )

                for chunk in chunks:
                    passages.append((page_number, chunk))

        if not passages:
            raise ValueError("PDF içerisinde işlenebilir metin bulunamadı.")

        # Pasajları batch halinde embedding işleminden geçir.
        for i in range(0, len(passages), batch_size):

            batch = passages[i:i + batch_size]

            response = ollama.embed(
                model=model,
                input=[text for _, text in batch]
            )

            if len(response.embeddings) != len(batch):
                raise RuntimeError(
                    "Embedding sayısı ile pasaj sayısı eşleşmiyor."
                )

            records = []

            for (page_number, text), embedding in zip(
                batch, response.embeddings
            ):

                vector = np.asarray(
                    embedding,
                    dtype=np.float32
                )

                # Vektörleri normalize ederek sakla.
                norm = np.linalg.norm(vector)

                if norm == 0:
                    raise RuntimeError("Geçersiz embedding vektörü.")

                vector = vector / norm

                records.append((
                    page_number,
                    text,
                    vector.tobytes()
                ))

            connection.executemany("""
                INSERT INTO chunks (page, text, embedding)
                VALUES (?, ?, ?)
            """, records)

            connection.commit()

            print(
                f"Embedding: {min(i + batch_size, len(passages))}"
                f" / {len(passages)}"
            )

        # Index bilgilerini kaydet.
        metadata = {
            "source_hash": source_hash,
            "source_file": pdf_path.name,
            "model": model,
            "chunk_size": str(chunk_size),
            "overlap": str(overlap),
            "chunk_count": str(len(passages)),
            "status": "complete"
        }

        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            metadata.items()
        )

        connection.commit()
        connection.close()
        connection = None

        # Tamamlanan index'i hedef dosyaya taşı.
        os.replace(temp_path, index_path)

        print(f"Index oluşturuldu: {index_path}")

    except Exception:
        if connection is not None:
            connection.close()

        if temp_path.exists():
            temp_path.unlink()

        raise


class PDFIndex:
    """
    Diskten yüklenen PDF embedding index'i üzerinde arama yapar.
    """

    def __init__(self, index_path: str | Path) -> None:
        self.index_path = Path(index_path)

        if not self.index_path.is_file():
            raise FileNotFoundError(
                f"Index bulunamadı: {self.index_path}"
            )

        self.metadata = _read_metadata(self.index_path)

        if self.metadata.get("status") != "complete":
            raise ValueError("Index tamamlanmamış veya geçersiz.")

        self.model = self.metadata["model"]

        with sqlite3.connect(str(self.index_path)) as connection:
            rows = connection.execute("""
                SELECT page, text, embedding
                FROM chunks
            """).fetchall()

        if not rows:
            raise ValueError("Index içerisinde pasaj bulunamadı.")

        self.pages = [row[0] for row in rows]
        self.texts = [row[1] for row in rows]

        self.embeddings = np.stack([
            np.frombuffer(row[2], dtype=np.float32)
            for row in rows
        ])

    def search(
        self,
        query: str,
        n: int = 5
    ) -> list[dict]:
        """
        Query ile en alakalı pasajları bulur.

        Args:
            query: Aranacak metin.
            n: Döndürülecek pasaj sayısı.

        Returns:
            list[dict]: Benzerlik skoruna göre sıralanmış pasajlar.

        Raises:
            ValueError: Query veya n geçersizse.
        """

        if not query.strip():
            raise ValueError("Query boş olamaz.")

        if n <= 0:
            raise ValueError("n pozitif olmalıdır.")

        response = ollama.embed(
            model=self.model,
            input=query
        )

        query_vector = np.asarray(
            response.embeddings[0],
            dtype=np.float32
        )

        norm = np.linalg.norm(query_vector)

        if norm == 0:
            raise ValueError("Query embedding geçersiz.")

        query_vector /= norm

        # Normalize edilmiş vektörlerin dot product işlemi
        # cosine similarity ile aynıdır.
        scores = self.embeddings @ query_vector

        top_indices = np.argsort(scores)[::-1][:n]

        return [
            {
                "role": "context",
                "content": f"Page: {self.pages[i]}\n{self.texts[i]}\n"
            }
            for i in top_indices
        ]


def load_index(index_path: str | Path) -> PDFIndex:
    """
    Önceden oluşturulmuş PDF index'ini diskten yükler.

    Args:
        index_path: SQLite index dosyasının yolu.

    Returns:
        PDFIndex: Arama yapılabilecek index nesnesi.
    """

    return PDFIndex(index_path)
