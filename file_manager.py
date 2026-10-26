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

Davranış:
    - Basit bir dosya adı verilirse varsayılan olarak storage kullanılır.
    - Alt klasörler desteklenir.
    - storage/... ve data/... yolları desteklenir.
    - İzin verilen klasörlerin içindeki absolute path'ler desteklenir.
    - storage/data dışına çıkmaya çalışan yollar engellenir.
    - create_file aynı isimde dosya varsa mevcut içeriğin üzerine yazar.

Örnekler:
    create_file("example.txt", b"Hello")
        -> storage/example.txt

    create_file("documents/example.txt", b"Hello")
        -> storage/documents/example.txt

    create_file("data/example.txt", b"Hello")
        -> data/example.txt

    load_file("storage/example.txt")

    load_file("data/document.pdf")

    rename_file("data/old.pdf", "new.pdf")
        -> data/new.pdf

    delete_file("data/example.txt")
"""

from pathlib import Path


# ============================================================
# TEMEL KLASÖRLER
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STORAGE_DIR = BASE_DIR / "storage"
DATA_DIR = BASE_DIR / "data"


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def _validate_path(path_value: str) -> Path:
    """
    Kullanıcıdan gelen dosya yolunun temel doğrulamasını yapar.

    Alt klasör kullanımına izin verilir.

    Geçerli örnekler:
        file.txt
        documents/file.txt
        storage/file.txt
        data/file.pdf
        data/documents/file.pdf

    Raises:
        ValueError:
            Yol string değilse,
            boşsa,
            null karakter içeriyorsa
            veya '..' ile üst klasöre çıkılmaya çalışılıyorsa.
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

    # ../ veya ..\ kullanılarak üst klasöre çıkılmasını engeller.
    if ".." in path.parts:
        raise ValueError(
            "Dosya yolunda '..' kullanılamaz."
        )

    # Windows'ta C:folder\file.txt gibi drive-relative
    # yolların kullanılmasını engeller.
    if path.drive and not path.is_absolute():
        raise ValueError(
            "Drive-relative dosya yolları kullanılamaz."
        )

    return path


def _is_inside(path: Path, directory: Path) -> bool:
    """
    Bir yolun verilen klasörün içinde olup olmadığını kontrol eder.

    Args:
        path:
            Kontrol edilecek yol.

        directory:
            İzin verilen ana klasör.

    Returns:
        bool:
            Yol klasörün içindeyse True,
            değilse False.
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
    Kullanıcıdan gelen yolu güvenli bir dosya yoluna dönüştürür.

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

    Absolute path yalnızca storage veya data klasörlerinin
    içindeyse kabul edilir.

    Symlink dahil gerçek yol kontrol edilir ve izin verilen
    klasörlerin dışına çıkış engellenir.

    Args:
        path_value:
            Kullanıcı tarafından verilen dosya adı veya yolu.

        default_directory:
            Prefix verilmediğinde kullanılacak varsayılan klasör.
            Belirtilmezse STORAGE_DIR kullanılır.

    Returns:
        Path:
            Güvenli dosya yolu.

    Raises:
        ValueError:
            Yol geçersizse veya izin verilen klasörlerin
            dışına çıkıyorsa.

        OSError:
            Dosya sistemi yolu çözümlenirken hata oluşursa.
    """

    # STORAGE_DIR testlerde monkeypatch ile değiştirilebildiği için
    # varsayılan değer fonksiyon tanımında sabitlenmez.
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
        candidate_path = supplied_path
        resolved_path = candidate_path.resolve(strict=False)

        if not any(
            _is_inside(resolved_path, root)
            for root in allowed_roots
        ):
            raise ValueError(
                "Dosya yolu izin verilen klasörlerin "
                "dışına çıkamaz."
            )

        return candidate_path

    # --------------------------------------------------------
    # RELATIVE PATH
    # --------------------------------------------------------

    parts = supplied_path.parts

    if not parts:
        raise ValueError(
            "Geçerli bir dosya yolu verilmelidir."
        )

    first_part = parts[0].lower()

    # storage/... şeklinde verilmişse
    if first_part == STORAGE_DIR.name.lower():
        root = STORAGE_DIR
        relative_parts = parts[1:]

    # data/... şeklinde verilmişse
    elif first_part == DATA_DIR.name.lower():
        root = DATA_DIR
        relative_parts = parts[1:]

    # Prefix yoksa varsayılan olarak storage kullanılır.
    else:
        root = default_directory
        relative_parts = parts

    if not relative_parts:
        raise ValueError(
            "Bir klasör değil, dosya yolu verilmelidir."
        )

    relative_path = Path(*relative_parts)

    candidate_path = root / relative_path

    resolved_root = root.resolve()
    resolved_path = candidate_path.resolve(strict=False)

    # Symlink dahil gerçek yolun root dışına çıkmasını engeller.
    if not _is_inside(
        resolved_path,
        resolved_root,
    ):
        raise ValueError(
            "Dosya yolu izin verilen klasörün "
            "dışına çıkamaz."
        )

    return candidate_path


# ============================================================
# PUBLIC API
# ============================================================

def load_file(filename: str) -> bytes:
    """
    Diskte bulunan bir dosyayı hafızaya yükler.

    Args:
        filename:
            Dosya adı veya güvenli dosya yolu.

            Örnek:
                example.txt
                documents/example.txt
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
            Dosya yolu geçersizse,
            izin verilen klasörlerin dışına çıkıyorsa
            veya verilen yol bir dosya değilse.

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
    Hafızadaki binary veriyi diske kaydeder.

    Dosya mevcut değilse yeni dosya oluşturur.

    Aynı isimde dosya zaten mevcutsa eski içeriği siler
    ve verilen yeni içeriği dosyanın üzerine yazar.

    Basit dosya adı verilirse varsayılan olarak storage
    klasörü kullanılır.

    Örnek:

        create_file(
            "example.txt",
            b"Hello AxxonSoft"
        )

        -> storage/example.txt

    Alt klasör:

        create_file(
            "documents/example.txt",
            b"Hello"
        )

        -> storage/documents/example.txt

    Data klasörü:

        create_file(
            "data/example.txt",
            b"Hello"
        )

        -> data/example.txt

    Args:
        filename:
            Oluşturulacak veya üzerine yazılacak
            dosyanın adı veya yolu.

        content:
            Dosyaya yazılacak bytes verisi.

    Raises:
        ValueError:
            filename veya content geçersizse.

        OSError:
            Dosya sistemi işlemi başarısız olursa.
    """

    if not isinstance(content, bytes):
        raise ValueError(
            "Dosya içeriği bytes türünde olmalıdır."
        )

    # Storage klasörünün mevcut olduğundan emin olur.
    STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = _resolve_file_path(filename)

    # data/... veya alt klasör kullanılıyorsa
    # gerekli klasörleri otomatik oluşturur.
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # "w" -> dosya mevcutsa içeriğini sıfırlar ve üzerine yazar.
    #        dosya mevcut değilse yeni dosya oluşturur.
    #
    # "b" -> binary mod.
    with file_path.open("wb") as file:
        file.write(content)


def rename_file(
    old_filename: str,
    new_filename: str,
) -> None:
    """
    Diskte bulunan bir dosyanın adını değiştirir.

    Sadece yeni dosya adı verilirse dosya mevcut olduğu
    klasörde yeniden adlandırılır.

    Örnek:

        rename_file(
            "data/document.pdf",
            "new_document.pdf"
        )

    Sonuç:

        data/document.pdf
            ->
        data/new_document.pdf

    Eğer new_filename açık bir yol içeriyorsa
    belirtilen hedef kullanılır.

    Örnek:

        rename_file(
            "data/document.pdf",
            "storage/document.pdf"
        )

    Args:
        old_filename:
            Mevcut dosyanın adı veya yolu.

        new_filename:
            Yeni dosya adı veya güvenli yolu.

    Raises:
        FileNotFoundError:
            Eski dosya bulunamazsa.

        FileExistsError:
            Hedef dosya zaten mevcutsa.

        ValueError:
            Dosya yollarından biri geçersizse
            veya verilen yol dosya değilse.

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

    # --------------------------------------------------------
    # SADECE YENİ DOSYA ADI VERİLMİŞSE
    #
    # Örnek:
    # data/a.pdf -> b.pdf
    #
    # Sonuç:
    # data/b.pdf
    # --------------------------------------------------------

    if (
        not validated_new_path.is_absolute()
        and len(validated_new_path.parts) == 1
    ):
        new_path = old_path.parent / validated_new_path.name

        resolved_new_path = new_path.resolve(strict=False)

        allowed_roots = (
            STORAGE_DIR.resolve(),
            DATA_DIR.resolve(),
        )

        if not any(
            _is_inside(resolved_new_path, root)
            for root in allowed_roots
        ):
            raise ValueError(
                "Yeni dosya yolu izin verilen "
                "klasörlerin dışına çıkamaz."
            )

    # --------------------------------------------------------
    # AÇIK HEDEF YOL VERİLMİŞSE
    # --------------------------------------------------------

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
            Silinecek dosyanın adı veya güvenli yolu.

            Örnek:
                example.txt
                storage/example.txt
                data/example.pdf
                data/documents/example.pdf

    Raises:
        FileNotFoundError:
            Dosya bulunamazsa.

        ValueError:
            Dosya yolu geçersizse
            veya verilen yol dosya değilse.

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