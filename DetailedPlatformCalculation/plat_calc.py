#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AxxonSoft Platform Calculator - multi camera group runner.

INPUT SPECIFICATION
===================

Usage:
    python plat_calc.py input.json output.xlsx
    python plat_calc.py input.json output.xlsx --headed

Required top-level fields:
    groups                non-empty list of camera groups

Optional top-level fields:
    archive_days          int, archive depth in days (default: 60)
    software              "Axxon One (x64)" (default) or "Axxon PSIM (x64)"
    calculation_type      "Server" (default), "Server with viewing client",
                          or "Operator's workstation"
    recording_percentage  int: 0, 10, ..., 100 (default: 100)
    raid_level            RAID level (default: "RAID_5")
    disk_size_tb          numeric disk size in TB (default: 16)
    max_disks_per_raid_group int (default: 3)
    resolution            default stream resolution (default: "1920x1080")
    fps                   default stream FPS (default: 25)
    codec                 "H264", "H265", or "MJPEG" (default: "H264")
    gpu_detectors         optional list of detector aliases to assign to GPU.
                          Multiple GPU detectors are allowed. If omitted or
                          empty, all selected detectors with a GPU variant use
                          it. A non-empty list limits GPU use to those aliases.
                          GPU-only detectors always use GPU.
    gpu_priority          legacy name for gpu_detectors.

Each item in "groups":
    name                  descriptive name used in log output
    camera_count          positive integer
    detectors             list of detector aliases (default: [])
    resolution            optional per-group override
    fps                   optional per-group override
    codec                 optional per-group override

Detector aliases accepted in JSON:
    motion_detection
    service_detection
    camera_embedded_detection
    tracker_vmda
    ai_tracker_neural_filter
    neurotracker
    neural_counter
    license_plate_recognition_vt
    license_plate_recognition_rr
    vehicle_make_model_rr
    license_plate_make_model_rr
    license_plate_recognition_iv
    facial_recognition
    fire_detection
    smoke_detection
    visitors_counter
    queue_detector
    human_pose_detector
    equipment_detector
    meta_detector
    crowd_estimation_va

GPU assignment:
    - Multiple GPU-based detectors may be selected across groups or within a
      group; the Platform Calculator handles the resulting sizing.
    - By default, every selected detector with a GPU variant uses it, including
      when gpu_detectors is an empty list.
    - Set a non-empty gpu_detectors list to choose which GPU-capable aliases
      use GPU; other detectors use CPU when available.
    - GPU-only detectors always use GPU.

Example:
    {
      "archive_days": 60,
      "recording_percentage": 100,
      "raid_level": "RAID_5",
      "disk_size_tb": 16,
      "max_disks_per_raid_group": 3,
      "resolution": "1920x1080",
      "fps": 25,
      "codec": "H264",
      "gpu_detectors": [
        "facial_recognition",
        "ai_tracker_neural_filter"
      ],
      "groups": [
        {
          "name": "Face cameras",
          "camera_count": 20,
          "detectors": ["facial_recognition", "ai_tracker_neural_filter"]
        },
        {
          "name": "Fire cameras",
          "camera_count": 10,
          "detectors": ["fire_detection"]
        },
        {
          "name": "General cameras",
          "camera_count": 30,
          "detectors": []
        }
      ]
    }

Notes:
    - RAID 5 requires at least three disks per RAID group. The calculator
      setting controls the maximum group size; a maximum of three yields
      three-disk groups.
    - Each group is configured using its first/default video stream.
    - Camera group names are retained in the script's log. The calculator's
      own group title is left at its default in this first standalone version.
    - The script uses the calculator's native "Save as XLS" download. The
      output filename is taken from the CLI argument; if the server's actual
      workbook extension differs, the actual extension is preserved.
    - The calculator is a sizing estimate. It does not validate whether
      camera image/FPS parameters satisfy each detector's operational needs.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    Page,
    Locator,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError,
    sync_playwright,
)


CALCULATOR_URL = "https://sale.axxonsoft.com/calc/calculator.jsf"

SUPPORTED_RECORDING_PERCENTAGES = {
    0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
}
DEFAULT_ARCHIVE_DAYS = 60
DEFAULT_RECORDING_PERCENTAGE = 100
DEFAULT_RAID_LEVEL = "RAID_5"
DEFAULT_DISK_SIZE_TB = 16
DEFAULT_MAX_DISKS_PER_RAID_GROUP = 18
SUPPORTED_RAID_LEVELS = {
    "NO_RAID",
    "JBOD",
    "RAID_0",
    "RAID_1",
    "RAID_10",
    "RAID_5",
    "RAID_6",
}

LOG = logging.getLogger("plat_calc")


@dataclass(frozen=True)
class DetectorVariant:
    category: str
    cpu: str | None
    gpu: str | None


# Names below follow the Axxon One x64 detector names in the
# Platform Calculator documentation. The visible calculator labels are
# matched exactly; if Axxon changes a label, the script fails with a useful
# error rather than silently selecting a different detector.
DETECTORS: dict[str, DetectorVariant] = {
    "motion_detection": DetectorVariant(
        "Trackers", "Motion detector (CPU)", "Motion detector (GPU)"
    ),
    "service_detection": DetectorVariant(
        "Service", "Service detector (CPU, key frames)", None
    ),
    "camera_embedded_detection": DetectorVariant(
        "Embedded", "Embedded camera detector (any) (CPU)", None
    ),
    "tracker_vmda": DetectorVariant(
        "Trackers", "Object tracker (CPU)", None
    ),
    "ai_tracker_neural_filter": DetectorVariant(
        "Trackers",
        "Object tracker with neural filter (CPU)",
        "Object tracker with neural filter (GPU)",
    ),
    "neurotracker": DetectorVariant(
        "Trackers",
        "Neural tracker (CPU, 6 FPS)",
        "Neural tracker (GPU, 6 FPS)",
    ),
    "neural_counter": DetectorVariant(
        "Retail",
        "Neural counter (CPU, 1 FPS)",
        "Neural counter (GPU, 1 FPS)",
    ),
    "license_plate_recognition_vt": DetectorVariant(
        "Vehicle", "License plate recognition VT (CPU)", None
    ),
    "license_plate_recognition_rr": DetectorVariant(
        "Vehicle",
        "License plate recognition RR (CPU)",
        "License plate recognition RR (GPU)",
    ),
    "vehicle_make_model_rr": DetectorVariant(
        "Vehicle",
        "Vehicle make and model recognition RR (CPU)",
        "Vehicle make and model recognition RR (GPU)",
    ),
    "license_plate_make_model_rr": DetectorVariant(
        "Vehicle",
        "License plate, make and model recognition RR (CPU)",
        "License plate, make and model recognition RR (GPU)",
    ),
    "license_plate_recognition_iv": DetectorVariant(
        "Vehicle",
        "License plate recognition IV (CPU)",
        "License plate recognition IV (GPU)",
    ),
    "facial_recognition": DetectorVariant(
        "Face", "Face detector VA (CPU)", "Face detector VA (GPU)"
    ),
    "fire_detection": DetectorVariant(
        "Production Safety",
        "Fire detector (CPU, 0.1 FPS)",
        "Fire detector (GPU, 0.1 FPS)",
    ),
    "smoke_detection": DetectorVariant(
        "Production Safety",
        "Smoke detector (CPU, 0.1 FPS)",
        "Smoke detector (GPU, 0.1 FPS)",
    ),
    "visitors_counter": DetectorVariant(
        "Retail", "People counter (CPU)", None
    ),
    "queue_detector": DetectorVariant(
        "Retail", "Queue detector (CPU)", None
    ),
    "human_pose_detector": DetectorVariant(
        "Poses",
        "Human pose detector (CPU, 3 FPS)",
        "Human pose detector (GPU, 3 FPS)",
    ),
    "equipment_detector": DetectorVariant(
        "Production Safety",
        "Equipment detector (CPU, 1 FPS)",
        "Equipment detector (GPU, 1 FPS)",
    ),
    "meta_detector": DetectorVariant(
        "Retail", None, "Meta-detector (GPU, 1 FPS)"
    ),
    "crowd_estimation_va": DetectorVariant(
        "Retail", None, "Crowd estimation VA (GPU)"
    ),
}


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_and_validate_input(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Input JSON not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    if not isinstance(config, dict):
        raise ValueError("Input JSON root must be an object.")

    config.setdefault("archive_days", DEFAULT_ARCHIVE_DAYS)
    config.setdefault("recording_percentage", DEFAULT_RECORDING_PERCENTAGE)
    config.setdefault("raid_level", DEFAULT_RAID_LEVEL)
    config.setdefault("disk_size_tb", DEFAULT_DISK_SIZE_TB)
    config.setdefault(
        "max_disks_per_raid_group",
        DEFAULT_MAX_DISKS_PER_RAID_GROUP,
    )

    archive_days = config["archive_days"]
    if isinstance(archive_days, bool) or not isinstance(archive_days, int):
        raise ValueError("'archive_days' must be an integer.")
    if archive_days < 0:
        raise ValueError("'archive_days' cannot be negative.")

    percentage = config["recording_percentage"]
    if isinstance(percentage, bool) or not isinstance(percentage, int):
        raise ValueError("'recording_percentage' must be an integer.")
    if percentage not in SUPPORTED_RECORDING_PERCENTAGES:
        raise ValueError(
            "'recording_percentage' must be one of "
            f"{sorted(SUPPORTED_RECORDING_PERCENTAGES)}."
        )

    raid_level = config["raid_level"]
    if not isinstance(raid_level, str) or raid_level not in SUPPORTED_RAID_LEVELS:
        raise ValueError(
            "'raid_level' must be one of "
            f"{sorted(SUPPORTED_RAID_LEVELS)}."
        )

    disk_size_tb = config["disk_size_tb"]
    if (
        isinstance(disk_size_tb, bool)
        or not isinstance(disk_size_tb, (int, float))
        or disk_size_tb <= 0
    ):
        raise ValueError("'disk_size_tb' must be a positive number.")

    max_disks_per_raid_group = config["max_disks_per_raid_group"]
    if (
        isinstance(max_disks_per_raid_group, bool)
        or not isinstance(max_disks_per_raid_group, int)
        or not 1 <= max_disks_per_raid_group <= 30
    ):
        raise ValueError(
            "'max_disks_per_raid_group' must be an integer from 1 to 30."
        )
    if raid_level == "RAID_5" and max_disks_per_raid_group < 3:
        raise ValueError(
            "'max_disks_per_raid_group' must be at least 3 for RAID 5."
        )

    groups = config.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("'groups' must be a non-empty JSON array.")

    total_cameras = 0
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise ValueError(f"groups[{index}] must be an object.")

        count = group.get("camera_count")
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError(
                f"groups[{index}].camera_count must be a positive integer."
            )

        detectors = group.get("detectors", [])
        if not isinstance(detectors, list):
            raise ValueError(f"groups[{index}].detectors must be an array.")

        for alias in detectors:
            if not isinstance(alias, str) or alias not in DETECTORS:
                raise ValueError(
                    f"Unknown detector alias in groups[{index}]: {alias!r}. "
                    f"Allowed aliases: {', '.join(DETECTORS)}"
                )

        total_cameras += count

        fps = group.get("fps", config.get("fps", 25))
        if isinstance(fps, bool) or not isinstance(fps, int) or not 1 <= fps <= 60:
            raise ValueError(
                f"groups[{index}].fps must be an integer from 1 to 60."
            )

    if "camera_count" in config and config["camera_count"] != total_cameras:
        raise ValueError(
            "Top-level camera_count does not match the sum of group camera_count."
        )

    software = config.get("software", "Axxon One (x64)")
    if software not in {"Axxon One (x64)", "Axxon PSIM (x64)"}:
        raise ValueError(
            "software must be 'Axxon One (x64)' or 'Axxon PSIM (x64)'."
        )

    calculation_type = config.get("calculation_type", "Server")
    if calculation_type not in {
        "Server",
        "Server with viewing client",
        "Operator's workstation",
    }:
        raise ValueError("Unsupported calculation_type.")

    if calculation_type == "Operator's workstation":
        if any(group.get("detectors", []) for group in groups):
            raise ValueError(
                "The Platform Calculator does not allow detector selection "
                "for Operator's workstation calculations."
            )

    return config


def resolve_detector_assignments(
    config: dict[str, Any],
) -> list[list[tuple[str, str]]]:
    """
    Return per-group (alias, exact UI label) pairs.

    By default, select the GPU variant for every detector that provides one.
    gpu_detectors (or the legacy gpu_priority key) can restrict this to an
    explicit set of aliases. GPU-only detectors always use their GPU variant.
    """
    if "gpu_detectors" in config and "gpu_priority" in config:
        raise ValueError(
            "Use 'gpu_detectors' instead of specifying both "
            "'gpu_detectors' and the legacy 'gpu_priority'."
        )

    gpu_aliases = config.get("gpu_detectors", config.get("gpu_priority"))
    if gpu_aliases is not None and (
        not isinstance(gpu_aliases, list)
        or not all(
            isinstance(item, str) and item in DETECTORS
            for item in gpu_aliases
        )
    ):
        raise ValueError(
            "'gpu_detectors' must be a list of detector aliases."
        )
    selected_for_gpu = set(gpu_aliases) if gpu_aliases else None

    assignments: list[list[tuple[str, str]]] = [
        [] for _ in config["groups"]
    ]

    for group_index, group in enumerate(config["groups"]):
        for alias in group.get("detectors", []):
            variant = DETECTORS[alias]

            use_gpu = variant.gpu is not None and (
                selected_for_gpu is None
                or alias in selected_for_gpu
                or variant.cpu is None
            )
            if use_gpu:
                selected_label = variant.gpu
            elif variant.cpu:
                selected_label = variant.cpu
            else:
                raise ValueError(
                    f"Detector '{alias}' has no CPU or GPU variant."
                )

            if selected_label is None:
                raise ValueError(f"No usable variant found for detector '{alias}'.")

            assignments[group_index].append((alias, selected_label))

    return assignments


def _wait_for_first_camera_group(page: Page) -> Locator:
    camera_count = page.locator(
        'input[id^="cameraGroupForm:cameras:cameraGroupPanel:0:'
        'cameraGroupMainSettingsPanel:"][id$="_input"]'
    ).first
    camera_count.wait_for(state="visible", timeout=30000)
    return page.locator(
        '[id^="cameraGroupForm:cameras:cameraGroupPanel:0:"]'
    )


def _click_accept_if_present(page: Page) -> None:
    for frame in page.frames:
        for _ in range(5):
            buttons = frame.get_by_role(
                "button",
                name=re.compile(r"^Accept$", re.I),
            )
            visible_buttons = [
                buttons.nth(index)
                for index in range(buttons.count())
                if buttons.nth(index).is_visible()
            ]
            if not visible_buttons:
                break

            visible_buttons[0].click(timeout=3000)
            page.wait_for_timeout(700)
        else:
            raise RuntimeError(
                "Calculator still shows an Accept dialog after five attempts."
            )


def _select_software(page: Page, software: str) -> None:
    page.get_by_role("radio", name=software, exact=True).check()
    page.wait_for_timeout(800)
    LOG.info("Software selected: %s", software)


def _select_calculation_type(page: Page, calculation_type: str) -> None:
    page.get_by_role(
        "radio", name=calculation_type, exact=True
    ).check()
    page.wait_for_timeout(1000)
    LOG.info("Calculation type selected: %s", calculation_type)


def _wait_for_primefaces_idle(page: Page, timeout: int = 30000) -> None:
    page.wait_for_function(
        """() => {
            const queue = window.PrimeFaces?.ajax?.Queue;
            const activeRequests = window.jQuery?.active;
            if (
                !queue
                || activeRequests === undefined
                || !queue.isEmpty()
                || queue.xhrs.length > 0
                || activeRequests > 0
            ) {
                window.__platformCalculatorIdleSince = null;
                return false;
            }

            if (window.__platformCalculatorIdleSince === null
                || window.__platformCalculatorIdleSince === undefined) {
                window.__platformCalculatorIdleSince = Date.now();
                return false;
            }
            return Date.now() - window.__platformCalculatorIdleSince >= 750;
        }""",
        timeout=timeout,
    )
    page.evaluate("window.__platformCalculatorIdleSince = null")


def _set_global_archive(page: Page, config: dict[str, Any]) -> None:
    archive_panel = page.locator(
        '[id="archiveForm:archiveSettingsPanel"]'
    )
    archive_panel.scroll_into_view_if_needed()

    percentage_select = page.locator(
        '[id="archiveForm:vendor-and-archice-settings:archivePercentInputEng_input"]'
    )
    percentage_select.wait_for(state="attached", timeout=15000)
    percentage_select.select_option(
        value=str(config["recording_percentage"]),
        force=True,
    )
    _wait_for_primefaces_idle(page)

    archive_input = page.locator(
        '[id="archiveForm:vendor-and-archice-settings:archiveDays_input"]'
    )
    archive_input.wait_for(state="visible", timeout=15000)
    archive_input.fill(str(config["archive_days"]))
    archive_input.press("Tab")
    _wait_for_primefaces_idle(page)

    if archive_input.input_value() != str(config["archive_days"]):
        raise RuntimeError("Could not set global archive days.")

    raid_level = config["raid_level"]
    raid_labels = {
        "NO_RAID": "Calculation without RAID",
        "JBOD": "JBOD",
        "RAID_0": "RAID 0",
        "RAID_1": "RAID 1",
        "RAID_10": "RAID 10",
        "RAID_5": "RAID 5",
        "RAID_6": "RAID 6",
    }
    raid_group = page.locator(
        '[id="archiveForm:vendor-and-archice-settings:archive-calculation-type"]'
    )
    raid_radio = raid_group.get_by_role(
        "radio",
        name=raid_labels[raid_level],
        exact=True,
    )
    if not raid_radio.is_checked():
        raid_radio.locator("xpath=..").click()
        _wait_for_primefaces_idle(page)
    if not raid_radio.is_checked():
        raise RuntimeError(f"Could not select archive RAID level {raid_level}.")

    disk_size_input = page.locator(
        '[id="archiveForm:vendor-and-archice-settings:raidArchiveCapacity_input"]'
    )
    if raid_level != "NO_RAID":
        disk_size_input.wait_for(state="visible", timeout=15000)
        page.wait_for_function(
            "(id) => { const input = document.getElementById(id); "
            "return input !== null && !input.disabled; }",
            arg="archiveForm:vendor-and-archice-settings:raidArchiveCapacity_input",
            timeout=15000,
        )
        disk_size_value = str(config["disk_size_tb"])
        disk_size_input.fill(disk_size_value)
        disk_size_input.press("Tab")
        _wait_for_primefaces_idle(page)
        if disk_size_input.input_value() != disk_size_value:
            raise RuntimeError(
                f"Could not set archive disk size to {disk_size_value} TB."
            )

    max_disks = config["max_disks_per_raid_group"]
    max_disks_label = page.locator(
        '[id="archiveForm:vendor-and-archice-settings:numberOfDisksInRaid_label"]'
    )
    if raid_level == "RAID_5":
        max_disks_label.wait_for(state="visible", timeout=15000)
    if max_disks_label.is_visible():
        max_disks_label.click()
        options_panel = page.locator(
            '[id="archiveForm:vendor-and-archice-settings:numberOfDisksInRaid_panel"]'
        )
        max_disks_option = options_panel.get_by_role(
            "option",
            name=str(max_disks),
            exact=True,
        )
        max_disks_option.wait_for(state="visible", timeout=10000)
        max_disks_option.click()
        _wait_for_primefaces_idle(page)

        selected_max_disks = page.locator(
            '[id="archiveForm:vendor-and-archice-settings:numberOfDisksInRaid_input"]'
        )
        if selected_max_disks.input_value() != str(max_disks):
            raise RuntimeError(
                "Could not set maximum disks per RAID group to "
                f"{max_disks}."
            )
    elif raid_level == "RAID_5":
        raise RuntimeError(
            "Maximum disks per RAID group control is unavailable for RAID 5."
        )

    LOG.info(
        "Global archive: %s days, %s%% of day; %s, disk size %s TB, "
        "maximum %s disks per RAID group",
        config["archive_days"],
        config["recording_percentage"],
        raid_level,
        config["disk_size_tb"],
        max_disks,
    )


def _add_camera_group(page: Page, expected_index: int) -> Locator:
    add_button = page.locator(
        '[id="cameraGroupForm:cameras:addCameraGroupButton"]'
    )
    add_button.wait_for(state="visible", timeout=15000)
    add_button.click()

    camera_count = page.locator(
        f'input[id^="cameraGroupForm:cameras:cameraGroupPanel:{expected_index}:'
        'cameraGroupMainSettingsPanel:"][id$="_input"]'
    ).first
    camera_count.wait_for(state="visible", timeout=20000)
    page.wait_for_timeout(700)
    LOG.info("Camera group %s created.", expected_index + 1)
    return page.locator(
        f'[id^="cameraGroupForm:cameras:cameraGroupPanel:{expected_index}:"]'
    )


def _set_group_camera_count(
    page: Page,
    group_index: int,
    count: int,
) -> None:
    camera_input = page.locator(
        f'input[id^="cameraGroupForm:cameras:cameraGroupPanel:{group_index}:'
        'cameraGroupMainSettingsPanel:"][id$="_input"]'
    ).first

    camera_input.wait_for(state="visible", timeout=15000)
    camera_input.fill(str(count))
    camera_input.press("Tab")
    _wait_for_primefaces_idle(page)

    actual = camera_input.input_value()
    if actual != str(count):
        raise RuntimeError(
            f"Group {group_index + 1}: camera count mismatch; "
            f"expected {count}, got {actual!r}."
        )


def _set_group_select(
    page: Page,
    group: Locator,
    group_index: int,
    field: str,
    value: str,
) -> None:
    element_id = (
        f"cameraGroupForm:cameras:cameraGroupPanel:{group_index}:"
        f"cameraRequestForm:{field}_input"
    )
    select = group.page.locator(f'[id="{element_id}"]')
    select.wait_for(state="attached", timeout=15000)

    options = select.locator("option")
    available = []
    for i in range(options.count()):
        option = options.nth(i)
        available.append(
            (
                option.get_attribute("value"),
                (option.inner_text() or "").strip(),
            )
        )

    matched_value = None
    normalized = value.strip().lower()
    for option_value, label in available:
        if option_value == value or label.lower() == normalized:
            matched_value = option_value
            break

    if matched_value is None and field == "fpsInput":
        for option_value, label in available:
            if option_value in {f"{value}.0", value} or label in {
                f"{value}.0",
                value,
            }:
                matched_value = option_value
                break

    if matched_value is None:
        raise ValueError(
            f"Unsupported {field} value {value!r} for group {group_index + 1}. "
            f"Calculator options: {available}"
        )

    select.select_option(value=matched_value, force=True)
    _wait_for_primefaces_idle(page)

    refreshed = page.locator(f'[id="{element_id}"]')
    current = refreshed.input_value()
    if current != matched_value:
        raise RuntimeError(
            f"Could not set {field} for group {group_index + 1}: "
            f"expected {matched_value!r}, got {current!r}."
        )


def _find_analytics_trigger(page: Page, group_index: int) -> Locator:
    trigger = page.locator(
        '[id="cameraGroupForm:cameras:cameraGroupPanel:'
        f'{group_index}:cameraRequestForm:applyDetectorsButton"]'
    )
    if trigger.count() != 1:
        raise RuntimeError(
            f"Could not identify the Video Analytics edit button for group "
            f"{group_index + 1}; found {trigger.count()} matching controls."
        )
    return trigger


def _click_category_if_needed(dialog: Locator, category: str) -> None:
    tab = dialog.locator('a[href*="detectorsTabs"]').filter(
        has_text=re.compile(rf"^\s*{re.escape(category)}\s*$", re.I)
    )
    if tab.count() == 0:
        raise RuntimeError(
            f"Detector category tab not found in calculator: {category!r}."
        )
    tab.first.click()
    dialog.page.wait_for_timeout(250)


def _select_detectors_for_group(
    page: Page,
    group_index: int,
    selected_labels: list[str],
) -> None:
    if not selected_labels:
        LOG.info("Group %s: no additional detectors.", group_index + 1)
        return

    trigger = _find_analytics_trigger(page, group_index)
    trigger.click()
    page.wait_for_timeout(500)

    detector_panel = page.locator(
        'div.detectors-panel[id^="cameraGroupForm:cameras:cameraGroupPanel:'
        f'{group_index}:cameraRequestForm:"]'
    ).first
    detector_panel.wait_for(state="visible", timeout=10000)
    category_tabs = detector_panel.locator('a[href*="detectorsTabs"]')
    category_tabs.first.wait_for(state="attached", timeout=15000)

    for label in selected_labels:
        category = next(
            (
                item.category
                for item in DETECTORS.values()
                if label in {item.cpu, item.gpu}
            ),
            None,
        )
        if category:
            _click_category_if_needed(detector_panel, category)

        detector_item = detector_panel.get_by_text(label, exact=True)
        if detector_item.count() == 0 or not detector_item.first.is_visible():
            raise RuntimeError(
                f"Detector label not found in calculator dialog: {label!r}. "
                "Check the current calculator detector catalog and UI labels."
            )

        detector_item.first.click()
        page.wait_for_timeout(250)
        LOG.info("Group %s: detector selected: %s", group_index + 1, label)

    apply_button = detector_panel.get_by_role(
        "button", name=re.compile(r"^Apply$", re.I)
    )
    if apply_button.count() == 0:
        apply_button = detector_panel.get_by_text("Apply", exact=True)

    if apply_button.count() == 0:
        raise RuntimeError("Could not find Apply in the detector dialog.")

    apply_button.first.click()
    page.wait_for_timeout(700)
    for label in selected_labels:
        detector_panel.get_by_text(label, exact=True).first.wait_for(
            state="visible", timeout=10000
        )


def _save_xls(page: Page, requested_output: Path) -> Path:
    requested_output.parent.mkdir(parents=True, exist_ok=True)

    export_button = page.get_by_role(
        "button", name=re.compile(r"Save as XLS", re.I)
    )
    export_button.wait_for(state="visible", timeout=30000)

    with page.expect_download(timeout=60000) as download_info:
        export_button.click()

    download = download_info.value
    suggested = Path(download.suggested_filename)
    actual_suffix = suggested.suffix or requested_output.suffix

    destination = requested_output
    if requested_output.suffix.lower() != actual_suffix.lower():
        destination = requested_output.with_suffix(actual_suffix)
        LOG.warning(
            "Calculator exported %s, not %s. Saving with the real extension: %s",
            actual_suffix or "(no extension)",
            requested_output.suffix,
            destination,
        )

    download.save_as(str(destination))

    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError(f"Downloaded workbook is missing or empty: {destination}")

    LOG.info("Workbook saved: %s", destination.resolve())
    return destination


def run_calculation(
    config: dict[str, Any],
    output_path: Path,
    headed: bool = False,
) -> Path:
    assignments = resolve_detector_assignments(config)

    LOG.info(
        "Total cameras: %s in %s groups",
        sum(group["camera_count"] for group in config["groups"]),
        len(config["groups"]),
    )

    for index, group in enumerate(config["groups"]):
        LOG.info(
            "Group %s (%s): %s cameras; detectors=%s",
            index + 1,
            group.get("name", f"Group {index + 1}"),
            group["camera_count"],
            [label for _, label in assignments[index]],
        )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        try:
            page = browser.new_page(
                viewport={"width": 1600, "height": 1100},
                accept_downloads=True,
            )
            page.set_default_timeout(15000)

            LOG.info("Opening AxxonSoft Platform Calculator.")
            page.goto(
                CALCULATOR_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )
            page.wait_for_timeout(1500)
            _click_accept_if_present(page)

            page.get_by_text(
                "Please select your software", exact=False
            ).first.wait_for(state="visible", timeout=30000)

            _select_software(
                page,
                config.get("software", "Axxon One (x64)"),
            )
            _select_calculation_type(
                page,
                config.get("calculation_type", "Server"),
            )

            first_group = _wait_for_first_camera_group(page)

            # The first group already exists. Create additional groups before
            # applying their parameters.
            groups: list[Locator] = [first_group]
            for index in range(1, len(config["groups"])):
                groups.append(_add_camera_group(page, index))

            for index, (group_config, group_locator) in enumerate(
                zip(config["groups"], groups)
            ):
                group_name = group_config.get("name", f"Group {index + 1}")
                LOG.info("Configuring group %s: %s", index + 1, group_name)

                _set_group_camera_count(
                    page,
                    index,
                    group_config["camera_count"],
                )

                _set_group_select(
                    page,
                    group_locator,
                    index,
                    "resolutionInput",
                    group_config.get(
                        "resolution", config.get("resolution", "1920x1080")
                    ),
                )
                _set_group_select(
                    page,
                    group_locator,
                    index,
                    "fpsInput",
                    str(group_config.get("fps", config.get("fps", 25))),
                )

                codec = group_config.get("codec", config.get("codec", "H264"))
                codec_mapping = {
                    "H.264": "H264",
                    "H264": "H264",
                    "H.265": "H265",
                    "H265": "H265",
                    "MJPEG": "MjPEG",
                    "MjPEG": "MjPEG",
                }
                if codec not in codec_mapping:
                    raise ValueError(
                        f"Unsupported codec {codec!r}; use H264, H265, or MJPEG."
                    )
                _set_group_select(
                    page,
                    group_locator,
                    index,
                    "codecInput",
                    codec_mapping[codec],
                )

            for index, group_config in enumerate(config["groups"]):
                group_name = group_config.get("name", f"Group {index + 1}")
                LOG.info("Assigning detectors for group %s: %s", index + 1, group_name)
                _select_detectors_for_group(
                    page,
                    index,
                    [label for _, label in assignments[index]],
                )

            _set_global_archive(page, config)

            # Give PrimeFaces time to recalculate the recommendation tables.
            page.wait_for_timeout(3000)

            result_table = page.locator(
                '[id="results:results-form:recommended-platforms"]'
            )
            result_table.wait_for(state="visible", timeout=30000)

            return _save_xls(page, output_path)

        finally:
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure Axxon Platform Calculator camera groups and export XLS."
    )
    parser.add_argument("input_json", type=Path, help="Input specification JSON file.")
    parser.add_argument("output_file", type=Path, help="Requested output workbook path.")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the Chromium browser window for troubleshooting.",
    )
    args = parser.parse_args()

    configure_logging()

    try:
        config = load_and_validate_input(args.input_json)
        output = run_calculation(config, args.output_file, headed=args.headed)
        print(f"\nCompleted. Workbook: {output.resolve()}")
        return 0

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        RuntimeError,
        PlaywrightTimeoutError,
        PlaywrightError,
    ) as error:
        LOG.error("%s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
