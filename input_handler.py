# Kullanıcıdan gelen input değerlendirilecek. Konuşma mı, hesaplama isteği mi, başka bir şey mi belirlenecek.
# Belirlenen tipe göre ya programlar çalıştırılacak ya da llm çalıştırılacak.


"""
Kullanıcıdan gelen isteği analiz eden modül.

Görevleri:
1. İsteğin türünü belirlemek.
2. Platform Calculator isteğiyse gerekli parametreleri çıkarmak.
3. Normal konuşma ise LLM tarafına yönlendirilmek üzere işaretlemek.

Şimdilik desteklenen istek türleri:
- conversation
- platform_calculation
"""

import re

from platform_matrix import normalize_platform_parameters
from platform_service import handle_platform_request


# ============================================================
# REQUEST TYPES
# ============================================================

REQUEST_CONVERSATION = "conversation"
REQUEST_PLATFORM_CALCULATION = "platform_calculation"


# ============================================================
# PLATFORM CALCULATION DETECTION
# ============================================================

CALCULATION_ACTION_WORDS = (
    "hesapla",
    "hesaplama",
    "hesap",
    "öner",
    "öneri",
    "platform",
    "server",
    "sunucu",
    "sistem öner",
    "sistem hesapla",
)


PLATFORM_PARAMETER_WORDS = (
    "kamera",
    "camera",
    "fps",
    "bitrate",
    "mbit",
    "codec",
    "h264",
    "h.264",
    "h265",
    "h.265",
    "hevc",
    "mjpeg",
    "mp",
    "megapixel",
    "çözünürlük",
    "resolution",
    "arşiv",
    "archive",
    "gün",
)


def detect_request_type(
    user_input: str,
) -> str:
    """
    Kullanıcı mesajının hangi işlem türüne ait
    olduğunu belirler.
    """

    if not isinstance(user_input, str):
        raise ValueError(
            "user_input string olmalıdır."
        )

    text = user_input.strip().lower()

    if not text:
        raise ValueError(
            "Kullanıcı mesajı boş olamaz."
        )

    has_action = any(
        keyword in text
        for keyword in CALCULATION_ACTION_WORDS
    )

    parameter_count = sum(
        keyword in text
        for keyword in PLATFORM_PARAMETER_WORDS
    )

    # Calculator'ın açılması için:
    #
    # - hesaplama niyeti bulunmalı
    # - en az bir teknik platform parametresi bulunmalı
    #
    # Böylece:
    # "AxxonSoft server nedir?"
    #
    # gibi bilgi soruları yanlışlıkla calculator'a gitmez.
    if has_action and parameter_count >= 1:
        return REQUEST_PLATFORM_CALCULATION

    return REQUEST_CONVERSATION


# ============================================================
# CAMERA COUNT
# ============================================================

def extract_camera_count(
    text: str,
) -> int | None:
    """
    Kamera sayısını kullanıcı mesajından çıkarır.

    Örnekler:
        10 kamera
        10 adet kamera
        10 tane 4 MP H.265 kamera
        kamera sayısı 20

    H.265 gibi codec değerlerindeki sayıları
    kamera sayısı olarak algılamaz.
    """

    # Önce "10 tane" / "10 adet" gibi güçlü ifadeleri ara.
    match = re.search(
        r"\b(\d+)\s*(?:adet|tane)\b",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        # Bu sayı yalnızca cümlede kamera ifadesi de varsa
        # kamera sayısı olarak kabul edilir.
        if re.search(
            r"\b(?:kamera|camera)s?\b",
            text,
            flags=re.IGNORECASE,
        ):
            return int(
                match.group(1)
            )

    # "kamera sayısı: 10"
    match = re.search(
        r"\b(?:kamera|camera)\s*"
        r"(?:sayısı\s*)?"
        r"[:=]?\s*(\d+)\b",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return int(
            match.group(1)
        )

    # "10 kamera"
    #
    # (?<![\d.]) sayesinde H.265 kamera içindeki
    # "265 kamera" kısmı eşleşmez.
    match = re.search(
        r"(?<![\d.])\b(\d+)\s*"
        r"(?:kamera|camera)s?\b",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return int(
            match.group(1)
        )

    return None

# ============================================================
# ARCHIVE DAYS
# ============================================================

def extract_archive_days(
    text: str,
) -> int | None:
    """
    Arşiv süresini gün olarak çıkarır.

    Örnek:
        30 gün
        45 günlük kayıt
        60 gün arşiv
    """

    patterns = (
        r"(\d+)\s*gün(?:lük)?",
        r"(\d+)\s*day(?:s)?",
        r"(?:archive|arşiv)\s*[:=]?\s*(\d+)",
    )

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return int(
                match.group(1)
            )

    return None


# ============================================================
# FPS
# ============================================================

def extract_fps(
    text: str,
) -> int | None:
    """
    FPS değerini çıkarır.
    """

    patterns = (
        r"(\d+)\s*fps\b",
        r"fps\s*[:=]?\s*(\d+)",
    )

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return int(
                match.group(1)
            )

    return None


# ============================================================
# BITRATE
# ============================================================

def extract_bitrate(
    text: str,
) -> float | None:
    """
    Bitrate değerini Mbit/s olarak çıkarır.

    Örnek:
        3.33 Mbit/s
        4 Mbps
        bitrate 2.5
    """

    patterns = (
        r"(\d+(?:[.,]\d+)?)\s*(?:mbit/s|mbps|mbit)",
        r"bitrate\s*[:=]?\s*(\d+(?:[.,]\d+)?)",
    )

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

            value = (
                match.group(1)
                .replace(",", ".")
            )

            return float(value)

    return None


# ============================================================
# CODEC
# ============================================================

def extract_codec(
    text: str,
) -> str | None:
    """
    Codec bilgisini çıkarır.
    """

    codec_patterns = (
        r"\bh\.?264\b",
        r"\bh\.?265\b",
        r"\bhevc\b",
        r"\bmjpe?g\b",
    )

    for pattern in codec_patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(0)

    return None


# ============================================================
# RESOLUTION
# ============================================================

def extract_resolution(
    text: str,
) -> str | None:
    """
    Resolution veya megapixel bilgisini çıkarır.

    Öncelik:
    1. Gerçek çözünürlük: 1920x1080
    2. MP: 4 MP
    3. Yaygın isim: 1080p / 4K / Full HD
    """

    # 1920x1080 vb.
    match = re.search(
        r"\b(\d{3,4}\s*[xX×]\s*\d{3,4})\b",
        text,
    )

    if match:

        value = match.group(1)

        value = re.sub(
            r"\s+",
            "",
            value,
        )

        value = (
            value
            .replace("X", "x")
            .replace("×", "x")
        )

        return value

    # 4 MP / 8MP vb.
    match = re.search(
        r"\b(\d+(?:[.,]\d+)?)\s*(?:mp|megapixel)\b",
        text,
        flags=re.IGNORECASE,
    )

    if match:

        mp = (
            match.group(1)
            .replace(",", ".")
        )

        return f"{mp} MP"

    # Yaygın resolution isimleri.
    aliases = (
        "1080p",
        "720p",
        "1440p",
        "2160p",
        "full hd",
        "fullhd",
        "fhd",
        "qhd",
        "wqhd",
        "4k",
        "4k uhd",
        "uhd",
        "8k",
    )

    lowered = text.lower()

    for alias in aliases:
        if alias in lowered:
            return alias

    return None


# ============================================================
# PLATFORM PARAMETERS
# ============================================================

def extract_platform_parameters(
    user_input: str,
) -> dict:
    """
    Kullanıcı mesajından calculator parametrelerini çıkarır.

    Çıkarılan değerler platform_matrix üzerinden
    normalize edilir.
    """

    camera_count = extract_camera_count(
        user_input
    )

    archive_days = extract_archive_days(
        user_input
    )

    resolution = extract_resolution(
        user_input
    )

    fps = extract_fps(
        user_input
    )

    codec = extract_codec(
        user_input
    )

    bitrate_mbps = extract_bitrate(
        user_input
    )

    # --------------------------------------------------------
    # Zorunlu bilgiler
    # --------------------------------------------------------

    missing = []

    if camera_count is None:
        missing.append(
            "camera_count"
        )

    if archive_days is None:
        missing.append(
            "archive_days"
        )

    if missing:
        raise ValueError(
            "Platform hesabı için eksik bilgiler: "
            + ", ".join(missing)
        )

    # Resolution, FPS ve Codec verilmezse
    # platform_matrix default değerlerini kullanabilir.
    parameters = normalize_platform_parameters(
        camera_count=camera_count,
        archive_days=archive_days,
        resolution=resolution,
        fps=fps,
        codec=codec,
        bitrate_mbps=bitrate_mbps,
    )

    return parameters


# ============================================================
# MAIN INPUT ANALYSIS
# ============================================================

def analyze_input(
    user_input: str,
) -> dict:
    """
    Kullanıcı mesajının tamamını analiz eder.

    Returns:

        Normal konuşma:

        {
            "type": "conversation",
            "text": "..."
        }

        Platform hesabı:

        {
            "type": "platform_calculation",
            "parameters": {...}
        }
    """

    request_type = detect_request_type(
        user_input
    )

    if (
        request_type
        == REQUEST_PLATFORM_CALCULATION
    ):

        parameters = extract_platform_parameters(
            user_input
        )

        return {
            "type":
                REQUEST_PLATFORM_CALCULATION,

            "parameters":
                parameters,
        }

    return {
        "type":
            REQUEST_CONVERSATION,

        "text":
            user_input,
    }

def process_input(
    user_input: str,
) -> dict:
    """
    Kullanıcı isteğini analiz eder ve gerekiyorsa
    ilgili programı çalıştırır.

    Platform hesaplama isteği:
        Platform Calculator çalıştırılır.

    Normal konuşma:
        LLM tarafından cevaplanmak üzere işaretlenir.

    Returns:
        {
            "type": str,
            "response": str | None,
            "parameters": dict | None
        }
    """

    analysis = analyze_input(
        user_input
    )

    request_type = analysis["type"]

    # ========================================================
    # PLATFORM CALCULATION
    # ========================================================

    if (
        request_type
        == REQUEST_PLATFORM_CALCULATION
    ):

        parameters = analysis[
            "parameters"
        ]

        response = handle_platform_request(
            camera_count=parameters[
                "camera_count"
            ],

            archive_days=parameters[
                "archive_days"
            ],

            resolution=parameters[
                "resolution"
            ],

            fps=parameters[
                "fps"
            ],

            codec=parameters[
                "codec"
            ],

            bitrate_mbps=parameters[
                "bitrate_mbps"
            ],

            software=parameters[
                "software"
            ],

            calculation_type=parameters[
                "calculation_type"
            ],
        )

        return {
            "type":
                REQUEST_PLATFORM_CALCULATION,

            "parameters":
                parameters,

            "response":
                response,
        }

    # ========================================================
    # NORMAL CONVERSATION
    # ========================================================

    return {
        "type":
            REQUEST_CONVERSATION,

        "parameters":
            None,

        # Burayı daha sonra mevcut LLM sistemimize bağlayacağız.
        "response":
            None,
    }
# ============================================================
# MANUEL TEST
# ============================================================

if __name__ == "__main__":

    user_message = (
        "10 tane 4 MP H.265 kamera, "
        "25 FPS, 3.33 Mbit/s ve "
        "30 gün kayıt için platform hesapla"
    )

    print(
        "Kullanıcı:",
        user_message,
    )

    print("\nİstek analiz ediliyor...\n")

    try:

        result = process_input(
            user_message
        )

        print(
            "İstek tipi:",
            result["type"],
        )

        print(
            "\nÇıkarılan parametreler:"
        )

        if result["parameters"]:

            for key, value in (
                result["parameters"].items()
            ):
                print(
                    f"{key}: {value}"
                )

        print(
            "\nAI CEVABI"
        )

        print(
            "=" * 60
        )

        print(
            result["response"]
        )

    except ValueError as error:

        print(
            "Geçersiz istek:",
            error,
        )

    except Exception as error:

        print(
            "Platform hesabı sırasında hata oluştu:",
            error,
        )