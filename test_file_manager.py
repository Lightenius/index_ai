import pytest
import file_manager


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    """
    Her test için geçici bir storage klasörü kullanır.

    Böylece gerçek storage klasörü test sırasında değiştirilmez.
    """
    monkeypatch.setattr(file_manager, "STORAGE_DIR", tmp_path)
    return tmp_path


def test_create_file(temp_storage):
    file_manager.create_file(
        "test.txt",
        b"Hello AxxonSoft"
    )

    created_file = temp_storage / "test.txt"

    assert created_file.exists()
    assert created_file.read_bytes() == b"Hello AxxonSoft"


def test_create_existing_file_raises_error(temp_storage):
    file_manager.create_file(
        "test.txt",
        b"First content"
    )

    with pytest.raises(FileExistsError):
        file_manager.create_file(
            "test.txt",
            b"Second content"
        )


def test_load_file(temp_storage):
    file_manager.create_file(
        "test.txt",
        b"Hello AxxonSoft"
    )

    data = file_manager.load_file("test.txt")

    assert data == b"Hello AxxonSoft"


def test_load_missing_file_raises_error(temp_storage):
    with pytest.raises(FileNotFoundError):
        file_manager.load_file(
            "olmayan_dosya.txt"
        )


def test_rename_file(temp_storage):
    file_manager.create_file(
        "old.txt",
        b"Test content"
    )

    file_manager.rename_file(
        "old.txt",
        "new.txt"
    )

    assert not (temp_storage / "old.txt").exists()
    assert (temp_storage / "new.txt").exists()

    assert (
        temp_storage / "new.txt"
    ).read_bytes() == b"Test content"


def test_rename_missing_file_raises_error(temp_storage):
    with pytest.raises(FileNotFoundError):
        file_manager.rename_file(
            "olmayan.txt",
            "new.txt"
        )


def test_rename_existing_destination_raises_error(
    temp_storage
):
    file_manager.create_file(
        "first.txt",
        b"First"
    )

    file_manager.create_file(
        "second.txt",
        b"Second"
    )

    with pytest.raises(FileExistsError):
        file_manager.rename_file(
            "first.txt",
            "second.txt"
        )


def test_delete_file(temp_storage):
    file_manager.create_file(
        "delete_me.txt",
        b"Delete"
    )

    file_manager.delete_file(
        "delete_me.txt"
    )

    assert not (
        temp_storage / "delete_me.txt"
    ).exists()


def test_delete_missing_file_raises_error(temp_storage):
    with pytest.raises(FileNotFoundError):
        file_manager.delete_file(
            "olmayan.txt"
        )


def test_empty_filename_raises_value_error(temp_storage):
    with pytest.raises(ValueError):
        file_manager.create_file(
            "",
            b"content"
        )


def test_invalid_content_type_raises_value_error(
    temp_storage
):
    with pytest.raises(ValueError):
        file_manager.create_file(
            "test.txt",
            "Bu bytes değil"
        )


@pytest.mark.parametrize(
    "filename",
    [
        "../hack.txt",
        "../../secret.txt",
        "folder/test.txt",
        r"folder\test.txt",
        r"C:\Windows\test.txt",
        ".",
        "..",
    ],
)
def test_unsafe_filenames_are_rejected(
    temp_storage,
    filename
):
    with pytest.raises(ValueError):
        file_manager.create_file(
            filename,
            b"test"
        )


def test_binary_file_content(temp_storage):
    """
    File Manager'ın yalnızca metin değil,
    PDF/resim gibi binary içerikleri de bozmadan
    saklayabildiğini kontrol eder.
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
        binary_data
    )

    loaded_data = file_manager.load_file(
        "binary_file.bin"
    )

    assert loaded_data == binary_data