import re
import time

from logger import Logger
from playwright.sync_api import (
    sync_playwright,
    Page,
    Frame,
    Error as PlaywrightError,
)


logger = Logger()

CALCULATOR_URL = (
    "https://sale.axxonsoft.com/calc/calculator.jsf"
)


# ============================================================
# LOGGER YARDIMCILARI
# ============================================================

def _log_system(message: str) -> None:
    """
    Logger sınıfında system seviyesi varsa onu kullanır.
    Yoksa INFO seviyesine düşer.
    """
    system_method = getattr(logger, "system", None)

    if callable(system_method):
        system_method(message)
    else:
        logger.info(message)


def _log_warning(message: str) -> None:
    """
    Logger sınıfında warning seviyesi varsa onu kullanır.
    Yoksa INFO seviyesine düşer.
    """
    warning_method = getattr(logger, "warning", None)

    if callable(warning_method):
        warning_method(message)
    else:
        logger.info(message)


# ============================================================
# POPUP YÖNETİMİ
# ============================================================

def _click_accept_in_frame(frame: Frame) -> bool:
    """
    Frame içinde görünür Accept butonu varsa tıklar.
    """
    try:
        buttons = frame.get_by_role(
            "button",
            name="Accept",
            exact=True,
        )

        for index in range(buttons.count()):
            button = buttons.nth(index)

            if button.is_visible():
                button.click(timeout=5000)
                return True

    except PlaywrightError:
        pass

    return False


def dismiss_popups(page: Page) -> int:
    """
    Important Note ve cookie gibi popup'ları kapatır.
    """
    clicked_count = 0

    for _ in range(5):
        clicked = False

        for frame in page.frames:
            if _click_accept_in_frame(frame):
                clicked_count += 1
                clicked = True

                logger.info(
                    f"Accept geçildi ({clicked_count})."
                )

                page.wait_for_timeout(700)
                break

        if not clicked:
            break

    return clicked_count


# ============================================================
# SAYFA HAZIRLIK
# ============================================================

def wait_until_calculator_ready(page: Page) -> None:
    """
    Calculator ana ekranının hazır olduğunu kontrol eder.
    """
    page.get_by_text(
        "Please select your software",
        exact=False,
    ).first.wait_for(
        state="visible",
        timeout=15000,
    )

    logger.info("Calculator hazır.")


# ============================================================
# CALCULATOR INPUT'LARI
# ============================================================

def select_software(
    page: Page,
    software: str = "Axxon One (x64)",
) -> None:
    """
    Kullanılacak AxxonSoft yazılımını seçer.
    """
    radio = page.get_by_role(
        "radio",
        name=software,
        exact=True,
    )

    radio.check()
    page.wait_for_timeout(800)

    logger.info(
        f"Software seçildi: {software}"
    )


def select_calculation_type(
    page: Page,
    calculation_type: str = "Server",
) -> None:
    """
    Hesaplama tipini seçer.
    """
    radio = page.get_by_role(
        "radio",
        name=calculation_type,
        exact=True,
    )

    radio.check()
    page.wait_for_timeout(800)

    logger.info(
        "Calculation type seçildi: "
        f"{calculation_type}"
    )


def set_camera_count(
    page: Page,
    camera_count: int,
) -> None:
    """
    İlk kamera grubunun kamera sayısını değiştirir.
    """
    if isinstance(camera_count, bool) or not isinstance(
        camera_count,
        int,
    ):
        raise ValueError(
            "camera_count integer olmalıdır."
        )

    if camera_count <= 0:
        raise ValueError(
            "camera_count 0'dan büyük olmalıdır."
        )

    # JSF içindeki j_id_XX kısmı değişebileceği için
    # tam ID yerine stabil prefix/suffix kullanıyoruz.
    camera_input = page.locator(
        'input['
        'id^="cameraGroupForm:cameras:cameraGroupPanel:0:'
        'cameraGroupMainSettingsPanel:"'
        '][id$="_input"]'
    ).first

    camera_input.wait_for(
        state="visible",
        timeout=10000,
    )

    old_value = camera_input.input_value()

    camera_input.fill(str(camera_count))
    camera_input.press("Tab")

    page.wait_for_timeout(1500)

    new_value = camera_input.input_value()

    if new_value != str(camera_count):
        raise RuntimeError(
            "Kamera sayısı değiştirilemedi. "
            f"Beklenen: {camera_count}, mevcut: {new_value}"
        )

    logger.info(
        "Kamera sayısı: "
        f"{old_value} -> {new_value}"
    )


def set_archive_days(
    page: Page,
    archive_days: int,
) -> None:
    """
    Arşiv süresini gün cinsinden değiştirir.
    """
    if isinstance(archive_days, bool) or not isinstance(
        archive_days,
        int,
    ):
        raise ValueError(
            "archive_days integer olmalıdır."
        )

    if archive_days < 0:
        raise ValueError(
            "archive_days negatif olamaz."
        )

    archive_input = page.locator(
        '[id="archiveForm:vendor-and-archice-settings:'
        'archiveDays_input"]'
    )

    archive_input.wait_for(
        state="visible",
        timeout=10000,
    )

    old_value = archive_input.input_value()

    archive_input.fill(str(archive_days))
    archive_input.press("Tab")

    page.wait_for_timeout(1500)

    new_value = archive_input.input_value()

    if new_value != str(archive_days):
        raise RuntimeError(
            "Archive days değiştirilemedi. "
            f"Beklenen: {archive_days}, mevcut: {new_value}"
        )

    logger.info(
        "Archive days: "
        f"{old_value} -> {new_value}"
    )

SUPPORTED_RECORDING_PERCENTAGES = (
    0,
    10,
    20,
    30,
    40,
    50,
    60,
    70,
    80,
    90,
    100,
)

def set_recording_percentage(
    page: Page,
    recording_percentage: int,
) -> None:
    """
    Günlük kayıt yüzdesini Axxon Platform Calculator içindeki
    archivePercentInputEng alanı üzerinden ayarlar.

    Desteklenen değerler:
        0, 10, 20, 30, 40, 50,
        60, 70, 80, 90, 100

    Örnek:
        50  -> günün %50'sinde kayıt
        70  -> günün %70'inde kayıt
        100 -> sürekli kayıt
    """

    # --------------------------------------------------------
    # TYPE VALIDATION
    # --------------------------------------------------------

    if isinstance(recording_percentage, bool) or not isinstance(
        recording_percentage,
        int,
    ):
        raise ValueError(
            "recording_percentage integer olmalıdır."
        )

    # --------------------------------------------------------
    # SUPPORTED VALUE VALIDATION
    # --------------------------------------------------------

    if recording_percentage not in SUPPORTED_RECORDING_PERCENTAGES:
        raise ValueError(
            "recording_percentage şu değerlerden biri olmalıdır: "
            f"{SUPPORTED_RECORDING_PERCENTAGES}"
        )

    # --------------------------------------------------------
    # CALCULATOR SELECT ELEMENT
    # --------------------------------------------------------

    select_id = (
        "archiveForm:"
        "vendor-and-archice-settings:"
        "archivePercentInputEng_input"
    )

    select = page.locator(
        f'[id="{select_id}"]'
    )

    select.wait_for(
        state="attached",
        timeout=10000,
    )

    # --------------------------------------------------------
    # SİTENİN GERÇEKTEN DESTEKLEDİĞİ DEĞERLERİ KONTROL ET
    # --------------------------------------------------------

    options = select.locator(
        "option"
    )

    available_values = [
        options.nth(index).get_attribute(
            "value"
        )
        for index in range(
            options.count()
        )
    ]

    requested_value = str(
        recording_percentage
    )

    if requested_value not in available_values:
        raise RuntimeError(
            "Axxon Platform Calculator beklenen kayıt yüzdesini "
            "desteklemiyor. "
            f"İstenen: {recording_percentage}, "
            f"Site seçenekleri: {available_values}"
        )

    # --------------------------------------------------------
    # ESKİ DEĞER
    # --------------------------------------------------------

    old_value = select.input_value()

    # Zaten doğru değerdeyse tekrar AJAX tetikleme.
    if old_value == requested_value:
        logger.info(
            "Günlük kayıt yüzdesi zaten seçili: "
            f"{recording_percentage}%"
        )
        return

    # --------------------------------------------------------
    # YENİ DEĞERİ SEÇ
    # --------------------------------------------------------

    select.select_option(
        value=requested_value,
        force=True,
    )

    # PrimeFaces / JSF AJAX işleminin tamamlanmasını bekle.
    page.wait_for_timeout(
        1500
    )

    # AJAX sonrasında element yeniden render edilmiş olabilir.
    select = page.locator(
        f'[id="{select_id}"]'
    )

    select.wait_for(
        state="attached",
        timeout=10000,
    )

    new_value = select.input_value()

    # --------------------------------------------------------
    # DOĞRULAMA
    # --------------------------------------------------------

    if new_value != requested_value:
        raise RuntimeError(
            "Günlük kayıt yüzdesi değiştirilemedi. "
            f"Beklenen: {requested_value}%, "
            f"mevcut: {new_value}%"
        )

    logger.info(
        "Günlük kayıt yüzdesi: "
        f"{old_value}% -> {new_value}%"
    )


def _set_primefaces_select(
    page: Page,
    element_id: str,
    value: str,
    field_name: str,
) -> None:
    """
    PrimeFaces ui-selectOneMenu bileşeninin arkasındaki
    hidden <select> elementinin değerini değiştirir.
    """
    select = page.locator(
        f'[id="{element_id}"]'
    )

    select.wait_for(
        state="attached",
        timeout=10000,
    )

    options = select.locator("option")

    available_values = [
        options.nth(i).get_attribute("value")
        for i in range(options.count())
    ]

    if value not in available_values:
        raise ValueError(
            f"Geçersiz {field_name}: {value}. "
            f"Desteklenen değerler: {available_values}"
        )

    old_value = select.input_value()

    select.select_option(
        value=value,
        force=True,
    )

    page.wait_for_timeout(1200)

    # AJAX ile element yeniden render edilmiş olabilir.
    select = page.locator(
        f'[id="{element_id}"]'
    )

    new_value = select.input_value()

    if new_value != value:
        raise RuntimeError(
            f"{field_name} değiştirilemedi. "
            f"Beklenen: {value}, mevcut: {new_value}"
        )

    logger.info(
        f"{field_name}: {old_value} -> {new_value}"
    )


def set_resolution(
    page: Page,
    resolution: str,
) -> None:
    """
    İlk kamera grubunun ana stream çözünürlüğünü değiştirir.
    """
    _set_primefaces_select(
        page=page,
        element_id=(
            "cameraGroupForm:cameras:"
            "cameraGroupPanel:0:"
            "cameraRequestForm:"
            "resolutionInput_input"
        ),
        value=resolution,
        field_name="Resolution",
    )


def set_fps(
    page: Page,
    fps: int,
) -> None:
    """
    İlk kamera grubunun FPS değerini değiştirir.
    Calculator 1-60 FPS destekliyor.
    """
    if isinstance(fps, bool) or not isinstance(
        fps,
        int,
    ):
        raise ValueError(
            "fps integer olmalıdır."
        )

    if not 1 <= fps <= 60:
        raise ValueError(
            "fps 1 ile 60 arasında olmalıdır."
        )

    _set_primefaces_select(
        page=page,
        element_id=(
            "cameraGroupForm:cameras:"
            "cameraGroupPanel:0:"
            "cameraRequestForm:"
            "fpsInput_input"
        ),
        value=f"{fps}.0",
        field_name="FPS",
    )


def set_codec(
    page: Page,
    codec: str,
) -> None:
    """
    Codec değerini PrimeFaces'in görünür dropdown'ı
    üzerinden gerçek kullanıcı gibi seçer.
    """
    codec_mapping = {
        "H264": "H264",
        "H.264": "H264",
        "H265": "H265",
        "H.265": "H265",
        "MJPEG": "MjPEG",
        "MjPEG": "MjPEG",
    }

    normalized_codec = codec_mapping.get(codec)

    if normalized_codec is None:
        raise ValueError(
            "Desteklenmeyen codec. "
            "H264, H265 veya MjPEG kullanın."
        )

    select_id = (
        "cameraGroupForm:cameras:"
        "cameraGroupPanel:0:"
        "cameraRequestForm:"
        "codecInput_input"
    )

    label_id = (
        "cameraGroupForm:cameras:"
        "cameraGroupPanel:0:"
        "cameraRequestForm:"
        "codecInput_label"
    )

    panel_id = (
        "cameraGroupForm:cameras:"
        "cameraGroupPanel:0:"
        "cameraRequestForm:"
        "codecInput_panel"
    )

    select = page.locator(
        f'[id="{select_id}"]'
    )

    label = page.locator(
        f'[id="{label_id}"]'
    )

    panel = page.locator(
        f'[id="{panel_id}"]'
    )

    select.wait_for(
        state="attached",
        timeout=10000,
    )

    label.wait_for(
        state="visible",
        timeout=10000,
    )

    old_value = select.input_value()

    if old_value == normalized_codec:
        logger.info(
            f"Codec zaten seçili: {normalized_codec}"
        )
        return

    label.click()

    panel.wait_for(
        state="visible",
        timeout=5000,
    )

    option = panel.locator(
        "li.ui-selectonemenu-item"
    ).filter(
        has_text=normalized_codec
    ).first

    option.wait_for(
        state="visible",
        timeout=5000,
    )

    option.click()

    page.wait_for_timeout(1800)

    select = page.locator(
        f'[id="{select_id}"]'
    )

    new_value = select.input_value()

    if new_value != normalized_codec:
        raise RuntimeError(
            "Codec değiştirilemedi. "
            f"Beklenen: {normalized_codec}, "
            f"mevcut: {new_value}"
        )

    logger.info(
        f"Codec: {old_value} -> {new_value}"
    )


def get_site_bitrate(
    page: Page,
) -> float:
    """
    Resolution/FPS/Codec değerlerine göre calculator'ın
    otomatik belirlediği tek kamera bitrate değerini okur.

    Bu fonksiyon bitrate'i DEĞİŞTİRMEZ.
    """
    bitrate_input = page.locator(
        '[id="cameraGroupForm:cameras:'
        'cameraGroupPanel:0:'
        'cameraRequestForm:'
        'cbrInput_input"]'
    )

    bitrate_input.wait_for(
        state="visible",
        timeout=10000,
    )

    value = (
        bitrate_input
        .input_value()
        .strip()
        .replace(",", ".")
    )

    try:
        bitrate = float(value)
    except ValueError as error:
        raise RuntimeError(
            f"Site bitrate değeri okunamadı: {value!r}"
        ) from error

    logger.info(
        "Site tarafından hesaplanan bitrate: "
        f"{bitrate:.2f} Mbit/s"
    )

    return bitrate


# ============================================================
# SONUÇ PARSE
# ============================================================

def parse_first_result(page: Page) -> dict:
    """
    Recommended Platforms tablosundaki ilk platformu
    okuyup temiz bir Python dictionary olarak döndürür.
    """
    first_row = page.locator(
        '[id="results:results-form:recommended-platforms"] '
        'tr[data-ri="0"]'
    ).first

    first_row.wait_for(
        state="visible",
        timeout=15000,
    )

    cells = first_row.locator("td")

    if cells.count() < 7:
        raise RuntimeError(
            "Platform sonucu beklenen formatta değil."
        )

    values = []

    for index in range(7):
        text = (
            cells.nth(index)
            .inner_text()
            .strip()
            .replace("\n", " ")
        )

        text = " ".join(text.split())
        values.append(text)

    # Archive örneği:
    # 11.59 TB (HDD marked capacity 12.75 TB)
    archive_match = re.search(
        r"([\d.]+)\s*TB.*?([\d.]+)\s*TB",
        values[4],
    )

    if not archive_match:
        raise RuntimeError(
            f"Archive sonucu parse edilemedi: {values[4]}"
        )

    archive_tb = float(
        archive_match.group(1)
    )

    hdd_capacity_tb = float(
        archive_match.group(2)
    )

    recording_match = re.search(
        r"([\d.]+)",
        values[5],
    )

    if not recording_match:
        raise RuntimeError(
            f"Recording rate parse edilemedi: {values[5]}"
        )

    recording_mbps = float(
        recording_match.group(1)
    )

    lan_match = re.search(
        r"([\d.]+)\s*/\s*([\d.]+)",
        values[6],
    )

    if not lan_match:
        raise RuntimeError(
            f"LAN sonucu parse edilemedi: {values[6]}"
        )

    lan_in_mbps = float(
        lan_match.group(1)
    )

    lan_out_mbps = float(
        lan_match.group(2)
    )

    return {
        "servers": int(values[0]),
        "cpu": values[1],
        "cpu_load": values[2],
        "ram": values[3],
        "archive_tb": archive_tb,
        "hdd_capacity_tb": hdd_capacity_tb,
        "recording_mbps": recording_mbps,
        "lan_in_mbps": lan_in_mbps,
        "lan_out_mbps": lan_out_mbps,
    }


# ============================================================
# ANA HESAPLAMA
# ============================================================

def calculate_platform(
    camera_count: int,
    archive_days: int,
    resolution: str,
    fps: int,
    codec: str,
    bitrate_mbps: float | None = None,
    software: str = "Axxon One (x64)",
    calculation_type: str = "Server",
    recording_percentage: int = 50,
) -> dict:
    """
    AxxonSoft Platform Calculator'ı headless browser ile çalıştırır
    ve ilk önerilen platformu dictionary olarak döndürür.

    Önemli:
    - bitrate_mbps yalnızca eski çağrılar bozulmasın diye tutulur.
    - Manuel bitrate hiçbir zaman siteye yazılmaz.
    - Bitrate her zaman calculator'ın Resolution/FPS/Codec'e göre
      kendi hesapladığı değer olarak okunur.
    - recording_percentage 0-100 arasında ayarlanabilir.
    """
    total_start = time.perf_counter()

    _log_system(
        "Axxon Platform Calculator başlatılıyor."
    )

    if bitrate_mbps is not None:
        logger.info(
            "Manuel bitrate parametresi yok sayıldı; "
            "AxxonSoft Calculator'ın hesapladığı bitrate kullanılacak."
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True
        )

        try:
            page = browser.new_page(
                viewport={
                    "width": 1600,
                    "height": 1000,
                }
            )

            page.set_default_timeout(10000)

            # ----------------------------------------------------
            # SAYFA YÜKLEME
            # ----------------------------------------------------
            load_start = time.perf_counter()

            for attempt in range(3):
                try:
                    page.goto(
                        CALCULATOR_URL,
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )
                    break

                except PlaywrightError as error:
                    _log_warning(
                        "Calculator bağlantı denemesi "
                        f"{attempt + 1} başarısız: {error}"
                    )

                    if attempt == 2:
                        raise RuntimeError(
                            "Axxon Platform Calculator'a "
                            "3 denemede bağlanılamadı."
                        ) from error

                    page.wait_for_timeout(2000)

            logger.perf(
                "Calculator sayfa yükleme süresi: "
                f"{time.perf_counter() - load_start:.3f}s"
            )

            page.wait_for_timeout(1500)

            dismiss_popups(page)
            wait_until_calculator_ready(page)

            # ----------------------------------------------------
            # PARAMETRELER
            # ----------------------------------------------------
            input_start = time.perf_counter()

            select_software(
                page,
                software,
            )

            select_calculation_type(
                page,
                calculation_type,
            )

            set_camera_count(
                page,
                camera_count,
            )

            set_archive_days(
                page,
                archive_days,
            )

            set_recording_percentage(
                page,
                recording_percentage,
            )

            set_resolution(
                page,
                resolution,
            )

            set_fps(
                page,
                fps,
            )

            set_codec(
                page,
                codec,
            )

            # Resolution/FPS/Codec değişikliklerinden sonra
            # sitenin bitrate ve sonuçları yeniden hesaplamasını bekle.
            page.wait_for_timeout(2500)

            site_bitrate = get_site_bitrate(
                page
            )

            logger.perf(
                "Calculator parametre giriş süresi: "
                f"{time.perf_counter() - input_start:.3f}s"
            )

            # ----------------------------------------------------
            # SONUÇ
            # ----------------------------------------------------
            result_start = time.perf_counter()

            result = parse_first_result(
                page
            )

            result["camera_bitrate_mbps"] = site_bitrate
            result["recording_percentage"] = recording_percentage

            logger.perf(
                "Calculator sonuç okuma süresi: "
                f"{time.perf_counter() - result_start:.3f}s"
            )

            _log_system(
                "Platform hesabı başarıyla tamamlandı."
            )

            return result

        except Exception as error:
            logger.error(
                f"Platform hesabı başarısız: {error}"
            )
            raise

        finally:
            browser.close()

            logger.perf(
                "Platform Calculator toplam çalışma süresi: "
                f"{time.perf_counter() - total_start:.3f}s"
            )


# ============================================================
# MANUEL TEST
# ============================================================

if __name__ == "__main__":
    try:
        result = calculate_platform(
            camera_count=10,
            archive_days=30,
            resolution="1920x1080",
            fps=25,
            codec="H265",
            recording_percentage=70,
        )

        _log_system("CALCULATOR SONUCU")

        for key, value in result.items():
            logger.info(
                f"{key}: {value}"
            )

    except Exception as error:
        logger.error(
            f"Test başarısız: {error}"
        )
