# Dosya yükleme ve kaydetme özellikleri.
# diskteki bir dosyayı hafızaya yükleyen ve referans değişkenini döndüren bir fonksiyon
# diskte bir dosyanın ismini değiştirebilen bir fonksiyon
# diskte bulunan bir dosyayı silebilen bir fonksiyon
# hafızadaki bir dosyayı diske kaydeden bir fonksiyon

# ============================================================
# FILE MANAGER - PROJE NOTLARI
# ============================================================
#
# Bu modül AxxonSoft Index AI projesindeki dosya yönetimi
# işlemlerinden sorumludur.
#
# Desteklenen işlemler:
#
# 1. create_file(filename: str, content: bytes) -> None
#    - Hafızadaki binary veriyi storage klasörüne kaydeder.
#    - Aynı isimde dosya varsa FileExistsError oluşturur.
#
# 2. load_file(filename: str) -> bytes
#    - Diskte bulunan dosyayı hafızaya yükler.
#    - Dosya içeriğini bytes olarak döndürür.
#    - Dosya bulunamazsa FileNotFoundError oluşturur.
#
# 3. rename_file(old_filename: str, new_filename: str) -> None
#    - Diskteki bir dosyanın adını değiştirir.
#    - Eski dosya bulunamazsa FileNotFoundError oluşturur.
#    - Yeni isimde dosya varsa FileExistsError oluşturur.
#
# 4. delete_file(filename: str) -> None
#    - Diskte bulunan dosyayı siler.
#    - Dosya bulunamazsa FileNotFoundError oluşturur.
#
#
# HATA YÖNETİMİ
# ------------------------------------------------------------
#
# Kullanılan exception türleri:
#
# - FileExistsError
# - FileNotFoundError
# - ValueError
# - OSError
#
#
# GÜVENLİK
# ------------------------------------------------------------
#
# File Manager yalnızca "storage" klasörü içinde çalışır.
#
# Aşağıdaki gibi güvensiz yollar engellenir:
#
# ../secret.txt
# ../../file.txt
# folder/file.txt
# folder\file.txt
# C:\Windows\file.txt
#
# Böylece kullanıcının storage klasörünün dışındaki dosyalara
# erişmesi engellenir.
#
# Symbolic link kullanılarak storage klasörünün dışına çıkılması
# da _get_file_path() fonksiyonu tarafından kontrol edilir.
#
#
# BINARY DOSYA DESTEĞİ
# ------------------------------------------------------------
#
# Dosya içerikleri bytes olarak yönetildiği için sistem:
#
# - TXT
# - PDF
# - JSON
# - resim dosyaları
# - diğer binary dosya türleri
#
# gibi farklı dosya türlerini bozmadan saklayabilir.
#
#
# TESTLER
# ------------------------------------------------------------
#
# Test dosyası:
# test_file_manager.py
#
# Testleri çalıştırmak için:
#
# python -m pytest -v
#
# Test edilen durumlar:
#
# - Dosya oluşturma
# - Dosya yükleme
# - Dosya yeniden adlandırma
# - Dosya silme
# - Binary veri bütünlüğü
# - FileExistsError
# - FileNotFoundError
# - ValueError
# - Güvensiz yolların engellenmesi
#
# ============================================================


"""
AxxonSoft Index AI - File Manager

Bu modül, uygulamanın storage klasöründeki dosyaları güvenli bir şekilde
oluşturmak, hafızaya yüklemek, yeniden adlandırmak ve silmek için kullanılır.

Public API:
    create_file(filename: str, content: bytes) -> None
    load_file(filename: str) -> bytes
    rename_file(old_filename: str, new_filename: str) -> None
    delete_file(filename: str) -> None
"""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"


def _validate_filename(filename: str) -> str:
    """
    Dosya adının geçerli ve güvenli olup olmadığını kontrol eder.

    Raises:
        ValueError: Dosya adı geçersizse.
    """

    if not isinstance(filename, str):
        raise ValueError("Dosya adı string türünde olmalıdır.")

    filename = filename.strip()

    if not filename:
        raise ValueError("Dosya adı boş olamaz.")

    if filename in {".", ".."}:
        raise ValueError("Geçersiz dosya adı.")

    if "/" in filename or "\\" in filename:
        raise ValueError("Dosya adı klasör yolu içeremez.")

    if "\x00" in filename:
        raise ValueError("Dosya adı null karakter içeremez.")

    # Windows drive/path ifadelerini engeller.
    if ":" in filename:
        raise ValueError("Dosya adı ':' karakteri içeremez.")

    return filename


def _get_file_path(filename: str) -> Path:
    """
    storage klasörü içindeki güvenli dosya yolunu döndürür.

    Symlink kullanılarak storage dışındaki bir dosyaya erişilmesini
    engellemek için gerçek dosya yolu da kontrol edilir.

    Raises:
        ValueError: Dosya storage klasörünün dışına yönleniyorsa.
        OSError: Dosya sistemi yolu çözümlenirken hata oluşursa.
    """

    valid_filename = _validate_filename(filename)

    storage_path = STORAGE_DIR.resolve()
    file_path = STORAGE_DIR / valid_filename

    resolved_file_path = file_path.resolve(strict=False)

    if resolved_file_path.parent != storage_path:
        raise ValueError(
            "Dosya storage klasörünün dışına yönlendirilemez."
        )

    return file_path


def load_file(filename: str) -> bytes:
    """
    Diskteki bir dosyayı hafızaya yükler.

    Args:
        filename: Yüklenecek dosyanın adı.

    Returns:
        bytes: Dosyanın hafızadaki binary içeriği.

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        ValueError: Dosya adı geçersiz veya güvensizse.
        OSError: Dosya okunurken sistem hatası oluşursa.
    """

    file_path = _get_file_path(filename)

    with file_path.open("rb") as file:
        return file.read()


def create_file(filename: str, content: bytes) -> None:
    """
    Hafızadaki binary veriyi yeni bir dosya olarak diske kaydeder.

    Args:
        filename: Oluşturulacak dosyanın adı.
        content: Dosyaya yazılacak binary veri.

    Raises:
        FileExistsError: Aynı isimde dosya zaten varsa.
        ValueError: Dosya adı veya content geçersizse.
        OSError: Dosya oluşturulurken sistem hatası oluşursa.
    """

    if not isinstance(content, bytes):
        raise ValueError("Dosya içeriği bytes türünde olmalıdır.")

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    file_path = _get_file_path(filename)

    with file_path.open("xb") as file:
        file.write(content)


def rename_file(old_filename: str, new_filename: str) -> None:
    """
    Diskte bulunan bir dosyanın adını değiştirir.

    Args:
        old_filename: Mevcut dosyanın adı.
        new_filename: Yeni dosya adı.

    Raises:
        FileNotFoundError: Eski dosya bulunamazsa.
        FileExistsError: Yeni dosya adı zaten kullanılıyorsa.
        ValueError: Dosya adlarından biri geçersiz veya güvensizse.
        OSError: Yeniden adlandırma işlemi başarısız olursa.
    """

    old_path = _get_file_path(old_filename)
    new_path = _get_file_path(new_filename)

    if not old_path.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadı: {old_filename}"
        )

    if new_path.exists():
        raise FileExistsError(
            f"Bu isimde bir dosya zaten mevcut: {new_filename}"
        )

    old_path.rename(new_path)


def delete_file(filename: str) -> None:
    """
    Diskte bulunan bir dosyayı siler.

    Args:
        filename: Silinecek dosyanın adı.

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        ValueError: Dosya adı geçersiz veya güvensizse.
        OSError: Dosya silinirken sistem hatası oluşursa.
    """

    file_path = _get_file_path(filename)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadı: {filename}"
        )

    file_path.unlink()