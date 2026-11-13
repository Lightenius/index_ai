"""Create a Turkish, single-page Excel equipment listing."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any


_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_XML_NS = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("", _MAIN_NS)
ET.register_namespace("r", _REL_NS)


def _column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _number(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:g}"


def _cpu_rows(servers: list[dict[str, Any]]) -> list[list[Any]]:
    processor = servers[0]["processor"]
    return [["CPU", processor, 1, len(servers)]]


def _ram_rows(servers: list[dict[str, Any]]) -> list[list[Any]]:
    server = servers[0]
    recommendation = server["ram_recommendation"]
    proposed_gb = float(server["ram_gb"])
    module_match = re.search(
        r"(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*GB\b",
        recommendation,
        flags=re.IGNORECASE,
    )
    baseline_gb = server.get("ram_recommendation_gb")
    if module_match and not server.get("ram_upgrade_required", False):
        module_count = int(module_match.group(1))
        module_size_gb = float(module_match.group(2))
        ram_type = re.search(
            r"\bDDR[345]\w*\b",
            recommendation,
            flags=re.IGNORECASE,
        )
        type_text = f" {ram_type.group().upper()}" if ram_type else ""
        model = f"{_number(module_size_gb)} GB{type_text} RAM"
    else:
        module_count = int(module_match.group(1)) if module_match else 2
        module_size_gb = proposed_gb / module_count
        ram_type = re.search(
            r"\bDDR[345]\w*\b",
            recommendation,
            flags=re.IGNORECASE,
        )
        type_text = f" {ram_type.group().upper()}" if ram_type else ""
        model = f"{_number(module_size_gb)} GB{type_text} RAM"
    if baseline_gb is None or not re.search(
        r"\bDDR[345]\w*\b",
        recommendation,
        flags=re.IGNORECASE,
    ):
        model += " (tür belirtilmemiş)"
    return [[
        "RAM",
        model,
        module_count,
        module_count * len(servers),
    ]]


def _gpu_rows(servers: list[dict[str, Any]]) -> list[list[Any]]:
    counts: dict[str, int] = {}
    for server in servers:
        model = str(server["gpu"]).strip()
        if model and model != "-":
            counts[model] = counts.get(model, 0) + 1
    if not counts:
        return [["GPU", "Yok", 0, 0]]
    return [
        ["GPU", model, 1, count]
        for model, count in counts.items()
    ]


def _make_tables(proposal: dict[str, Any]) -> tuple[list[list[Any]], list[list[Any]], list[list[Any]]]:
    vms_servers = proposal["vms_servers"]
    recording_servers = proposal["recording_servers"]
    storage = proposal["storage"]
    camera_count = proposal["total_cameras"]
    drive_count = storage.get("drive_count")
    disk_size_tb = storage.get("drive_size_tb")
    disk_description = (
        f"{_number(disk_size_tb)} TB boyutlu"
        if drive_count is not None and disk_size_tb is not None
        else "Boyut belirtilmemiş"
    )
    general = [
        ["IP Kamera", "Toplam kamera sayısı", camera_count, "adet"],
        ["İş İstasyonu (VMS)", "VMS sunucusu", len(vms_servers), "adet"],
        [
            "Rack Tipi Sunucu (recording)",
            "Recording sunucusu",
            len(recording_servers),
            "adet",
        ],
        [
            "Disk Sürücüsü",
            disk_description,
            drive_count if drive_count is not None else "Belirtilmemiş",
            "adet",
        ],
    ]
    vms_details = (
        _cpu_rows(vms_servers)
        + _ram_rows(vms_servers)
        + _gpu_rows(vms_servers)
    )
    recording_details = (
        _cpu_rows(recording_servers)
        + _ram_rows(recording_servers)
        + _gpu_rows(recording_servers)
    )
    return general, vms_details, recording_details


def _style_sheet() -> ET.Element:
    root = ET.Element(f"{{{_MAIN_NS}}}styleSheet")
    fonts = ET.SubElement(root, f"{{{_MAIN_NS}}}fonts", count="3")
    ET.SubElement(fonts, f"{{{_MAIN_NS}}}font")
    title_font = ET.SubElement(fonts, f"{{{_MAIN_NS}}}font")
    ET.SubElement(title_font, f"{{{_MAIN_NS}}}b")
    ET.SubElement(title_font, f"{{{_MAIN_NS}}}sz", val="16")
    section_font = ET.SubElement(fonts, f"{{{_MAIN_NS}}}font")
    ET.SubElement(section_font, f"{{{_MAIN_NS}}}b")
    fills = ET.SubElement(root, f"{{{_MAIN_NS}}}fills", count="3")
    ET.SubElement(fills, f"{{{_MAIN_NS}}}fill").append(
        ET.Element(f"{{{_MAIN_NS}}}patternFill", patternType="none")
    )
    ET.SubElement(fills, f"{{{_MAIN_NS}}}fill").append(
        ET.Element(f"{{{_MAIN_NS}}}patternFill", patternType="gray125")
    )
    for color in ("FF1F4E78", "FFD9EAF7"):
        fill = ET.SubElement(fills, f"{{{_MAIN_NS}}}fill")
        pattern = ET.SubElement(
            fill, f"{{{_MAIN_NS}}}patternFill", patternType="solid"
        )
        ET.SubElement(pattern, f"{{{_MAIN_NS}}}fgColor", rgb=color)
        ET.SubElement(pattern, f"{{{_MAIN_NS}}}bgColor", indexed="64")
    borders = ET.SubElement(root, f"{{{_MAIN_NS}}}borders", count="2")
    ET.SubElement(borders, f"{{{_MAIN_NS}}}border")
    border = ET.SubElement(borders, f"{{{_MAIN_NS}}}border")
    for side in ("left", "right", "top", "bottom"):
        ET.SubElement(border, f"{{{_MAIN_NS}}}{side}", style="thin").append(
            ET.Element(f"{{{_MAIN_NS}}}color", rgb="FFB7C9D6")
        )
    cell_style_xfs = ET.SubElement(root, f"{{{_MAIN_NS}}}cellStyleXfs", count="1")
    ET.SubElement(cell_style_xfs, f"{{{_MAIN_NS}}}xf", numFmtId="0", fontId="0", fillId="0", borderId="0")
    cell_xfs = ET.SubElement(root, f"{{{_MAIN_NS}}}cellXfs", count="4")
    ET.SubElement(cell_xfs, f"{{{_MAIN_NS}}}xf", numFmtId="0", fontId="0", fillId="0", borderId="1", xfId="0", applyBorder="1", applyAlignment="1").append(
        ET.Element(f"{{{_MAIN_NS}}}alignment", vertical="center", wrapText="1")
    )
    ET.SubElement(cell_xfs, f"{{{_MAIN_NS}}}xf", numFmtId="0", fontId="1", fillId="0", borderId="0", xfId="0", applyAlignment="1").append(
        ET.Element(f"{{{_MAIN_NS}}}alignment", vertical="center")
    )
    ET.SubElement(cell_xfs, f"{{{_MAIN_NS}}}xf", numFmtId="0", fontId="2", fillId="2", borderId="1", xfId="0", applyFill="1", applyBorder="1", applyAlignment="1").append(
        ET.Element(f"{{{_MAIN_NS}}}alignment", vertical="center")
    )
    ET.SubElement(cell_xfs, f"{{{_MAIN_NS}}}xf", numFmtId="0", fontId="2", fillId="3", borderId="1", xfId="0", applyFill="1", applyBorder="1", applyAlignment="1").append(
        ET.Element(f"{{{_MAIN_NS}}}alignment", vertical="center", wrapText="1")
    )
    cell_styles = ET.SubElement(root, f"{{{_MAIN_NS}}}cellStyles", count="1")
    ET.SubElement(cell_styles, f"{{{_MAIN_NS}}}cellStyle", name="Normal", xfId="0", builtinId="0")
    return root


def _worksheet_xml(proposal: dict[str, Any]) -> ET.Element:
    general, vms, recording = _make_tables(proposal)
    rows: list[tuple[list[Any], int]] = []
    section_rows: list[int] = []

    def add_section(title: str, headers: list[str], values: list[list[Any]]) -> None:
        section_rows.append(len(rows) + 1)
        rows.append(([title], 2))
        rows.append((headers, 3))
        rows.extend((value, 0) for value in values)

    rows.append((["Ekipman ve Sistem Bileşenleri"], 1))
    rows.append(
        ([f"Tesis adı: {proposal.get('facility_name') or 'Belirtilmedi'}"], 2)
    )
    add_section(
        "1. Genel Liste",
        ["Kalem", "Açıklama", "Miktar", "Birim"],
        general,
    )
    add_section(
        "2. VMS Server Detayları",
        ["Bileşen", "Model / Özellik", "Sunucu Başına", "Toplam"],
        vms,
    )
    add_section(
        "3. Recording Server Detayları",
        ["Bileşen", "Model / Özellik", "Sunucu Başına", "Toplam"],
        recording,
    )
    rows.append((
        [
            "Not: RAM türü workbook'ta belirtilmemiş olabilir. "
            "CPU miktarı her sunucu için 1 olarak listelenmiştir."
        ],
        0,
    ))

    root = ET.Element(f"{{{_MAIN_NS}}}worksheet")
    sheet_properties = ET.SubElement(root, f"{{{_MAIN_NS}}}sheetPr")
    ET.SubElement(sheet_properties, f"{{{_MAIN_NS}}}pageSetUpPr", fitToPage="1")
    ET.SubElement(root, f"{{{_MAIN_NS}}}dimension", ref=f"A1:D{len(rows)}")
    views = ET.SubElement(root, f"{{{_MAIN_NS}}}sheetViews")
    ET.SubElement(views, f"{{{_MAIN_NS}}}sheetView", workbookViewId="0", showGridLines="0")
    ET.SubElement(root, f"{{{_MAIN_NS}}}sheetFormatPr", defaultRowHeight="19")
    columns = ET.SubElement(root, f"{{{_MAIN_NS}}}cols")
    for index, width in enumerate((34, 66, 29, 18), start=1):
        ET.SubElement(columns, f"{{{_MAIN_NS}}}col", min=str(index), max=str(index), width=str(width), customWidth="1")

    sheet_data = ET.SubElement(root, f"{{{_MAIN_NS}}}sheetData")
    for row_number, (values, style_id) in enumerate(rows, start=1):
        row_element = ET.SubElement(
            sheet_data,
            f"{{{_MAIN_NS}}}row",
            r=str(row_number),
        )
        if row_number == 1 or style_id == 2:
            row_element.set("ht", "25")
            row_element.set("customHeight", "1")
        for column_number, value in enumerate(values, start=1):
            reference = f"{_column_name(column_number)}{row_number}"
            cell = ET.SubElement(
                row_element,
                f"{{{_MAIN_NS}}}c",
                r=reference,
                s=str(style_id),
            )
            if isinstance(value, (int, float)):
                cell.set("t", "n")
                ET.SubElement(cell, f"{{{_MAIN_NS}}}v").text = str(value)
            else:
                cell.set("t", "inlineStr")
                inline = ET.SubElement(cell, f"{{{_MAIN_NS}}}is")
                text = ET.SubElement(inline, f"{{{_MAIN_NS}}}t")
                text.set(f"{{{_XML_NS}}}space", "preserve")
                text.text = str(value)

    merges = ET.SubElement(
        root,
        f"{{{_MAIN_NS}}}mergeCells",
        count=str(2 + len(section_rows)),
    )
    for row_number in (1, 2, *section_rows):
        ET.SubElement(merges, f"{{{_MAIN_NS}}}mergeCell", ref=f"A{row_number}:D{row_number}")
    ET.SubElement(
        root,
        f"{{{_MAIN_NS}}}printOptions",
        horizontalCentered="1",
        verticalCentered="0",
    )
    ET.SubElement(
        root,
        f"{{{_MAIN_NS}}}pageMargins",
        left="0.25",
        right="0.25",
        top="0.35",
        bottom="0.35",
        header="0.15",
        footer="0.15",
    )
    ET.SubElement(
        root,
        f"{{{_MAIN_NS}}}pageSetup",
        paperSize="9",
        orientation="landscape",
        fitToWidth="1",
        fitToHeight="1",
    )
    ET.SubElement(
        root,
        f"{{{_MAIN_NS}}}headerFooter",
    )
    return root


def write_listing(proposal: dict[str, Any], output_path: Path) -> Path:
    """Write all three Turkish equipment tables on one printable worksheet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(output_path.name + ".tmp")

    content_types = ET.Element(f"{{{_CONTENT_NS}}}Types")
    ET.SubElement(content_types, f"{{{_CONTENT_NS}}}Default", Extension="rels", ContentType="application/vnd.openxmlformats-package.relationships+xml")
    ET.SubElement(content_types, f"{{{_CONTENT_NS}}}Default", Extension="xml", ContentType="application/xml")
    ET.SubElement(content_types, f"{{{_CONTENT_NS}}}Override", PartName="/xl/workbook.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml")
    ET.SubElement(content_types, f"{{{_CONTENT_NS}}}Override", PartName="/xl/worksheets/sheet1.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml")
    ET.SubElement(content_types, f"{{{_CONTENT_NS}}}Override", PartName="/xl/styles.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml")

    package_relationships = ET.Element(f"{{{_PACKAGE_REL_NS}}}Relationships")
    ET.SubElement(package_relationships, f"{{{_PACKAGE_REL_NS}}}Relationship", Id="rId1", Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", Target="xl/workbook.xml")

    workbook = ET.Element(f"{{{_MAIN_NS}}}workbook")
    ET.SubElement(workbook, f"{{{_MAIN_NS}}}bookViews").append(
        ET.Element(f"{{{_MAIN_NS}}}workbookView", activeTab="0")
    )
    sheets = ET.SubElement(workbook, f"{{{_MAIN_NS}}}sheets")
    ET.SubElement(sheets, f"{{{_MAIN_NS}}}sheet", name="Malzeme Listesi", sheetId="1", attrib={f"{{{_REL_NS}}}id": "rId1"})
    workbook_relationships = ET.Element(f"{{{_PACKAGE_REL_NS}}}Relationships")
    ET.SubElement(workbook_relationships, f"{{{_PACKAGE_REL_NS}}}Relationship", Id="rId1", Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet", Target="worksheets/sheet1.xml")
    ET.SubElement(workbook_relationships, f"{{{_PACKAGE_REL_NS}}}Relationship", Id="rId2", Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", Target="styles.xml")

    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", ET.tostring(content_types, encoding="utf-8", xml_declaration=True))
            archive.writestr("_rels/.rels", ET.tostring(package_relationships, encoding="utf-8", xml_declaration=True))
            archive.writestr("xl/workbook.xml", ET.tostring(workbook, encoding="utf-8", xml_declaration=True))
            archive.writestr("xl/_rels/workbook.xml.rels", ET.tostring(workbook_relationships, encoding="utf-8", xml_declaration=True))
            archive.writestr("xl/styles.xml", ET.tostring(_style_sheet(), encoding="utf-8", xml_declaration=True))
            archive.writestr("xl/worksheets/sheet1.xml", ET.tostring(_worksheet_xml(proposal), encoding="utf-8", xml_declaration=True))
        temporary_path.replace(output_path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
    return output_path
