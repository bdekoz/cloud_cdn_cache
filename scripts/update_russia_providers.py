#!/usr/bin/env python3
"""Normalize retained Selectel, Cloud.ru and IXcellerate declarations."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re

from location_common import REPO_ROOT
from russia_enrichment_common import evidence, location, publish_locations, raw_path, soup


class Tables(HTMLParser):
    """Read table cells, including HTML's optional td/th/tr closing tags."""
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tables, self.table, self.row, self.cell = [], None, None, None
        self.feed(text)

    def finish_cell(self):
        if self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None

    def finish_row(self):
        self.finish_cell()
        if self.row is not None:
            self.table.append(self.row)
            self.row = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.table is not None:
                raise ValueError("Nested tables require a separate parser")
            self.table = []
        elif self.table is not None:
            if tag == "tr":
                self.finish_row()
                self.row = []
            elif tag in {"td", "th"}:
                self.finish_cell()
                self.cell = []
            elif self.cell is not None and tag in {"br", "p", "li"}:
                self.cell.append(" ")

    def handle_endtag(self, tag):
        if self.table is None:
            return
        if tag in {"td", "th"}:
            self.finish_cell()
        elif tag == "tr":
            self.finish_row()
        elif tag == "table":
            self.finish_row()
            self.tables.append(self.table)
            self.table = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def selectel_rows():
    document = soup("selectel")
    tables = Tables(raw_path("selectel").read_text()).tables
    panels = [table.find_parent(attrs={"role": "tabpanel"})["value"]
              for table in document.select("table")]
    regions = (("saint-petersburg", "Санкт-Петербург", "Saint Petersburg", 2),
               ("moscow", "Москва", "Moscow", 4),
               ("novosibirsk", "Новосибирск", "Novosibirsk", 1))
    rows = []
    for index, (identity, label, city, zone_count) in enumerate(regions):
        if panels[index] != ("spb", "msk", "nsk")[index] or label not in document.get_text():
            raise ValueError(f"Unexpected Selectel region tab: {panels[index]}")
        region = location("selectel", "selectel", "cloud_region", identity, label,
                          "Selectel", "selectel_cloud", country="RU", city=city,
                          scope=["public_cloud"], properties={"identity_basis": "provider_region_label"})
        rows.append(region)
        table, zones = tables[index], []
        if table[0][1:] != [f"Зона доступности {n}" for n in range(1, zone_count + 1)]:
            raise ValueError("Unexpected Selectel availability-zone headers")
        for number in range(1, zone_count + 1):
            zone = location("selectel", "selectel", "availability_zone", f"{identity}-az-{number}",
                f"{label}: Зона доступности {number}", "Selectel", "selectel_cloud", country="RU", city=city,
                parent=region["record_id"], scope=["public_cloud"],
                properties={"provider_zone_label": f"Зона доступности {number}"})
            rows.append(zone)
            zones.append(zone)
        pools = {}
        for cells in table[1:]:
            if cells[0] == "Пул и сегмент":
                cells = cells[1:]
            if len(cells) > zone_count:
                raise ValueError(f"Unexpected Selectel row: {cells}")
            cells = cells + [""] * (zone_count - len(cells))
            for zone, cell in zip(zones, cells):
                if not cell or cell in {"—", "–"}:
                    continue
                match = re.match(r"((?:ru|gis)-\d+|(?:SPB|MSK|NSK)-\d+)\b", cell)
                if not match:
                    raise ValueError(f"Unknown pool label: {cell}")
                code = match[1]
                entry = pools.setdefault(code, {"availability_zone_record_ids": [], "segments_by_zone": {},
                                               "source_cells": []})
                entry["availability_zone_record_ids"].append(zone["record_id"])
                entry["segments_by_zone"][zone["record_id"]] = re.findall(r"\b(?:ru|gis)-\d+[a-z]\b", cell)
                entry["source_cells"].append(cell)
        for code, properties in sorted(pools.items()):
            rows.append(location("selectel", "selectel", "cloud_resource_pool", code, code,
                "Selectel", "selectel_cloud", country="RU", city=city, code=code,
                parent=region["record_id"], scope=["public_cloud"], properties=properties))
    return rows


def cloudru_rows():
    text = soup("advanced").get_text(" ", strip=True)
    codes = sorted(set(re.findall(r"ru-moscow-1[a-z]", text)))
    if codes != ["ru-moscow-1a", "ru-moscow-1b", "ru-moscow-1c", "ru-moscow-1e"] or "территории России" not in text:
        raise ValueError("Cloud.ru Advanced zone or country declaration changed")
    region = location("advanced", "cloudru", "cloud_region", "advanced-ru-moscow-1", "ru-moscow-1",
        "Cloud.ru", "cloudru_advanced", country="RU", code="ru-moscow-1", scope=["public_cloud"])
    advanced = [region] + [location("advanced", "cloudru", "availability_zone", f"advanced-{code}", code,
        "Cloud.ru", "cloudru_advanced", country="RU", code=code, parent=region["record_id"],
        scope=["public_cloud"], properties={"zone_to_building_mapping_published": False}) for code in codes]
    tables = Tables(raw_path("evolution").read_text()).tables
    table = next(t for t in tables if t[0] == ["Зона доступности", "Идентификатор"])
    if "Вся инфраструктура размещена на территории Российской Федерации" not in soup("evolution_overview").get_text():
        raise ValueError("Evolution country declaration changed")
    evolution = []
    for name, identifier in table[1:]:
        if not re.fullmatch(r"ru\.AZ-[1-3]", name) or not re.fullmatch(r"[a-f0-9-]{36}", identifier):
            raise ValueError("Unexpected Cloud.ru Evolution zone identity")
        evolution.append(location("evolution", "cloudru", "availability_zone", f"evolution-{identifier}", name,
            "Cloud.ru", "cloudru_evolution", country="RU", code=identifier, scope=["public_cloud"],
            properties={"provider_zone_label": name, "country_evidence": evidence("evolution_overview"),
                        "parent_region_not_published_in_source": True,
                        "parent_identity_evidence": evidence("evolution")}))
    if len(evolution) != 3:
        raise ValueError("Unexpected Evolution zone count")
    return advanced, evolution


def ixcellerate_rows():
    paragraphs = [p.get_text(" ", strip=True) for p in soup("ixcellerate").select(".wpb_wrapper p")]
    south = next(p for p in paragraphs if p.startswith("В Южном кампусе"))
    veshki = next(p for p in paragraphs if p.startswith("В Вёшках"))
    north = next(p for p in paragraphs if p.startswith("Северный кампус IXcellerate"))
    guards = ((south, ["работает дата-центр MOS5", "готовится к запуску MOS7", "проектируется MOS6", "планируются новые объекты, включая MOS8"]),
              (veshki, ["готовится к запуску", "MOS11 и MOS12", "разместятся"]),
              (north, ["MOS1, MOS2, MOS3, MOS4", "полностью введённых в эксплуатацию"]))
    if any(phrase not in text for text, phrases in guards for phrase in phrases):
        raise ValueError("IXcellerate lifecycle declaration changed; review before normalization")
    groups = [(north, "Northern", {n: "operational" for n in (1, 2, 3, 4)}),
              (south, "Southern", {5: "operational", 6: "planned", 7: "in_development", 8: "planned"}),
              (veshki, "Veshki", {11: "in_development", 12: "planned"})]
    rows = []
    for paragraph, campus, statuses in groups:
        for number, status in statuses.items():
            code = f"MOS{number}"
            row = location("ixcellerate", "ixcellerate", "data_center", code, code,
                "IXcellerate", "colocation", country="RU", code=code, status=status, scope=["colocation"],
                properties={"campus_label": campus, "lifecycle_basis": "provider_directory_at_retrieval",
                            "current_health_verified": False,
                            "source_paragraph_index": paragraphs.index(paragraph),
                            "source_paragraph_selector": ".wpb_wrapper p",
                            "campus_capacity_not_assigned_to_building": True})
            row["location_precision"] = "unknown"
            rows.append(row)
    return rows


def run(root: Path):
    publish_locations(root, "selectel/russian-hierarchy", selectel_rows(), "selectel",
                      pool_unit="distinct_provider_pool_code", geography="Russian regions only")
    for layer, rows, key in zip(("cloudru/advanced-regions-and-zones", "cloudru/evolution-zones"),
                                cloudru_rows(), ("advanced", "evolution")):
        publish_locations(root, layer, rows, key, zone_to_building_mapping_asserted=False,
            enrichment_sources=[evidence("evolution_overview") | {"source_scope": "provider_declared"}]
            if key == "evolution" else [])
    publish_locations(root, "ixcellerate/data-centers", ixcellerate_rows(), "ixcellerate",
                      lifecycle_basis="provider_directory_at_retrieval", capacity_not_asserted=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    run(parser.parse_args().output_root)
