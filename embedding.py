
from pathlib import Path

from bake_pdf import PDFIndex, load_index


class Embedding:
    """
    Önceden oluşturulmuş PDF embedding index'i üzerinde
    anlamsal arama gerçekleştirir.
    """

    def __init__(self, index_path: str | Path) -> None:
        """
        Embedding index'ini diskten yükler.

        Args:
            index_path: SQLite index dosyasının yolu.

        Raises:
            FileNotFoundError: Index dosyası bulunamazsa.
            ValueError: Index geçersiz veya tamamlanmamışsa.
        """
        self.index: PDFIndex = load_index(index_path)

    def search(
        self,
        query: str,
        n: int = 5
    ) -> list[dict]:
        """
        Verilen query ile en alakalı pasajları bulur.

        Args:
            query: Aranacak metin.
            n: Döndürülecek pasaj sayısı.

        Returns:
            list[dict]: Benzerlik skoruna göre sıralanmış pasajlar.

        Raises:
            ValueError: Query boşsa veya n geçersizse.
            RuntimeError: Embedding işlemi başarısız olursa.
        """
        try:
            return self.index.search(
                query=query,
                n=n
            )
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(
                f"Anlamsal arama başarısız: {exc}"
            ) from exc
