"""
Axxon Platform Calculator için merkezi parametre matrisi.

Bu modülün görevi:
1. Calculator'ın desteklediği değerleri tek yerde tutmak.
2. Kullanıcının farklı yazımlarını standart değerlere çevirmek.
3. Calculator'a gönderilmeden önce parametreleri doğrulamak.
4. input_handler.py, platform_service.py ve platform_calculator.py
   arasında ortak bir veri standardı sağlamak.

Bu modül:
- Web sitesine bağlanmaz.
- Playwright çalıştırmaz.
- Hesaplama yapmaz.
"""


# ============================================================
# DEFAULT DEĞERLER
# ============================================================

DEFAULT_SOFTWARE = "Axxon One (x64)"
DEFAULT_CALCULATION_TYPE = "Server"

DEFAULT_RESOLUTION = "2688x1520"
DEFAULT_FPS = 25
DEFAULT_CODEC = "H265"


# ============================================================
# SOFTWARE
# ============================================================

SUPPORTED_SOFTWARE = (
    "Axxon One (x64)",
    "Axxon PSIM (x64)",
)


SOFTWARE_ALIASES = {
    "axxon one": "Axxon One (x64)",
    "axxonone": "Axxon One (x64)",
    "axxon one x64": "Axxon One (x64)",
    "axxon one (x64)": "Axxon One (x64)",

    "axxon psim": "Axxon PSIM (x64)",
    "psim": "Axxon PSIM (x64)",
    "axxon psim x64": "Axxon PSIM (x64)",
    "axxon psim (x64)": "Axxon PSIM (x64)",
}


# ============================================================
# CALCULATION TYPE
# ============================================================

SUPPORTED_CALCULATION_TYPES = (
    "Server",
    "Server with viewing client",
    "Operator's workstation",
)


CALCULATION_TYPE_ALIASES = {
    "server": "Server",
    "sunucu": "Server",

    "server with viewing client":
        "Server with viewing client",

    "server with client":
        "Server with viewing client",

    "viewing client":
        "Server with viewing client",

    "operator's workstation":
        "Operator's workstation",

    "operator workstation":
        "Operator's workstation",

    "operator station":
        "Operator's workstation",

    "operator":
        "Operator's workstation",
}


# ============================================================
# CODEC
# ============================================================

SUPPORTED_CODECS = (
    "H264",
    "H265",
    "MjPEG",
)


CODEC_ALIASES = {
    "h264": "H264",
    "h.264": "H264",
    "avc": "H264",

    "h265": "H265",
    "h.265": "H265",
    "hevc": "H265",

    "mjpeg": "MjPEG",
    "m-jpeg": "MjPEG",
    "motion jpeg": "MjPEG",
}


# ============================================================
# FPS
# ============================================================

FPS_MIN = 1
FPS_MAX = 60


# ============================================================
# RESOLUTION
# ============================================================

# Calculator'dan doğrudan alınan çözünürlük seçenekleri.

RESOLUTION_LABELS = {
    "200x100": "200x100 (0.02 MP)",
    "320x240": "320x240 (0.1 MP QVGA)",
    "400x200": "400x200 (0.07 MP)",
    "352x288": "352x288 (CIF)",
    "704x288": "704x288 (CIF2)",
    "640x360": "640x360 (0.2 MP 16:9)",
    "640x480": "640x480 (0.3 MP VGA)",
    "704x480": "704x480 (0.3 MP)",
    "704x576": "704x576 (CIF4)",
    "720x576": "720x576 (0.4 MP D1)",
    "800x600": "800x600 (0.5 MP SVGA)",
    "1024x768": "1024x768 (0.8 MP XGA)",
    "1280x720": "1280x720 (0.9 MP 720p)",
    "1280x960": "1280x960 (1.2 MP)",
    "1280x1024": "1280x1024 (1.3 MP SXGA)",
    "1600x1200": "1600x1200 (1.8 MP UXGA)",
    "1920x1080": "1920x1080 (2 MP 1080p)",
    "2048x1536": "2048x1536 (3 MP QXGA)",
    "3012x1152": "3012x1152 (3 MP)",
    "2560x1440": "2560x1440 (3 MP WQHD)",
    "2688x1520": "2688x1520 (4 MP)",
    "2560x1600": "2560x1600 (4 MP WQXGA)",
    "2048x2048": "2048x2048 (4.19 MP)",
    "2560x1920": "2560x1920 (5 MP)",
    "2592x1920": "2592x1920 (4.7 MP QSXGA)",
    "2592x1944": "2592x1944 (5.04 MP)",
    "2560x2048": "2560x2048 (5.2 MP QSXGA)",
    "3072x1728": "3072x1728 (5.31 MP)",
    "3072x2048": "3072x2048 (6.29 MP)",
    "2560x2560": "2560x2560 (6 MP)",
    "3072x2304": "3072x2304 (7.08 MP)",
    "6400x1200": "6400x1200 (7.3 MP)",
    "3840x2160": "3840x2160 (8 MP 2160p)",
    "4096x2160": "4096x2160 (8 MP 4K UHD)",
    "3072x3072": "3072x3072 (9.4 MP)",
    "3648x2752": "3648x2752 (10 MP)",
    "4000x3000": "4000x3000 (12 MP)",
    "4000x3072": "4000x3072 (12 MP 3072p)",
    "5472x3648": "5472x3648 (20 MP)",
    "7680x4320": "7680x4320 (32 MP 4320p)",
    "8192x4320": "8192x4320 (34 MP 8K UHD)",
}


SUPPORTED_RESOLUTIONS = tuple(
    RESOLUTION_LABELS.keys()
)


# ============================================================
# RESOLUTION ALIASES
# ============================================================

# Kullanıcının günlük dilde kullanabileceği yaygın ifadeler.

RESOLUTION_ALIASES = {
    "720p": "1280x720",
    "hd": "1280x720",

    "1080p": "1920x1080",
    "full hd": "1920x1080",
    "fullhd": "1920x1080",
    "fhd": "1920x1080",

    "1440p": "2560x1440",
    "qhd": "2560x1440",
    "wqhd": "2560x1440",

    "2160p": "3840x2160",
    "4k": "3840x2160",
    "4k uhd": "3840x2160",
    "uhd": "3840x2160",

    "8k": "8192x4320",
}


# ============================================================
# MEGAPIXEL MATRİSİ
# ============================================================

# Önemli:
#
# MP değeri her zaman tek bir çözünürlüğe karşılık gelmez.
#
# Örneğin calculator'da iki farklı 4 MP seçeneği vardır:
#
# 2688x1520
# 2560x1600
#
# Bu nedenle "options" tüm uygun seçenekleri,
# "default" ise AI'ın ek bilgi yoksa kullanacağı değeri tutar.

MEGAPIXEL_PRESETS = {
    "2mp": {
        "default": "1920x1080",
        "options": (
            "1920x1080",
        ),
    },

    "3mp": {
        "default": "2048x1536",
        "options": (
            "2048x1536",
            "3012x1152",
            "2560x1440",
        ),
    },

    "4mp": {
        "default": "2688x1520",
        "options": (
            "2688x1520",
            "2560x1600",
        ),
    },

    "5mp": {
        "default": "2560x1920",
        "options": (
            "2560x1920",
            "2592x1944",
        ),
    },

    "6mp": {
        "default": "2560x2560",
        "options": (
            "2560x2560",
        ),
    },

    "8mp": {
        "default": "3840x2160",
        "options": (
            "3840x2160",
            "4096x2160",
        ),
    },

    "10mp": {
        "default": "3648x2752",
        "options": (
            "3648x2752",
        ),
    },

    "12mp": {
        "default": "4000x3000",
        "options": (
            "4000x3000",
            "4000x3072",
        ),
    },

    "20mp": {
        "default": "5472x3648",
        "options": (
            "5472x3648",
        ),
    },
}


# ============================================================
# RAID
# ============================================================

SUPPORTED_RAID_TYPES = (
    "NO_RAID",
    "JBOD",
    "RAID_0",
    "RAID_1",
    "RAID_10",
    "RAID_5",
    "RAID_6",
)


RAID_ALIASES = {
    "no raid": "NO_RAID",
    "without raid": "NO_RAID",
    "raid yok": "NO_RAID",

    "jbod": "JBOD",

    "raid 0": "RAID_0",
    "raid0": "RAID_0",

    "raid 1": "RAID_1",
    "raid1": "RAID_1",

    "raid 10": "RAID_10",
    "raid10": "RAID_10",

    "raid 5": "RAID_5",
    "raid5": "RAID_5",

    "raid 6": "RAID_6",
    "raid6": "RAID_6",
}


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def _normalize_text(value: str) -> str:
    """
    Kullanıcıdan gelen metni karşılaştırmaya uygun hale getirir.
    """

    if not isinstance(value, str):
        raise ValueError(
            "Değer string olmalıdır."
        )

    return " ".join(
        value.strip().lower().split()
    )


def _normalize_mp_text(value: str) -> str:
    """
    '4 MP', '4mp', '4 megapixel' gibi ifadeleri
    ortak formata getirir.

    Örnek:
        '4 MP' -> '4mp'
    """

    text = _normalize_text(value)

    text = text.replace(
        "megapixels",
        "mp",
    )

    text = text.replace(
        "megapixel",
        "mp",
    )

    text = text.replace(
        "mega pixel",
        "mp",
    )

    text = text.replace(
        " ",
        "",
    )

    return text


# ============================================================
# SOFTWARE NORMALIZATION
# ============================================================

def normalize_software(
    software: str | None,
) -> str:
    """
    Software değerini calculator'ın kullandığı
    standart değere çevirir.
    """

    if software is None:
        return DEFAULT_SOFTWARE

    if software in SUPPORTED_SOFTWARE:
        return software

    key = _normalize_text(
        software
    )

    normalized = SOFTWARE_ALIASES.get(
        key
    )

    if normalized is None:
        raise ValueError(
            f"Desteklenmeyen software: {software}. "
            f"Desteklenen değerler: {SUPPORTED_SOFTWARE}"
        )

    return normalized


# ============================================================
# CALCULATION TYPE NORMALIZATION
# ============================================================

def normalize_calculation_type(
    calculation_type: str | None,
) -> str:
    """
    Calculation type değerini calculator'ın
    kullandığı standart değere çevirir.
    """

    if calculation_type is None:
        return DEFAULT_CALCULATION_TYPE

    if calculation_type in SUPPORTED_CALCULATION_TYPES:
        return calculation_type

    key = _normalize_text(
        calculation_type
    )

    normalized = CALCULATION_TYPE_ALIASES.get(
        key
    )

    if normalized is None:
        raise ValueError(
            "Desteklenmeyen calculation type: "
            f"{calculation_type}"
        )

    return normalized


# ============================================================
# CODEC NORMALIZATION
# ============================================================

def normalize_codec(
    codec: str | None,
) -> str:
    """
    Codec değerini calculator'ın kullandığı
    standart değere dönüştürür.

    Örnek:
        H.265 -> H265
        HEVC  -> H265
    """

    if codec is None:
        return DEFAULT_CODEC

    if codec in SUPPORTED_CODECS:
        return codec

    key = _normalize_text(
        codec
    )

    normalized = CODEC_ALIASES.get(
        key
    )

    if normalized is None:
        raise ValueError(
            f"Desteklenmeyen codec: {codec}. "
            f"Desteklenen codec'ler: {SUPPORTED_CODECS}"
        )

    return normalized


# ============================================================
# RESOLUTION NORMALIZATION
# ============================================================

def get_resolution_candidates(
    resolution: str,
) -> tuple[str, ...]:
    """
    Kullanıcı ifadesine karşılık gelebilecek
    tüm resolution seçeneklerini döndürür.

    Örnek:
        '4 MP'

    Returns:
        (
            '2688x1520',
            '2560x1600',
        )
    """

    if not isinstance(resolution, str):
        raise ValueError(
            "resolution string olmalıdır."
        )

    value = resolution.strip()

    # Kullanıcı doğrudan 1920x1080 gibi
    # calculator değerini vermiş olabilir.
    if value in SUPPORTED_RESOLUTIONS:
        return (
            value,
        )

    text_key = _normalize_text(
        resolution
    )

    alias = RESOLUTION_ALIASES.get(
        text_key
    )

    if alias is not None:
        return (
            alias,
        )

    mp_key = _normalize_mp_text(
        resolution
    )

    preset = MEGAPIXEL_PRESETS.get(
        mp_key
    )

    if preset is not None:
        return preset["options"]

    raise ValueError(
        f"Desteklenmeyen resolution: {resolution}"
    )


def normalize_resolution(
    resolution: str | None,
) -> str:
    """
    Resolution değerini calculator'ın kullanabileceği
    standart değere çevirir.

    Bir MP değeri birden fazla resolution'a karşılık
    geliyorsa preset içindeki default kullanılır.
    """

    if resolution is None:
        return DEFAULT_RESOLUTION

    value = resolution.strip()

    if value in SUPPORTED_RESOLUTIONS:
        return value

    text_key = _normalize_text(
        resolution
    )

    alias = RESOLUTION_ALIASES.get(
        text_key
    )

    if alias is not None:
        return alias

    mp_key = _normalize_mp_text(
        resolution
    )

    preset = MEGAPIXEL_PRESETS.get(
        mp_key
    )

    if preset is not None:
        return preset["default"]

    raise ValueError(
        f"Desteklenmeyen resolution: {resolution}"
    )


# ============================================================
# SAYISAL VALIDATION
# ============================================================

def normalize_camera_count(
    camera_count: int,
) -> int:
    """
    Kamera sayısını doğrular.
    """

    if isinstance(
        camera_count,
        bool,
    ):
        raise ValueError(
            "camera_count integer olmalıdır."
        )

    try:
        camera_count = int(
            camera_count
        )
    except (TypeError, ValueError):
        raise ValueError(
            "camera_count integer olmalıdır."
        )

    if camera_count <= 0:
        raise ValueError(
            "camera_count 0'dan büyük olmalıdır."
        )

    return camera_count


def normalize_archive_days(
    archive_days: int,
) -> int:
    """
    Arşiv gün sayısını doğrular.
    """

    if isinstance(
        archive_days,
        bool,
    ):
        raise ValueError(
            "archive_days integer olmalıdır."
        )

    try:
        archive_days = int(
            archive_days
        )
    except (TypeError, ValueError):
        raise ValueError(
            "archive_days integer olmalıdır."
        )

    if archive_days < 0:
        raise ValueError(
            "archive_days negatif olamaz."
        )

    return archive_days


def normalize_fps(
    fps: int | None,
) -> int:
    """
    FPS değerini doğrular.

    Calculator:
        1 - 60 FPS
    """

    if fps is None:
        return DEFAULT_FPS

    if isinstance(
        fps,
        bool,
    ):
        raise ValueError(
            "fps integer olmalıdır."
        )

    try:
        fps = int(
            fps
        )
    except (TypeError, ValueError):
        raise ValueError(
            "fps integer olmalıdır."
        )

    if not FPS_MIN <= fps <= FPS_MAX:
        raise ValueError(
            f"fps {FPS_MIN} ile "
            f"{FPS_MAX} arasında olmalıdır."
        )

    return fps


def normalize_bitrate(
    bitrate_mbps: float | None,
) -> float | None:
    """
    Bitrate değerini doğrular.

    None verilirse calculator'ın kendi mevcut/default
    bitrate değerinin kullanılmasına izin verir.

    Bu davranışı platform_calculator.py tarafında
    bir sonraki aşamada destekleyeceğiz.
    """

    if bitrate_mbps is None:
        return None

    if isinstance(
        bitrate_mbps,
        bool,
    ):
        raise ValueError(
            "bitrate_mbps sayı olmalıdır."
        )

    try:
        bitrate_mbps = float(
            bitrate_mbps
        )
    except (TypeError, ValueError):
        raise ValueError(
            "bitrate_mbps sayı olmalıdır."
        )

    if bitrate_mbps <= 0:
        raise ValueError(
            "bitrate_mbps 0'dan büyük olmalıdır."
        )

    return bitrate_mbps


# ============================================================
# TÜM PARAMETRELERİ NORMALIZE ET
# ============================================================

def normalize_platform_parameters(
    camera_count: int,
    archive_days: int,
    resolution: str | None = None,
    fps: int | None = None,
    codec: str | None = None,
    bitrate_mbps: float | None = None,
    software: str | None = None,
    calculation_type: str | None = None,
) -> dict:
    """
    AI veya input_handler tarafından çıkarılan
    calculator parametrelerini doğrular ve normalize eder.

    Returns:
        Calculator'a gönderilmeye hazır dictionary.
    """

    return {
        "camera_count":
            normalize_camera_count(
                camera_count
            ),

        "archive_days":
            normalize_archive_days(
                archive_days
            ),

        "resolution":
            normalize_resolution(
                resolution
            ),

        "fps":
            normalize_fps(
                fps
            ),

        "codec":
            normalize_codec(
                codec
            ),

        "bitrate_mbps":
            normalize_bitrate(
                bitrate_mbps
            ),

        "software":
            normalize_software(
                software
            ),

        "calculation_type":
            normalize_calculation_type(
                calculation_type
            ),
    }


# ============================================================
# GELECEKTE EKLENECEK PARAMETRELER
# ============================================================

# Calculator'da bulunan fakat henüz Playwright otomasyonuna
# bağlamadığımız alanlar.
#
# Bunları şu an normalize_platform_parameters içine dahil
# etmiyoruz. Otomasyonları tamamlandıkça ekleyeceğiz.

FUTURE_PLATFORM_FIELDS = (
    "camera_brand",
    "camera_model",
    "activity",
    "record_on_server",
    "transmit_to_client",
    "number_of_clients",
    "detectors",
    "raid_type",
    "raid_archive_capacity",
    "hot_spare_disks",
    "additional_camera_streams",
)


# ============================================================
# MANUEL TEST
# ============================================================

if __name__ == "__main__":

    parameters = normalize_platform_parameters(
        camera_count=10,
        archive_days=30,
        resolution="4 MP",
        fps=25,
        codec="H.265",
        bitrate_mbps=3.33,
        software="Axxon One",
        calculation_type="server",
    )

    print(
        "Normalize edilmiş parametreler:"
    )

    for key, value in parameters.items():
        print(
            f"{key}: {value}"
        )

    print("\n")

    print(
        "4 MP için mümkün çözünürlükler:"
    )

    print(
        get_resolution_candidates(
            "4 MP"
        )
    )