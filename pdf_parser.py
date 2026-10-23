
from pathlib import Path
import pymupdf


class PDFParser:
    """
    PDF dosyalarından metin çıkarır ve
    içerikleri sayfa numaralarına göre düzenler.
    """

    def __init__(self, file_path: str | Path) -> None:
        """
        PDF dosyasının yolunu alır ve saklar.

        Args:
            file_path (str | Path): PDF dosyasının yolu.

        Returns:
            None: Herhangi bir değer döndürmez.
        """
        self.file_path = Path(file_path)

    def extract_text(self, page: pymupdf.Page) -> str:
        """
        PDF'nin tek bir sayfasından metin çıkarır.

        Args:
            page (pymupdf.Page): Okunacak PDF sayfası.

        Returns:
            str: Sayfadan çıkarılan metin.
        """
        return page.get_text("text").strip()

    def parse(self) -> dict[int, dict[str, str]]:
        """
        PDF'nin bütün sayfalarını okuyarak dictionary oluşturur.

        Returns:
            dict[int, dict[str, str]]:
                Sayfa numaralarını ve metin içeriklerini tutar.

        Raises:
            FileNotFoundError: PDF dosyası bulunamazsa.
            ValueError: Dosya uzantısı PDF değilse.
        """

        # Dosyanın mevcut olup olmadığını kontrol eder.
        if not self.file_path.is_file():
            raise FileNotFoundError(
                f"Dosya bulunamadı: {self.file_path}"
            )

        # Dosyanın PDF uzantısına sahip olduğunu kontrol eder.
        if self.file_path.suffix.lower() != ".pdf":
            raise ValueError("Dosya PDF formatında olmalıdır.")

        # Sayfa bilgilerini saklamak için boş dictionary oluşturur.
        pages = {}

        # PDF dosyasını açar.
        with pymupdf.open(str(self.file_path)) as document:

            # Bütün sayfaları 1'den başlayarak numaralandırır.
            for page_number, page in enumerate(document, start=1):

                # Sayfa numarasını anahtar, metni değer olarak kaydeder.
                pages[page_number] = {
                    "text": self.extract_text(page)
                }

        # Oluşturulan dictionary'yi döndürür.
        return pages
