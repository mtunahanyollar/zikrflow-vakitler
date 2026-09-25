#!/usr/bin/env python3
"""Fetch Diyanet prayer times into one small JSON file per district."""

from __future__ import annotations

import argparse
import json
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from common import get_text

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Mozilla/5.0 (compatible; zikrflow-vakitler/1.0)"
MONTHS = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
    "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}


class PrayerTableParser(HTMLParser):
    def __init__(self, tab_id: str):
        super().__init__(convert_charrefs=True)
        self.tab_id = tab_id
        self.article_depth = 0
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "article" and attributes.get("id") == self.tab_id:
            self.article_depth = 1
        elif self.article_depth and tag == "article":
            self.article_depth += 1
        if not self.article_depth:
            return
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if self.article_depth:
            if tag in ("td", "th") and self.cell is not None and self.row is not None:
                self.row.append(" ".join("".join(self.cell).split()))
                self.cell = None
            elif tag == "tr" and self.row is not None:
                if self.row:
                    self.rows.append(self.row)
                self.row = None
            elif tag == "article":
                self.article_depth -= 1

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def iso_date(value: str) -> str | None:
    fields = value.split()
    if len(fields) < 3:
        return None
    try:
        return f"{int(fields[2]):04d}-{MONTHS[fields[1].casefold()]:02d}-{int(fields[0]):02d}"
    except (KeyError, ValueError):
        return None


def parse_table(html: str, tab_id: str) -> list[dict[str, str]]:
    parser = PrayerTableParser(tab_id)
    parser.feed(html)
    days = []
    for row in parser.rows:
        if len(row) < 8:
            continue
        day = iso_date(row[0])
        if day is None:
            continue
        days.append({
            "t": day, "h": row[1], "imsak": row[2], "gunes": row[3], "ogle": row[4],
            "ikindi": row[5], "aksam": row[6], "yatsi": row[7],
        })
    return days


def fetch(url: str) -> str:
    last_error = None
    for attempt in range(3):
        try:
            return get_text(url, USER_AGENT)
        except Exception as error:
            last_error = error
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(str(last_error))


def districts():
    source = json.loads((ROOT / "iller.json").read_text(encoding="utf-8"))
    for city in source["iller"]:
        for district in city["ilceler"]:
            yield city["ad"], district["ad"], district["id"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Comma-separated district IDs")
    parser.add_argument("--limit", type=int, help="Maximum selected districts")
    args = parser.parse_args()
    selected = set(args.only.split(",")) if args.only else None
    targets = [item for item in districts() if selected is None or item[2] in selected]
    if args.limit is not None:
        targets = targets[:args.limit]
    output_dir = ROOT / "vakitler"
    output_dir.mkdir(exist_ok=True)
    started = time.monotonic()
    successful, failed, fallback = [], [], []
    for index, (city, district, district_id) in enumerate(targets):
        if index:
            time.sleep(1)
        try:
            html = fetch(f"https://namazvakitleri.diyanet.gov.tr/tr-TR/{district_id}/x")
            days = parse_table(html, "tab-2")
            source_tab = "tab-2"
            # Diyanet currently exposes the next calendar year in tab-2 while
            # tab-1 contains the current month.  A yearly table without today is
            # not useful to consumers, so it is treated as insufficient.
            if not days or not any(day["t"] == date.today().isoformat() for day in days):
                days = parse_table(html, "tab-1")
                source_tab = "tab-1"
                fallback.append(district_id)
            if not days:
                raise ValueError("Yıllık ve aylık tabloda geçerli satır yok")
            payload = {"ilceId": district_id, "il": city, "ilce": district, "fetchedAt": date.today().isoformat(), "gunler": days}
            (output_dir / f"{district_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            successful.append({"id": district_id, "source": source_tab, "days": len(days)})
            print(f"OK {district_id}: {len(days)} gün ({source_tab})")
        except Exception as error:
            failed.append({"id": district_id, "error": str(error)})
            print(f"HATA {district_id}: {error}")
    report = {"fetchedAt": date.today().isoformat(), "durationSeconds": round(time.monotonic() - started, 2), "successful": successful, "failed": failed, "monthlyFallback": fallback}
    (ROOT / "fetch_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
