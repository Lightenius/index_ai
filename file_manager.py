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

Bu modül uygulamadaki dosya işlemlerinden sorumludur.

Desteklenen ana işlemler:
    create_file(filename: str, content: bytes) -> None
    load_file(filename: str) -> bytes
    rename_file(old_filename: str, new_filename: str) -> None
    delete_file(filename: str) -> None

Desteklenen dosya alanları:
    storage/
    data/

Basit bir dosya adı verilirse varsayılan olarak storage klasörü kullanılır.

Örnekler:
    create_file("example.txt", b"Hello")
        -> storage/example.txt

    load_file("storage/example.txt")

    load_file("data/document.pdf")

    load_file("data/documents/document.pdf")
"""

from pathlib import Path


# ------------------------------------------------------------
# TEMEL KLASÖRLER
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

STORAGE_DIR = BASE_DIR / "storage"
DATA_DIR = BASE_DIR / "data"


# ------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ------------------------------------------------------------

def _validate_path(path_value: str) -> Path:
    """
    Kullanıcıdan gelen dosya yolunun temel doğrulamasını yapar.

    Alt klasör kullanımına izin verilir.

    Örnek geçerli değerler:
        file.txt
        storage/file.txt
        data/file.pdf
        data/documents/file.pdf

    Raises:
        ValueError:
            Yol boşsa, string değilse, null karakter içeriyorsa
            veya '..' ile path traversal deneniyorsa.
    """

    if not isinstance(path_value, str):
        raise ValueError(
            "Dosya adı veya yolu string türünde olmalıdır."
        )

    path_value = path_value.strip()

    if not path_value:
        raise ValueError(
            "Dosya adı veya yolu boş olamaz."
        )

    if "\x00" in path_value:
        raise ValueError(
            "Dosya yolu null karakter içeremez."
        )

    path = Path(path_value)

    # ../ veya ..\\ kullanılarak üst klasöre çıkılmasını engeller.
    if ".." in path.parts:
        raise ValueError(
            "Dosya yolunda '..' kullanılamaz."
        )

    return path


def _is_inside(path: Path, directory: Path) -> bool:
    """
    Bir yolun verilen klasörün içinde olup olmadığını kontrol eder.
    """

    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def _resolve_file_path(
    path_value: str,
    default_directory: Path | None = None,
) -> Path:
    """
    Kullanıcıdan gelen yolu güvenli bir gerçek dosya yoluna dönüştürür.

    Kurallar:
        file.txt
            -> storage/file.txt

        folder/file.txt
            -> storage/folder/file.txt

        storage/file.txt
            -> storage/file.txt

        data/file.txt
            -> data/file.txt

        data/folder/file.txt
            -> data/folder/file.txt

    Absolute path yalnızca storage veya data klasörlerinin içindeyse
    kabul edilir.

    Raises:
        ValueError:
            Yol storage veya data klasörlerinin dışına çıkıyorsa.
    """

    # ÖNEMLİ:
    # STORAGE_DIR testlerde monkeypatch ile değiştirilebildiği için
    # varsayılan değeri fonksiyon tanımında değil,
    # fonksiyon çalışırken belirliyoruz.
    if default_directory is None:
        default_directory = STORAGE_DIR

    supplied_path = _validate_path(path_value)

    storage_root = STORAGE_DIR.resolve()
    data_root = DATA_DIR.resolve()

    allowed_roots = (
        storage_root,
        data_root,
    )

    # --------------------------------------------------------
    # ABSOLUTE PATH
    # --------------------------------------------------------

    if supplied_path.is_absolute():
        resolved_path = supplied_path.resolve(strict=False)

        if not any(
            _is_inside(resolved_path, root)
            for root in allowed_roots
        ):
            raise ValueError(
                "Dosya yolu izin verilen klasörlerin "
                "dışına çıkamaz."
            )

        return resolved_path

    # --------------------------------------------------------
    # RELATIVE PATH
    # --------------------------------------------------------

    parts = supplied_path.parts

    if not parts:
        raise ValueError(
            "Geçerli bir dosya yolu verilmelidir."
        )

    first_part = parts[0].lower()

    # storage/... verilmişse
    if first_part == STORAGE_DIR.name.lower():
        root = STORAGE_DIR
        relative_parts = parts[1:]

    # data/... verilmişse
    elif first_part == DATA_DIR.name.lower():
        root = DATA_DIR
        relative_parts = parts[1:]

    # Sadece dosya adı veya klasör/dosya verilmişse
    # varsayılan storage kullanılır.
    else:
        root = default_directory
        relative_parts = parts

    if not relative_parts:
        raise ValueError(
            "Bir klasör değil, dosya yolu verilmelidir."
        )

    relative_path = Path(*relative_parts)

    resolved_root = root.resolve()

    resolved_path = (
        root / relative_path
    ).resolve(strict=False)

    # Symlink dahil olmak üzere gerçek yolun
    # seçilen root dışına çıkmasını engeller.
    if not _is_inside(
        resolved_path,
        resolved_root,
    ):
        raise ValueError(
            "Dosya yolu izin verilen klasörün "
            "dışına çıkamaz."
        )

    return resolved_path


# ------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------

def load_file(filename: str) -> bytes:
    """
    Diskte bulunan dosyayı hafızaya yükler.

    Args:
        filename:
            Dosya adı veya güvenli dosya yolu.

            Örnek:
                example.txt
                storage/example.txt
                data/example.pdf
                data/documents/example.pdf

    Returns:
        bytes:
            Dosyanın hafızaya yüklenmiş binary içeriği.

    Raises:
        FileNotFoundError:
            Dosya bulunamazsa.

        ValueError:
            Dosya yolu geçersizse veya izin verilen
            klasörlerin dışına çıkıyorsa.

        OSError:
            Dosya okunurken işletim sistemi hatası oluşursa.
    """

    file_path = _resolve_file_path(filename)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadı: {filename}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Verilen yol bir dosya değil: {filename}"
        )

    with file_path.open("rb") as file:
        return file.read()


def create_file(
    filename: str,
    content: bytes,
) -> None:
    """
    Hafızadaki binary veriyi diskte yeni dosya olarak oluşturur.

    Basit dosya adı verilirse dosya storage klasörüne kaydedilir.

    Örnek:
        create_file(
            "example.txt",
            b"Hello AxxonSoft"
        )

        -> storage/example.txt

    Alt klasör de kullanılabilir:

        create_file(
            "documents/example.txt",
            b"Hello"
        )

        -> storage/documents/example.txt

    Args:
        filename:
            Oluşturulacak dosyanın adı veya yolu.

        content:
            Dosyaya yazılacak bytes verisi.

    Raises:
        FileExistsError:
            Dosya zaten mevcutsa.

        ValueError:
            filename veya content geçersizse.

        OSError:
            Dosya sistemi işlemi başarısız olursa.
    """

    if not isinstance(content, bytes):
        raise ValueError(
            "Dosya içeriği bytes türünde olmalıdır."
        )

    # Ana storage klasörünün mevcut olduğundan emin ol.
    STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = _resolve_file_path(filename)

    # data/... veya alt klasör kullanılıyorsa
    # gerekli klasörleri oluştur.
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # "x" -> dosya sadece yoksa oluşturulur.
    # "b" -> binary mod.
    #
    # Dosya mevcutsa FileExistsError otomatik oluşur.
    with file_path.open("xb") as file:
        file.write(content)


def rename_file(
    old_filename: str,
    new_filename: str,
) -> None:
    """
    Diskte bulunan bir dosyanın adını değiştirir.

    Örnek:

        rename_file(
            "data/document.pdf",
            "new_document.pdf"
        )

    Sonuç:

        data/document.pdf
            ->
        data/new_document.pdf

    Eğer new_filename açık bir yol içeriyorsa o yol kullanılır:

        rename_file(
            "data/document.pdf",
            "storage/document.pdf"
        )

    Args:
        old_filename:
            Mevcut dosyanın adı veya yolu.

        new_filename:
            Yeni dosya adı veya yolu.

    Raises:
        FileNotFoundError:
            Eski dosya bulunamazsa.

        FileExistsError:
            Hedef dosya zaten varsa.

        ValueError:
            Dosya yollarından biri geçersizse.

        OSError:
            Yeniden adlandırma sırasında sistem hatası oluşursa.
    """

    old_path = _resolve_file_path(
        old_filename
    )

    if not old_path.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadı: {old_filename}"
        )

    if not old_path.is_file():
        raise ValueError(
            f"Verilen yol bir dosya değil: {old_filename}"
        )

    validated_new_path = _validate_path(
        new_filename
    )

    # Sadece yeni dosya adı verilmişse:
    #
    # data/a.pdf -> b.pdf
    #
    # sonucunu:
    #
    # data/b.pdf
    #
    # olarak yap.
    if (
        not validated_new_path.is_absolute()
        and len(validated_new_path.parts) == 1
    ):
        new_path = (
            old_path.parent
            / validated_new_path.name
        ).resolve(strict=False)

        # Eski dosyanın parent klasöründen
        # symlink vb. yollarla çıkışı kontrol et.
        allowed_roots = (
            STORAGE_DIR.resolve(),
            DATA_DIR.resolve(),
        )

        if not any(
            _is_inside(new_path, root)
            for root in allowed_roots
        ):
            raise ValueError(
                "Yeni dosya yolu izin verilen "
                "klasörlerin dışına çıkamaz."
            )

    else:
        new_path = _resolve_file_path(
            new_filename
        )

    if new_path.exists():
        raise FileExistsError(
            f"Bu isimde bir dosya zaten mevcut: "
            f"{new_filename}"
        )

    new_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    old_path.rename(new_path)


def delete_file(filename: str) -> None:
    """
    Diskte bulunan bir dosyayı siler.

    Args:
        filename:
            Silinecek dosyanın adı veya yolu.

            Örnek:
                example.txt
                storage/example.txt
                data/example.pdf

    Raises:
        FileNotFoundError:
            Dosya bulunamazsa.

        ValueError:
            Dosya yolu geçersizse.

        OSError:
            Dosya silinirken işletim sistemi hatası oluşursa.
    """

    file_path = _resolve_file_path(
        filename
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadı: {filename}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Verilen yol bir dosya değil: {filename}"
        )

    file_path.unlink()