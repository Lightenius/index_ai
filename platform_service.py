from platform_calculator import calculate_platform
from platform_matrix import normalize_platform_parameters


def get_platform_recommendation(
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
    Kullanıcıdan / AI'dan gelen değerleri önce
    platform_matrix üzerinden normalize eder.

    Daha sonra Axxon Platform Calculator'a gönderir.
    """

    parameters = normalize_platform_parameters(
        camera_count=camera_count,
        archive_days=archive_days,
        resolution=resolution,
        fps=fps,
        codec=codec,
        bitrate_mbps=bitrate_mbps,
        software=software,
        calculation_type=calculation_type,
    )

    result = calculate_platform(
        camera_count=parameters["camera_count"],
        archive_days=parameters["archive_days"],
        resolution=parameters["resolution"],
        fps=parameters["fps"],
        codec=parameters["codec"],
        bitrate_mbps=parameters["bitrate_mbps"],
        software=parameters["software"],
        calculation_type=parameters["calculation_type"],
    )

    return result


def format_platform_result(
    result: dict,
) -> str:
    """
    Calculator sonucunu kullanıcıya okunabilir
    metin olarak döndürür.
    """

    return (
        "Önerilen AxxonSoft platformu:\n\n"
        f"Server sayısı: {result['servers']}\n"
        f"CPU: {result['cpu']}\n"
        f"CPU yükü: {result['cpu_load']}\n"
        f"RAM: {result['ram']}\n"
        f"Arşiv kapasitesi: {result['archive_tb']} TB\n"
        f"HDD kapasitesi: {result['hdd_capacity_tb']} TB\n"
        f"Kayıt trafiği: {result['recording_mbps']} Mbit/s\n"
        f"LAN giriş: {result['lan_in_mbps']} Mbit/s\n"
        f"LAN çıkış: {result['lan_out_mbps']} Mbit/s"
    )


def handle_platform_request(
    camera_count: int,
    archive_days: int,
    resolution: str | None = None,
    fps: int | None = None,
    codec: str | None = None,
    bitrate_mbps: float | None = None,
    software: str | None = None,
    calculation_type: str | None = None,
) -> str:
    """
    Input handler / AI tarafından çağrılacak ana fonksiyon.
    """

    result = get_platform_recommendation(
        camera_count=camera_count,
        archive_days=archive_days,
        resolution=resolution,
        fps=fps,
        codec=codec,
        bitrate_mbps=bitrate_mbps,
        software=software,
        calculation_type=calculation_type,
    )

    return format_platform_result(
        result
    )


if __name__ == "__main__":

    response = handle_platform_request(
        camera_count=10,
        archive_days=30,

        # Burada özellikle kullanıcı dili kullanıyoruz.
        resolution="4 MP",
        fps=25,
        codec="H.265",
        bitrate_mbps=3.33,
        software="Axxon One",
        calculation_type="server",
    )

    print("\n")
    print(response)