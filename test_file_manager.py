import pytest
import file_manager


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    """
    Her test için geçici storage ve data klasörleri kullanır.

    Böylece testler gerçek proje klasörlerindeki dosyalara dokunmaz.
    """

    storage_dir = tmp_path / "storage"
    data_dir = tmp_path / "data"

    monkeypatch.setattr(
        file_manager,
        "STORAGE_DIR",
        storage_dir,
    )

    monkeypatch.setattr(
        file_manager,
        "DATA_DIR",
        data_dir,
    )

    return storage_dir


# ============================================================
# CREATE FILE TESTLERİ
# ============================================================

def test_create_file(temp_storage):
    file_manager.create_file(
        "test.txt",
        b"Hello AxxonSoft",
    )

    created_file = temp_storage / "test.txt"

    assert created_file.exists()
    assert created_file.is_file()
    assert created_file.read_bytes() == b"Hello AxxonSoft"


def test_create_existing_file_raises_error(temp_storage):
    file_manager.create_file(
        "test.txt",
        b"First content",
    )

    with pytest.raises(FileExistsError):
        file_manager.create_file(
            "test.txt",
            b"Second content",
        )


def test_create_file_in_subdirectory(temp_storage):
    """
    Alt klasör kullanımının desteklendiğini kontrol eder.
    """

    file_manager.create_file(
        "documents/test.txt",
        b"Subdirectory test",
    )

    created_file = (
        temp_storage
        / "documents"
        / "test.txt"
    )

    assert created_file.exists()
    assert created_file.read_bytes() == b"Subdirectory test"


def test_create_file_with_storage_prefix(temp_storage):
    """
    storage/... şeklindeki yolların çalıştığını kontrol eder.
    """

    file_manager.create_file(
        "storage/example.txt",
        b"Storage prefix",
    )

    created_file = temp_storage / "example.txt"

    assert created_file.exists()
    assert created_file.read_bytes() == b"Storage prefix"


def test_create_file_in_data_directory(temp_storage):
    """
    data/... yoluyla data klasörüne dosya yazılabildiğini
    kontrol eder.
    """

    file_manager.create_file(
        "data/document.txt",
        b"Data directory",
    )

    created_file = (
        file_manager.DATA_DIR
        / "document.txt"
    )

    assert created_file.exists()
    assert created_file.read_bytes() == b"Data directory"


# ============================================================
# LOAD FILE TESTLERİ
# ============================================================

def test_load_file(temp_storage):
    file_manager.create_file(
        "test.txt",
        b"Hello AxxonSoft",
    )

    data = file_manager.load_file(
        "test.txt"
    )

    assert data == b"Hello AxxonSoft"


def test_load_file_from_subdirectory(temp_storage):
    file_manager.create_file(
        "documents/test.txt",
        b"Hello from folder",
    )

    data = file_manager.load_file(
        "documents/test.txt"
    )

    assert data == b"Hello from folder"


def test_load_file_from_data_directory(temp_storage):
    file_manager.create_file(
        "data/test.txt",
        b"Hello Data",
    )

    data = file_manager.load_file(
        "data/test.txt"
    )

    assert data == b"Hello Data"


def test_load_missing_file_raises_error(temp_storage):
    with pytest.raises(FileNotFoundError):
        file_manager.load_file(
            "olmayan_dosya.txt"
        )


# ============================================================
# RENAME FILE TESTLERİ
# ============================================================

def test_rename_file(temp_storage):
    file_manager.create_file(
        "old.txt",
        b"Test content",
    )

    file_manager.rename_file(
        "old.txt",
        "new.txt",
    )

    assert not (
        temp_storage / "old.txt"
    ).exists()

    assert (
        temp_storage / "new.txt"
    ).exists()

    assert (
        temp_storage / "new.txt"
    ).read_bytes() == b"Test content"


def test_rename_file_in_data_directory(temp_storage):
    """
    data/old.txt -> new.txt çağrısının
    data/new.txt sonucunu oluşturduğunu kontrol eder.
    """

    file_manager.create_file(
        "data/old.txt",
        b"Data rename",
    )

    file_manager.rename_file(
        "data/old.txt",
        "new.txt",
    )

    old_file = (
        file_manager.DATA_DIR
        / "old.txt"
    )

    new_file = (
        file_manager.DATA_DIR
        / "new.txt"
    )

    assert not old_file.exists()
    assert new_file.exists()
    assert new_file.read_bytes() == b"Data rename"


def test_rename_missing_file_raises_error(temp_storage):
    with pytest.raises(FileNotFoundError):
        file_manager.rename_file(
            "olmayan.txt",
            "new.txt",
        )


def test_rename_existing_destination_raises_error(
    temp_storage,
):
    file_manager.create_file(
        "first.txt",
        b"First",
    )

    file_manager.create_file(
        "second.txt",
        b"Second",
    )

    with pytest.raises(FileExistsError):
        file_manager.rename_file(
            "first.txt",
            "second.txt",
        )


def test_rename_between_allowed_directories(temp_storage):
    """
    storage içindeki bir dosyanın data klasörüne
    taşınabildiğini kontrol eder.
    """

    file_manager.create_file(
        "move_me.txt",
        b"Move test",
    )

    file_manager.rename_file(
        "move_me.txt",
        "data/moved.txt",
    )

    assert not (
        temp_storage / "move_me.txt"
    ).exists()

    destination = (
        file_manager.DATA_DIR
        / "moved.txt"
    )

    assert destination.exists()
    assert destination.read_bytes() == b"Move test"


# ============================================================
# DELETE FILE TESTLERİ
# ============================================================

def test_delete_file(temp_storage):
    file_manager.create_file(
        "delete_me.txt",
        b"Delete",
    )

    file_manager.delete_file(
        "delete_me.txt"
    )

    assert not (
        temp_storage / "delete_me.txt"
    ).exists()


def test_delete_file_from_data_directory(temp_storage):
    file_manager.create_file(
        "data/delete_me.txt",
        b"Delete",
    )

    file_manager.delete_file(
        "data/delete_me.txt"
    )

    assert not (
        file_manager.DATA_DIR
        / "delete_me.txt"
    ).exists()


def test_delete_missing_file_raises_error(temp_storage):
    with pytest.raises(FileNotFoundError):
        file_manager.delete_file(
            "olmayan.txt"
        )


# ============================================================
# VALUE ERROR TESTLERİ
# ============================================================

def test_empty_filename_raises_value_error(temp_storage):
    with pytest.raises(ValueError):
        file_manager.create_file(
            "",
            b"content",
        )


def test_invalid_content_type_raises_value_error(
    temp_storage,
):
    with pytest.raises(ValueError):
        file_manager.create_file(
            "test.txt",
            "Bu bytes değil",
        )


def test_directory_instead_of_file_raises_error(
    temp_storage,
):
    directory = temp_storage / "folder"

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    with pytest.raises(ValueError):
        file_manager.load_file(
            "folder"
        )


# ============================================================
# GÜVENLİK TESTLERİ
# ============================================================

@pytest.mark.parametrize(
    "filename",
    [
        "../hack.txt",
        "../../secret.txt",
        "documents/../../../secret.txt",
        "..",
    ],
)
def test_path_traversal_is_rejected(
    temp_storage,
    filename,
):
    """
    '..' kullanılarak izin verilen klasörlerin
    dışına çıkılamadığını kontrol eder.
    """

    with pytest.raises(ValueError):
        file_manager.create_file(
            filename,
            b"test",
        )


def test_absolute_path_outside_allowed_directories_is_rejected(
    temp_storage,
    tmp_path,
):
    """
    storage ve data dışındaki absolute path'lerin
    engellendiğini kontrol eder.
    """

    outside_file = (
        tmp_path
        / "outside"
        / "secret.txt"
    ).resolve()

    with pytest.raises(ValueError):
        file_manager.create_file(
            str(outside_file),
            b"secret",
        )


def test_absolute_path_inside_storage_is_allowed(
    temp_storage,
):
    """
    storage içindeki absolute path kullanımının
    desteklendiğini kontrol eder.
    """

    absolute_file = (
        temp_storage
        / "absolute.txt"
    ).resolve()

    file_manager.create_file(
        str(absolute_file),
        b"Absolute path test",
    )

    assert absolute_file.exists()

    data = file_manager.load_file(
        str(absolute_file)
    )

    assert data == b"Absolute path test"


# ============================================================
# BINARY DOSYA TESTLERİ
# ============================================================

def test_binary_file_content(temp_storage):
    """
    PDF, resim vb. binary dosyalardaki verilerin
    bozulmadan kaydedilip okunabildiğini kontrol eder.
    """

    binary_data = bytes([
        0,
        1,
        2,
        3,
        255,
        128,
        64,
        32,
    ])

    file_manager.create_file(
        "binary_file.bin",
        binary_data,
    )

    loaded_data = file_manager.load_file(
        "binary_file.bin"
    )

    assert loaded_data == binary_data


def test_empty_binary_file(temp_storage):
    """
    İçeriği boş olan bir dosyanın da
    oluşturulabildiğini kontrol eder.
    """

    file_manager.create_file(
        "empty.bin",
        b"",
    )

    loaded_data = file_manager.load_file(
        "empty.bin"
    )

    assert loaded_data == b""