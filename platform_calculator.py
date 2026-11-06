# Axxon Platform Calculator'ın formülü çözülmeli veya bir şekilde kaynak kodu elde edilmeli.
# Veya alternatif olarak yapoay zekaya o web sitesini kullandırmanın bir yolu bulunmalı.

import re

from playwright.sync_api import (
    sync_playwright,
    Page,
    Frame,
    Error as PlaywrightError,
)


CALCULATOR_URL = (
    "https://sale.axxonsoft.com/calc/calculator.jsf"
)


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
                button.click(
                    timeout=5000
                )

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

                print(
                    f"Accept geçildi ({clicked_count})."
                )

                page.wait_for_timeout(
                    700
                )

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

    page.wait_for_timeout(
        800
    )

    print(
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

    page.wait_for_timeout(
        800
    )

    print(
        f"Calculation type seçildi: "
        f"{calculation_type}"
    )


def set_camera_count(
    page: Page,
    camera_count: int,
) -> None:
    """
    İlk kamera grubunun kamera sayısını değiştirir.
    """

    if not isinstance(camera_count, int):
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

    camera_input.fill(
        str(camera_count)
    )

    # PrimeFaces değişikliği çoğu zaman blur/change
    # olayında gönderdiği için input'tan çıkıyoruz.
    camera_input.press(
        "Tab"
    )

    page.wait_for_timeout(
        1500
    )

    new_value = camera_input.input_value()

    print(
        f"Kamera sayısı: "
        f"{old_value} -> {new_value}"
    )


def set_archive_days(
    page: Page,
    archive_days: int,
) -> None:
    """
    Arşiv süresini gün cinsinden değiştirir.
    """

    if not isinstance(archive_days, int):
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

    archive_input.fill(
        str(archive_days)
    )

    archive_input.press(
        "Tab"
    )

    page.wait_for_timeout(
        1500
    )

    new_value = archive_input.input_value()

    print(
        f"Archive days: "
        f"{old_value} -> {new_value}"
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

    select_option() input/change eventlerini de tetiklediği için
    JSF/PrimeFaces hesaplaması güncellenir.
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

    page.wait_for_timeout(
        1200
    )

    new_value = select.input_value()

    if new_value != value:
        raise RuntimeError(
            f"{field_name} değiştirilemedi. "
            f"Beklenen: {value}, mevcut: {new_value}"
        )

    print(
        f"{field_name}: {old_value} -> {new_value}"
    )


def set_resolution(
    page: Page,
    resolution: str,
) -> None:
    """
    İlk kamera grubunun ana stream çözünürlüğünü değiştirir.

    Örnek:
        1920x1080
        2688x1520
        3840x2160
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

    if not isinstance(fps, int):
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

    # Zaten istenen codec seçiliyse tekrar işlem yapma.
    if old_value == normalized_codec:
        print(
            f"Codec zaten seçili: {normalized_codec}"
        )
        return

    # PrimeFaces dropdown'ını gerçek kullanıcı gibi aç.
    label.click()

    panel.wait_for(
        state="visible",
        timeout=5000,
    )

    # Açılan listedeki gerçek seçeneği tıkla.
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

    # PrimeFaces / JSF AJAX işleminin tamamlanması için.
    page.wait_for_timeout(
        1800
    )

    # Ajax sırasında widget yeniden render edilmiş olabilir,
    # bu yüzden locator'ı yeniden alıyoruz.
    select = page.locator(
        f'[id="{select_id}"]'
    )

    new_value = select.input_value()

    if new_value != normalized_codec:
        raise RuntimeError(
            f"Codec değiştirilemedi. "
            f"Beklenen: {normalized_codec}, "
            f"mevcut: {new_value}"
        )

    print(
        f"Codec: {old_value} -> {new_value}"
    )


def set_bitrate(
    page: Page,
    bitrate_mbps: float,
) -> None:
    """
    İlk kamera grubunun bitrate değerini Mbit/s olarak değiştirir.
    PrimeFaces input olduğu için gerçek klavye girişini taklit eder.
    """

    if not isinstance(
        bitrate_mbps,
        (int, float),
    ):
        raise ValueError(
            "bitrate_mbps sayı olmalıdır."
        )

    if bitrate_mbps <= 0:
        raise ValueError(
            "bitrate_mbps 0'dan büyük olmalıdır."
        )

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

    old_value = bitrate_input.input_value()

    

    # Gerçek kullanıcı gibi alanı seçiyoruz.
    bitrate_input.click()

    bitrate_input.press(
        "Control+A"
    )

    bitrate_input.type(
        str(bitrate_mbps),
        delay=100,
    )

    # AJAX çalışmadan hemen önce gerçekten ne yazıldığını görelim.
    typed_value = bitrate_input.input_value()


    # PrimeFaces change/blur olayını tetikle.
    bitrate_input.press(
        "Tab"
    )

    page.wait_for_timeout(
        2000
    )

    final_value = bitrate_input.input_value()

    print(
    f"Bitrate: {old_value} -> "
    f"{final_value} Mbit/s"
)

# ============================================================
# SONUÇ KONTROLÜ
# ============================================================
def inspect_stream_widgets(page: Page) -> None:
    """
    İlk kamera grubunun ana stream'ine ait
    Resolution, FPS ve Codec PrimeFaces bileşenlerini inceler.

    Amaç:
        - Gerçek element ID'lerini bulmak
        - Hidden select/input yapılarını görmek
        - Kullanılabilecek option value'larını çıkarmak
    """

    print("\n")
    print("=" * 70)
    print("STREAM WIDGET ANALİZİ")
    print("=" * 70)

    widget_names = [
        "resolutionInput",
        "fpsInput",
        "codecInput",
    ]

    for widget_name in widget_names:

        print("\n")
        print("#" * 70)
        print(widget_name)
        print("#" * 70)

        # Sadece ilk kamera grubunun ANA stream'i.
        # childCameras altındaki ikinci stream'i almıyoruz.
        elements = page.locator(
            f'[id*="cameraGroupPanel:0:cameraRequestForm:{widget_name}"]'
        )

        print(
            f"Bulunan element sayısı: {elements.count()}"
        )

        for index in range(elements.count()):
            element = elements.nth(index)

            try:
                tag = element.evaluate(
                    "(el) => el.tagName.toLowerCase()"
                )

                element_id = element.get_attribute("id")
                name = element.get_attribute("name")
                element_type = element.get_attribute("type")
                class_name = element.get_attribute("class")
                role = element.get_attribute("role")

                visible = element.is_visible()

                try:
                    value = element.input_value()
                except Exception:
                    value = None

                try:
                    text = element.inner_text().strip()
                except Exception:
                    text = ""

                print("\n" + "-" * 70)
                print(f"INDEX   : {index}")
                print(f"TAG     : {tag}")
                print(f"ID      : {element_id}")
                print(f"NAME    : {name}")
                print(f"TYPE    : {element_type}")
                print(f"CLASS   : {class_name}")
                print(f"ROLE    : {role}")
                print(f"VISIBLE : {visible}")
                print(f"VALUE   : {value}")
                print(f"TEXT    : {text}")

                # Eğer gerçek bir <select> ise option'ları da çıkar.
                if tag == "select":
                    options = element.locator("option")

                    print(
                        f"OPTION SAYISI: {options.count()}"
                    )

                    for option_index in range(
                        options.count()
                    ):
                        option = options.nth(
                            option_index
                        )

                        option_text = (
                            option.inner_text().strip()
                        )

                        option_value = (
                            option.get_attribute("value")
                        )

                        print(
                            f"    [{option_index}] "
                            f"text={option_text!r} "
                            f"value={option_value!r}"
                        )

            except PlaywrightError:
                continue

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

        # Birden fazla boşluğu tek boşluğa indir.
        text = " ".join(
            text.split()
        )

        values.append(text)

    # --------------------------------------------------------
    # Archive
    # Örnek:
    # 11.59 TB (HDD marked capacity 12.75 TB)
    # --------------------------------------------------------

    archive_match = re.search(
        r"([\d.]+)\s*TB.*?"
        r"([\d.]+)\s*TB",
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

    # --------------------------------------------------------
    # Recording
    # Örnek:
    # 50.0 Mbit/s
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # LAN
    # Örnek:
    # 64.9 / 14.9 Mbit/s
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Temiz sonuç
    # --------------------------------------------------------

    result = {
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

    return result

def calculate_platform(
    camera_count: int,
    archive_days: int,
    resolution: str,
    fps: int,
    codec: str,
    bitrate_mbps: float | None = None,
    software: str = "Axxon One (x64)",
    calculation_type: str = "Server",
) -> dict:
    """
    AxxonSoft Platform Calculator'ı headless browser ile
    arka planda kullanır ve ilk önerilen platformu döndürür.

    Kullanıcı browser penceresi görmez.

    Bitrate None verilirse calculator'ın mevcut/default
    bitrate değeri kullanılır.
    """

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

            page.set_default_timeout(
                10000
            )

            print(
                "Axxon Platform Calculator çalıştırılıyor..."
            )

            # ------------------------------------------------
            # SAYFAYA BAĞLAN
            # ------------------------------------------------

            for attempt in range(3):
                try:
                    page.goto(
                        CALCULATOR_URL,
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )

                    break

                except PlaywrightError as error:

                    print(
                        f"Bağlantı denemesi "
                        f"{attempt + 1} başarısız: "
                        f"{error}"
                    )

                    if attempt == 2:
                        raise RuntimeError(
                            "Axxon Platform Calculator'a "
                            "3 denemede bağlanılamadı."
                        ) from error

                    page.wait_for_timeout(
                        2000
                    )

            # ------------------------------------------------
            # SAYFAYI HAZIRLA
            # ------------------------------------------------

            page.wait_for_timeout(
                1500
            )

            dismiss_popups(
                page
            )

            wait_until_calculator_ready(
                page
            )

            # ------------------------------------------------
            # SOFTWARE
            # ------------------------------------------------

            select_software(
                page,
                software,
            )

            # ------------------------------------------------
            # CALCULATION TYPE
            # ------------------------------------------------

            select_calculation_type(
                page,
                calculation_type,
            )

            # ------------------------------------------------
            # CAMERA COUNT
            # ------------------------------------------------

            set_camera_count(
                page,
                camera_count,
            )

            # ------------------------------------------------
            # ARCHIVE DAYS
            # ------------------------------------------------

            set_archive_days(
                page,
                archive_days,
            )

            # ------------------------------------------------
            # RESOLUTION
            # ------------------------------------------------

            set_resolution(
                page,
                resolution,
            )

            # ------------------------------------------------
            # FPS
            # ------------------------------------------------

            set_fps(
                page,
                fps,
            )

            # ------------------------------------------------
            # CODEC
            # ------------------------------------------------

            set_codec(
                page,
                codec,
            )

            # ------------------------------------------------
            # BITRATE
            # ------------------------------------------------

            if bitrate_mbps is not None:

                set_bitrate(
                    page,
                    bitrate_mbps,
                )

            else:

                print(
                    "Bitrate belirtilmedi; "
                    "calculator varsayılan değeri kullanılacak."
                )

            # ------------------------------------------------
            # SONUÇLARIN GÜNCELLENMESİNİ BEKLE
            # ------------------------------------------------

            page.wait_for_timeout(
                2500
            )

            # ------------------------------------------------
            # SONUCU OKU
            # ------------------------------------------------

            result = parse_first_result(
                page
            )

            return result

        finally:
            browser.close()
# ============================================================
# TEST
# ============================================================

def test_calculator_inputs() -> None:
    """
    Headless calculator üzerinde ilk otomatik
    input testini gerçekleştirir.
    """

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

            page.set_default_timeout(
                10000
            )

            print(
                "Calculator'a bağlanılıyor..."
            )

            page.goto(
                CALCULATOR_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            print(
                "Bağlantı başarılı."
            )

            page.wait_for_timeout(
                1500
            )

            dismiss_popups(
                page
            )

            wait_until_calculator_ready(
                page
            )

            print(
                "Calculator hazır."
            )

            # --------------------------------------------
            # TEST PARAMETRELERİ
            # --------------------------------------------

            select_software(
                page,
                "Axxon One (x64)",
            )

            select_calculation_type(
                page,
                "Server",
            )

            set_camera_count(
                page,
                20,
            )

            set_archive_days(
                page,
                45,
            )
            set_resolution(
                page,
                "1920x1080",
            )

            set_fps(
                page,
                15,
            )

            set_codec(
                page,
                "H264",
            )

            # Bitrate'i en son değiştiriyoruz.
            # Resolution/FPS/Codec değişiklikleri bitrate'i
            # otomatik etkileyebileceği için bu sıra önemli.
            set_bitrate(
                page,
                2.5,
            )
            # Hesaplamanın güncellenmesi için kısa bekleme.
            page.wait_for_timeout(
                2000
            )

            print_first_result(
                page
            )

        finally:
            browser.close()


if __name__ == "__main__":

    result = calculate_platform(
        camera_count= 10,
        archive_days=30,
        resolution="1920x1080",
        fps=25,
        codec="H265",
        bitrate_mbps=3.33,
    )

    print("\n")
    print("=" * 60)
    print("CALCULATOR SONUCU")
    print("=" * 60)

    for key, value in result.items():
        print(
            f"{key}: {value}"
        )