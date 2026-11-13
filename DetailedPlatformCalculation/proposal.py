"""Build and render policy-checked infrastructure proposals."""

from __future__ import annotations

import math
import re
from typing import Any

import plat_calc


def _policy_integer(specification: str, pattern: str, label: str) -> int:
    match = re.search(pattern, specification, flags=re.IGNORECASE)
    if match is None:
        raise ValueError(f"specification.ai does not define {label}.")
    return int(match.group(1))


def _ram_gigabytes(value: str | None) -> float | None:
    if not value:
        return None
    amounts = re.findall(r"(\d+(?:\.\d+)?)\s*GB\b", value, flags=re.IGNORECASE)
    if not amounts:
        return None
    module_match = re.search(
        r"(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*GB\b",
        value,
        flags=re.IGNORECASE,
    )
    if module_match:
        return float(module_match.group(1)) * float(module_match.group(2))
    return sum(float(amount) for amount in amounts)


def _has_two_eight_gb_modules(value: str) -> bool:
    match = re.search(
        r"(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*GB\b",
        value,
        flags=re.IGNORECASE,
    )
    return (
        match is not None
        and int(match.group(1)) >= 2
        and float(match.group(2)) >= 8
    )


def _value_after_label(
    sheets: list[tuple[str, list[list[str]]]],
    label: str,
) -> str | None:
    target = label.casefold()
    for _, rows in sheets:
        for row_index, row in enumerate(rows):
            for column_index, cell in enumerate(row):
                if cell.strip().casefold() != target:
                    continue
                if not any(value.strip() for value in row[column_index + 1 :]):
                    for next_row in rows[row_index + 1 :]:
                        if column_index < len(next_row) and next_row[column_index].strip():
                            return next_row[column_index].strip()
                for next_row in rows[row_index + 1 :]:
                    for value in next_row[column_index:]:
                        if value.strip():
                            return value.strip()
    return None


def _workbook_storage(
    sheets: list[tuple[str, list[list[str]]]],
    recommendations: list[dict[str, str]],
) -> dict[str, Any]:
    archive_result = _value_after_label(sheets, "Total video archive size") or ""
    required_match = re.search(
        r"([\d,]+(?:\.\d+)?)\s*TB",
        archive_result,
        flags=re.IGNORECASE,
    )
    marked_match = re.search(
        r"HDD marked capacity\s*([\d,]+(?:\.\d+)?)\s*TB",
        archive_result,
        flags=re.IGNORECASE,
    )
    required_tb = float(required_match.group(1).replace(",", "")) if required_match else None
    marked_tb = float(marked_match.group(1).replace(",", "")) if marked_match else None
    raid_level = _value_after_label(sheets, "RAID level")
    disk_size_value = _value_after_label(sheets, "Disk size, TB")
    max_group_value = _value_after_label(
        sheets, "Maximum number of disks per RAID group"
    )
    archive_days = _value_after_label(sheets, "Archive, days")
    recording_percentage = _value_after_label(sheets, "% of day")

    storage_options: list[tuple[str, str]] = []
    for recommendation in recommendations:
        storage_text = recommendation.get("server_storage_configuration", "")
        archive_storage_match = re.search(
            r"Archive size:\s*([\d,]+(?:\.\d+)?)\s*TB",
            storage_text,
            flags=re.IGNORECASE,
        )
        hdd_line = next(
            (
                line.strip()
                for line in storage_text.splitlines()
                if re.search(r"\bHDD\s*:", line, flags=re.IGNORECASE)
            ),
            "",
        )
        if hdd_line and not any(option == hdd_line for option, _ in storage_options):
            storage_options.append(
                (
                    hdd_line,
                    archive_storage_match.group(1).replace(",", "")
                    if archive_storage_match
                    else "",
                )
            )

    configured_raid_number_match = re.search(r"\d+", raid_level or "")
    configured_raid_number = (
        configured_raid_number_match.group()
        if configured_raid_number_match
        else None
    )
    selected_option = next(
        (
            option
            for option in storage_options
            if configured_raid_number
            and re.search(
                rf"\bRAID\s*{re.escape(configured_raid_number)}\b",
                option[0],
                flags=re.IGNORECASE,
            )
        ),
        storage_options[0] if storage_options else ("", ""),
    )
    global_storage_configuration, archive_size_text = selected_option
    recommended_archive_tb = (
        float(archive_size_text)
        if archive_size_text
        else None
    )
    disk_match = re.search(
        r"HDD:\s*(\d+)\s*x\s*([\d,]+(?:\.\d+)?)\s*TB"
        r"\s*\((\d+)\s*x\s*RAID\s*(\d+)\)",
        global_storage_configuration,
        flags=re.IGNORECASE,
    )
    drive_count = int(disk_match.group(1)) if disk_match else None
    drive_size_tb = (
        float(disk_match.group(2).replace(",", "")) if disk_match else None
    )
    raid_group_count = int(disk_match.group(3)) if disk_match else None
    storage_raid_number = int(disk_match.group(4)) if disk_match else None
    raw_tb = (
        drive_count * drive_size_tb
        if drive_count is not None and drive_size_tb is not None
        else None
    )

    configured_disk_tb = drive_size_tb
    if configured_disk_tb is None and disk_size_value:
        size_match = re.search(r"[\d,]+(?:\.\d+)?", disk_size_value)
        if size_match:
            configured_disk_tb = float(size_match.group().replace(",", ""))
    max_group_size: int | None = None
    if max_group_value:
        group_match = re.search(r"\d+", max_group_value)
        if group_match:
            max_group_size = int(group_match.group())

    usable_tb: float | None = None
    usable_note = (
        "Workbook verileri kullanılabilir kapasiteyi hesaplamak için yeterli değildir."
    )
    selected_raid = (
        f"RAID {storage_raid_number}" if storage_raid_number is not None else None
    )
    normalized_raid = (selected_raid or raid_level or "").upper().replace(" ", "_")
    if (
        normalized_raid == "RAID_5"
        and drive_count is not None
        and raid_group_count is not None
        and drive_size_tb is not None
    ):
        group_sizes = _balanced_counts(
            drive_count,
            raid_group_count,
        )
        valid_layout = all(size >= 3 for size in group_sizes) and (
            max_group_size is None
            or all(size <= max_group_size for size in group_sizes)
        )
        if valid_layout:
            usable_tb = (
                drive_count - raid_group_count
            ) * drive_size_tb
            usable_note = (
                f"Nominal RAID 5 kapasitesi, global RAID düzenindeki "
                f"{raid_group_count} group için birer parity diski düşülerek "
                "hesaplanmıştır; biçimlendirme ve dosya sistemi kayıpları dahil değildir."
            )
        else:
            usable_note = (
                "Seçilen global Recommended platforms depolama yapılandırması geçerli "
                "bir RAID 5 disk düzeni belirtmediğinden kullanılabilir kapasite "
                "doğrulanamamıştır."
            )

    return {
        "archive_result": archive_result,
        "required_tb": required_tb,
        "marked_tb": marked_tb,
        "marked_tb_total": marked_tb,
        "raid_level": raid_level or "Unspecified in workbook",
        "recommended_raid_level": selected_raid or raid_level or "Unspecified in workbook",
        "raid_configurations": [option for option, _ in storage_options],
        "disk_size_tb": configured_disk_tb,
        "max_group_size": max_group_size,
        "archive_days": archive_days,
        "recording_percentage": recording_percentage,
        "drive_count": drive_count,
        "drive_size_tb": drive_size_tb,
        "raid_group_count": raid_group_count,
        "raw_tb": raw_tb,
        "usable_tb": usable_tb,
        "usable_note": usable_note,
        "storage_configuration_global": global_storage_configuration,
        "recommended_archive_tb": recommended_archive_tb,
        "storage_source": "Recommended platforms table (selected independently of processor)",
    }


def _gpu_recommendations(
    sheets: list[tuple[str, list[list[str]]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    models: dict[str, int] = {}
    workloads: list[dict[str, Any]] = []
    for _, rows in sheets:
        for row_index, row in enumerate(rows):
            if any(cell.strip().casefold() == "gpu model" for cell in row):
                for candidate_row in rows[row_index + 1 :]:
                    candidate = next(
                        (cell.strip() for cell in candidate_row if cell.strip()),
                        "",
                    )
                    match = re.match(r"(\d+)\s*x\s*(.+)", candidate, re.IGNORECASE)
                    if match:
                        model_name = match.group(2).strip()
                        models[model_name] = max(
                            models.get(model_name, 0), int(match.group(1))
                        )

            normalized = [cell.strip().casefold() for cell in row]
            if "detector" not in normalized or "number of detectors" not in normalized:
                continue
            detector_column = normalized.index("detector")
            count_column = normalized.index("number of detectors")
            for workload_row in rows[row_index + 1 :]:
                if len(workload_row) <= max(detector_column, count_column):
                    continue
                detector_name = workload_row[detector_column].strip()
                if not detector_name or detector_name.casefold() == "total:":
                    break
                try:
                    count = int(float(workload_row[count_column]))
                except ValueError:
                    continue
                workloads.append({"name": detector_name, "count": count})
            break
    return (
        [{"model": model, "count": count} for model, count in models.items()],
        workloads,
    )


def _weakest_platform(
    recommendations: list[dict[str, str]],
) -> tuple[dict[str, str], list[dict[str, str]]]:
    eligible_recommendations = [
        item
        for item in recommendations
        if re.search(
            r"\bIntel\s+(?:Xeon\s+(?:Silver|Gold)\b|Core\s+Ultra\b)",
            item.get("processor", ""),
            flags=re.IGNORECASE,
        )
    ]
    if not eligible_recommendations:
        raise ValueError(
            "The calculator workbook has no recommended processor from the "
            "allowed Intel Xeon Silver, Intel Core Ultra, or Intel Xeon Gold lines."
        )

    loads: list[tuple[float, int, dict[str, str]]] = []
    for index, recommendation in enumerate(eligible_recommendations):
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)",
            recommendation.get("server_cpu_load", ""),
        )
        if match is None:
            raise ValueError(
                "Cannot select the weakest recording-server processor: "
                f"CPU-load range is missing for {recommendation['processor']}."
            )
        if float(match.group(2)) <= 0:
            raise ValueError(
                "The calculator reports a zero CPU-load recommendation for "
                f"{recommendation['processor']}; a nonzero CPU recommendation is required."
            )
        loads.append((float(match.group(2)), index, recommendation))
    selected = max(loads, key=lambda item: (item[0], -item[1]))[2]
    return selected, [
        item for item in eligible_recommendations if item is not selected
    ]


def _balanced_counts(total: int, count: int) -> list[int]:
    quotient, remainder = divmod(total, count)
    return [quotient + (1 if index < remainder else 0) for index in range(count)]


def _allocate_groups(
    servers: list[dict[str, Any]],
    groups: list[dict[str, Any]],
) -> None:
    group_index = 0
    group_remaining = groups[0]["camera_count"] if groups else 0
    for server in servers:
        remaining = server["camera_count"]
        allocations: list[dict[str, Any]] = []
        while remaining:
            while group_index < len(groups) and group_remaining == 0:
                group_index += 1
                if group_index < len(groups):
                    group_remaining = groups[group_index]["camera_count"]
            if group_index >= len(groups):
                raise ValueError("Source camera groups do not match the total camera count.")
            amount = min(remaining, group_remaining)
            allocations.append(
                {
                    "group_number": group_index + 1,
                    "group_name": groups[group_index].get(
                        "name", f"Group {group_index + 1}"
                    ),
                    "camera_count": amount,
                }
            )
            remaining -= amount
            group_remaining -= amount
        server["camera_groups"] = allocations


def build_proposal(
    specification: str,
    groups: list[dict[str, Any]],
    recommendations: list[dict[str, str]],
    sheets: list[tuple[str, list[list[str]]]],
    configuration: dict[str, Any],
    specification_name: str = "specification.ai",
    facility_name: str = "",
) -> dict[str, Any]:
    if not specification.strip():
        raise ValueError("The loaded specification.ai file is empty.")
    if not groups:
        raise ValueError("The calculator configuration contains no camera groups.")

    max_cameras = _policy_integer(
        specification,
        r"no more than\s+(\d+)\s+cameras",
        "the recording-server camera limit",
    )
    minimum_ram = _policy_integer(
        specification,
        r"at least\s+(\d+)\s*GB\s+of\s+RAM",
        "the per-server RAM minimum",
    )
    vms_minimum_ram = _policy_integer(
        specification,
        r"VMS servers must have at least\s+(\d+)\s*GB\s+RAM",
        "the VMS RAM minimum",
    )
    total_cameras = sum(group["camera_count"] for group in groups)
    recording_count = max(1, math.ceil(total_cameras / max_cameras))
    recording_servers = [
        {
            "server_number": index + 1,
            "camera_count": count,
            "processor": "",
            "processor_cpu_load": "",
            "ram": "",
            "gpu": "-",
        }
        for index, count in enumerate(_balanced_counts(total_cameras, recording_count))
    ]
    _allocate_groups(recording_servers, groups)

    weakest, alternatives = _weakest_platform(recommendations)
    recording_ram_recommendation = (
        weakest.get("server_ram", "").strip() or "Unspecified in workbook"
    )
    recommended_recording_ram_gb = _ram_gigabytes(recording_ram_recommendation)
    if recommended_recording_ram_gb is None:
        raise ValueError(
            "The selected recommended platform does not provide a readable RAM "
            "specification for the recording servers."
        )
    recording_ram_meets_minimum = (
        recommended_recording_ram_gb >= minimum_ram
        and _has_two_eight_gb_modules(recording_ram_recommendation)
    )
    recording_ram = (
        recording_ram_recommendation
        if recording_ram_meets_minimum
        else (
            "2 x 8 GB minimum (workbook baseline: "
            f"{recording_ram_recommendation}; upgrade/configuration check required)"
        )
    )
    recording_ram_gb = max(minimum_ram, recommended_recording_ram_gb)
    for server in recording_servers:
        server["processor"] = weakest["processor"]
        server["processor_cpu_load"] = weakest["server_cpu_load"]
        server["ram"] = recording_ram
        server["ram_gb"] = recording_ram_gb
        server["ram_recommendation"] = recording_ram_recommendation
        server["ram_recommendation_gb"] = recommended_recording_ram_gb
        server["ram_upgrade_required"] = not recording_ram_meets_minimum

    gpu_models, gpu_workloads = _gpu_recommendations(sheets)
    gpu_count = sum(item["count"] for item in gpu_models)
    gpu_detector_labels = {item["name"] for item in gpu_workloads}
    resolved_assignments = plat_calc.resolve_detector_assignments(configuration)
    detector_groups: list[dict[str, Any]] = []
    for group_index, group in enumerate(groups):
        detector_names = [
            selected_label
            for _, selected_label in resolved_assignments[group_index]
        ]
        if detector_names:
            detector_groups.append(
                {
                    "group_number": group_index + 1,
                    "group_name": group.get("name", f"Group {group_index + 1}"),
                    "camera_count": group["camera_count"],
                    "detectors": sorted(set(detector_names)),
                }
            )
    if any(
        detector in gpu_detector_labels
        for item in detector_groups
        for detector in item["detectors"]
    ) and gpu_count == 0:
        raise ValueError(
            "The calculator reports GPU detector workloads but no recommended GPU "
            "model or quantity; VMS server count cannot be safely determined."
        )
    if gpu_count and not gpu_workloads:
        raise ValueError(
            "The calculator recommends GPUs but does not identify their detector "
            "workloads."
        )

    vms_count = max(1, gpu_count)
    vms_servers = []
    assigned_models: list[str] = []
    for item in gpu_models:
        assigned_models.extend([item["model"]] * item["count"])
    recommended_vms_ram = weakest.get("server_ram", "").strip()
    recommended_vms_ram_gb = _ram_gigabytes(recommended_vms_ram)
    if recommended_vms_ram_gb is None:
        raise ValueError(
            "The selected recommended platform does not provide a readable RAM "
            "specification for the VMS servers."
        )
    proposed_vms_ram = (
        recommended_vms_ram
        if recommended_vms_ram_gb >= vms_minimum_ram
        else (
            f"{vms_minimum_ram} GB minimum (workbook baseline: "
            f"{recommended_vms_ram}; upgrade required)"
        )
    )
    for index in range(vms_count):
        vms_servers.append(
            {
                "server_number": index + 1,
                "processor": weakest["processor"],
                "processor_cpu_load": weakest["server_cpu_load"],
                "ram": proposed_vms_ram,
                "ram_recommendation": recommended_vms_ram,
                "ram_recommendation_gb": recommended_vms_ram_gb,
                "ram_gb": max(vms_minimum_ram, recommended_vms_ram_gb),
                "ram_upgrade_required": recommended_vms_ram_gb < vms_minimum_ram,
                "minimum_ram_gb": vms_minimum_ram,
                "gpu": assigned_models[index] if index < len(assigned_models) else "NVIDIA GTX 1650",
                "detectors": [],
                "detector_feeds": [],
            }
        )

    for workload in gpu_workloads:
        workload_assignment = _balanced_counts(workload["count"], vms_count)
        for index, count in enumerate(workload_assignment):
            if count:
                vms_servers[index]["detectors"].append(
                    {
                        "name": workload["name"],
                        "count": count,
                        "gpu": True,
                    }
                )

    for group_workload in detector_groups:
        group_assignment = _balanced_counts(
            group_workload["camera_count"],
            vms_count,
        )
        for index, count in enumerate(group_assignment):
            if count:
                vms_servers[index]["detector_feeds"].append(
                    {
                        "group_number": group_workload["group_number"],
                        "group_name": group_workload["group_name"],
                        "camera_count": count,
                        "detectors": group_workload["detectors"],
                    }
                )
                for detector_name in group_workload["detectors"]:
                    if detector_name not in gpu_detector_labels and not any(
                        detector["name"] == detector_name
                        for detector in vms_servers[index]["detectors"]
                    ):
                        vms_servers[index]["detectors"].append(
                            {
                                "name": detector_name,
                                "count": None,
                                "gpu": False,
                            }
                        )

    storage = _workbook_storage(sheets, recommendations)
    storage["minimum_ram_gb"] = minimum_ram
    policy_source = specification.splitlines()
    return {
        "policy_source": specification_name,
        "facility_name": facility_name.strip(),
        "policy_rules": policy_source,
        "total_cameras": total_cameras,
        "groups": groups,
        "vms_servers": vms_servers,
        "recording_servers": recording_servers,
        "recording_processor_alternatives": alternatives,
        "gpu_models": gpu_models,
        "gpu_workloads": gpu_workloads,
        "storage": storage,
        "minimum_ram_gb": minimum_ram,
        "vms_minimum_ram_gb": vms_minimum_ram,
        "weakest_processor_rationale": (
            "Selected the weakest eligible listed recording-server processor "
            "(Intel Xeon Silver, Intel Core Ultra, or Intel Xeon Gold) with the highest "
            "upper CPU-load range; ties are resolved by the workbook's first-listed "
            "option. Ineligible processor lines are excluded. The same eligible "
            "platform supplies the VMS processor and baseline RAM; RAM is increased "
            "to the applicable tier minimum when the workbook baseline is lower."
        ),
        "specification_text": specification,
    }


def _format_camera_groups(server: dict[str, Any]) -> list[str]:
    lines = ["  Camera groups:"]
    if not server["camera_groups"]:
        return lines + ["    - None"]
    lines.extend(
        f"    - {group['group_name']}: {group['camera_count']}"
        for group in server["camera_groups"]
    )
    return lines


def render_report(proposal: dict[str, Any]) -> str:
    storage = proposal["storage"]
    facility_name = proposal.get("facility_name") or "Belirtilmedi"
    lines = [
        f"Tesis adı: {facility_name}",
        "",
        "Altyapı modeli: Sistem, ayrı VMS ve recording katmanlarından oluşur. "
        "Tüm kameralar recording server'lara bağlıdır ve kayıtları burada tutulur. "
        "VMS server'lar görüntüleme ve detector işleme için recording server'lardan "
        "video akışlarını alır; kameralar VMS server'lara taşınmaz ve burada yeniden "
        "sayılmaz.",
        "",
        "Kamera Sistemi Önerisi",
        "======================",
        "",
        f"Yüklenen şartname: {proposal['policy_source']}",
        f"Toplam kamera sayısı: {proposal['total_cameras']}",
        "Kamera grupları:",
    ]
    lines.extend(
        f"- {group.get('name', f'Grup {index + 1}')}: {group['camera_count']} kamera"
        for index, group in enumerate(proposal["groups"])
    )
    lines.extend(
        [
            "",
            f"VMS server sayısı: {len(proposal['vms_servers'])}",
            "VMS server özellikleri",
            "-----------------------",
        ]
    )
    for server in proposal["vms_servers"]:
        lines.extend(
            [
                "",
                f"VMS Server {server['server_number']}: 0 kamera atanmıştır (detector feed alır)",
                f"  İşlemci: {server['processor']}",
                f"  CPU yükü: {server['processor_cpu_load']}",
                f"  RAM: {server['ram']}",
                f"  GPU: {server['gpu']}",
            ]
        )
        lines.extend(
            [
                f"  Workbook RAM önerisi: {server['ram_recommendation']}",
                "  Detector feed'leri (kamera ataması değildir):",
            ]
        )
        if server["detector_feeds"]:
            for feed in server["detector_feeds"]:
                lines.append(
                    f"    - {feed['group_name']}: {', '.join(feed['detectors'])} "
                    f"için {feed['camera_count']} kamera akışı"
                )
        else:
            lines.append("    - Yok")
        lines.append("  Detector iş yükleri:")
        if server["detectors"]:
            for detector in server["detectors"]:
                if detector["count"] is None:
                    lines.append(
                        f"    - {detector['name']} (CPU); adet bilgisi calculator "
                        "çıktısında belirtilmemiş"
                    )
                else:
                    lines.append(
                        f"    - {detector['name']}: {detector['count']} detector örneği"
                    )
        else:
            lines.append("    - Calculator çıktısında detector bildirilmemiş")

    lines.extend(
        [
            "",
            f"Recording server sayısı: {len(proposal['recording_servers'])}",
            "Recording server özellikleri",
            "-----------------------------",
        ]
    )
    for server in proposal["recording_servers"]:
        lines.extend(
            [
                "",
                f"Recording Server {server['server_number']}: {server['camera_count']} kamera",
                f"  İşlemci: {server['processor']}",
                f"  CPU yükü: {server['processor_cpu_load']}",
                f"  RAM: {server['ram']}",
                "  GPU: Yok",
            ]
        )
        lines.extend(_format_camera_groups(server))
    lines.extend(
        [
            "",
            "Seçim ve kaynak açıklamaları",
            "----------------------------",
            (
                "Recording server'lar için izin verilen Intel Xeon Silver, Intel "
                "Core Ultra veya Intel Xeon Gold işlemci ailelerindeki seçenekler "
                "değerlendirilmiştir. Aynı iş yükündeki CPU yük aralığı en yüksek "
                "olan uygun işlemci en zayıf seçenek kabul edilmiştir; eşitlikte "
                "workbook'ta ilk listelenen seçilmiştir. Uygun olmayan işlemci "
                "aileleri ve alternatifleri dışarıda bırakılmıştır. VMS server "
                "işlemcisi ve başlangıç RAM miktarı da uygun Recommended platforms "
                "satırından alınmıştır."
            ),
            (
                f"Şartnamedeki server başına kamera sınırı için gereken en az "
                f"recording server sayısı kullanılmıştır. {proposal['total_cameras']} "
                f"kamera, {len(proposal['recording_servers'])} recording server'a "
                "mümkün olduğunca eşit dağıtılmıştır."
            ),
            (
                f"Calculator {sum(item['count'] for item in proposal['gpu_models'])} "
                "detector GPU önermektedir. Her gerekli GPU için en az bir VMS "
                "server bulunur. Detector GPU atanmayan VMS server'lara NVIDIA "
                "GTX 1650 verilir."
            ),
            (
                "Tüm kamera grupları recording server'larda kalır; recording "
                "server'lara GPU atanmaz. VMS bölümünde kamera ataması değil, "
                "işlenecek video akışları gösterilir."
            ),
            "",
            "Recording server işlemci alternatifleri",
            "----------------------------------------",
        ]
    )
    if proposal["recording_processor_alternatives"]:
        for option in proposal["recording_processor_alternatives"]:
            lines.append(
                f"- {option['processor']}: CPU yükü "
                f"{option.get('server_cpu_load', 'belirtilmemiş')}; RAM "
                f"{option.get('server_ram', 'belirtilmemiş')}"
            )
    else:
        lines.append("- Uygun alternatif işlemci listelenmemiştir.")

    recording_ram = proposal["recording_servers"][0]["ram_gb"]
    recording_ram_recommendation = proposal["recording_servers"][0][
        "ram_recommendation"
    ]
    vms_ram_values = [server["ram_gb"] for server in proposal["vms_servers"]]
    vms_ram_known = all(value is not None for value in vms_ram_values)
    vms_below_minimum = any(
        value is not None and value < proposal["vms_minimum_ram_gb"]
        for value in vms_ram_values
    )
    lines.extend(
        [
            "",
            "RAM durumu",
            "-----------",
            f"Şartname her recording server için en az {proposal['minimum_ram_gb']} GB RAM gerektirir.",
            (
                f"Recording server başına {recording_ram:g} GB RAM planlanmıştır; "
                f"workbook önerisi: {recording_ram_recommendation}. "
                + (
                    "Öneri, en az 2 x 8 GB (toplam 16 GB) koşulunu karşılar."
                    if not proposal["recording_servers"][0]["ram_upgrade_required"]
                    else "RAM, en az 2 x 8 GB (toplam 16 GB) olacak şekilde "
                    "yükseltilmelidir."
                )
            ),
            (
                f"VMS RAM, workbook önerisi dikkate alınarak en az "
                f"{proposal['vms_minimum_ram_gb']} GB planlanmıştır."
                if vms_ram_known and not vms_below_minimum
                else f"VMS RAM, gereken {proposal['vms_minimum_ram_gb']} GB "
                "minimumunun altındadır."
            ),
            "",
            "Depolama ve RAID",
            "----------------",
            f"Gerekli video arşivi: {storage['required_tb']} TB"
            if storage["required_tb"] is not None
            else "Gerekli video arşiv boyutu workbook'ta belirtilmemiştir.",
            (
                f"Recommended platforms arşiv boyutu: "
                f"{storage['recommended_archive_tb']} TB."
                if storage["recommended_archive_tb"] is not None
                else "Recommended platforms arşiv boyutu belirtilmemiştir."
            ),
            f"Recommended platforms RAID: {storage['recommended_raid_level']}",
            f"Calculator RAID ayarı: {storage['raid_level']}",
            (
                f"Arşiv saklama süresi: {storage['archive_days']} gün; günlük "
                f"kayıt oranı: %{storage['recording_percentage']}."
                if storage["archive_days"] is not None
                and storage["recording_percentage"] is not None
                else "Arşiv saklama ayarları workbook'ta eksiktir."
            ),
            f"Calculator disk boyutu: {storage['disk_size_tb']} TB"
            if storage["disk_size_tb"] is not None
            else "Disk boyutu workbook'ta belirtilmemiştir.",
            f"RAID group başına en fazla disk: {storage['max_group_size']}"
            if storage["max_group_size"] is not None
            else "RAID group başına en fazla disk sayısı belirtilmemiştir.",
            (
                "Global RAID/depolama yapılandırması (işlemciden bağımsız seçildi): "
                f"{storage['storage_configuration_global']}"
                if storage["storage_configuration_global"]
                else "Global RAID/depolama yapılandırması workbook'ta listelenmemiştir."
            ),
            f"Toplam ham HDD kapasitesi: {storage['drive_count']} x "
            f"{storage['drive_size_tb']} TB = {storage['raw_tb']} TB"
            if storage["raw_tb"] is not None
            else "Ham HDD kapasitesi workbook verileriyle hesaplanamıyor.",
            f"Yaklaşık kullanılabilir kapasite: {storage['usable_tb']} TB."
            if storage["usable_tb"] is not None
            else f"Kullanılabilir kapasite hesaplanamadı. {storage['usable_note']}",
            "Not: " + storage["usable_note"],
            (
                f"Global yapılandırma için calculator HDD marked capacity: "
                f"{storage['marked_tb_total']} TB."
                if storage["marked_tb_total"] is not None
                else "HDD marked capacity workbook'ta belirtilmemiştir."
            ),
        ]
    )
    if storage["raid_group_count"] is not None:
        lines.append(
            f"Global RAID düzeni: {storage['raid_group_count']} RAID group, "
            f"toplam {storage['drive_count']} disk."
        )
    alternative_configurations = [
        option
        for option in storage["raid_configurations"]
        if option != storage["storage_configuration_global"]
    ]
    if alternative_configurations:
        lines.append(
            "Workbook'ta listelenen diğer RAID yapılandırmaları: "
            + "; ".join(alternative_configurations)
            + "."
        )
    if storage["recommended_raid_level"] != storage["raid_level"]:
        lines.append(
            "Uyumsuzluk: seçilen global RAID yapılandırması "
            f"{storage['recommended_raid_level']}; calculator RAID ayarı ise "
            f"{storage['raid_level']}."
        )
    if (
        storage["marked_tb_total"] is not None
        and storage["usable_tb"] is not None
        and not math.isclose(storage["marked_tb_total"], storage["usable_tb"])
    ):
        lines.append(
            "Calculator tarafından bildirilen HDD marked capacity ile global "
            "RAID düzenine göre hesaplanan yaklaşık kapasite farklıdır. Workbook "
            "bu farkı açıklamadığından her iki değer de gösterilmiştir."
        )
    if storage["required_tb"] is not None and storage["usable_tb"] is not None:
        lines.append(
            "Kullanılabilir kapasite "
            + (
                "gerekli arşiv kapasitesini karşılar"
                if storage["usable_tb"] >= storage["required_tb"]
                else "gerekli arşiv kapasitesini karşılamaz"
            )
            + "."
        )
    lines.extend(
        [
            "Tek bir global RAID yapılandırması, işlemci seçiminden bağımsız olarak "
            "Recommended platforms tablosunda listelenen depolama seçeneklerinden "
            "seçilmiştir; server başına ayrı RAID atanmaz veya disk sayısı server "
            "sayısıyla çarpılmaz. Kullanılabilir kapasite hesabı listelenen RAID "
            "group'larını dikkate alır; biçimlendirme ve dosya sistemi kayıpları dahil değildir.",
            "",
            "Varsayımlar ve belirtilmeyen özellikler",
            "----------------------------------------",
            "- VMS işlemci ve başlangıç RAM bilgisi, izin verilen işlemci ailelerindeki Recommended platforms satırlarından alınmıştır; minimum RAM artışı ayrıca belirtilmiştir.",
            "- Önerilen depolama/RAID seçeneği, işlemciden ve recording server sayısından bağımsız tek bir global yapılandırmadır.",
            "- Calculator depolama ve GPU değerleri öneridir; performans veya kapasite garantisi değildir.",
        ]
    )
    return "\n".join(lines) + "\n"
