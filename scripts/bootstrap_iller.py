#!/usr/bin/env python3
"""Build the immutable district catalogue used by the fetcher."""

from __future__ import annotations

import argparse
import json
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from common import get_json

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "zikrflow-vakitler/1.0 (https://github.com/mtunahanyollar/zikrflow-vakitler)"
MIRROR = "https://ezanvakti.emushaf.net"
WIKIDATA = "https://query.wikidata.org/sparql"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


def turkish_title(value: str) -> str:
    """Title-case all-uppercase Turkish source names without losing dotted I."""
    lower = value.replace("I", "ı").replace("İ", "i").lower()
    def upper_initial(word: str) -> str:
        if word.startswith("i"):
            return "İ" + word[1:]
        if word.startswith("ı"):
            return "I" + word[1:]
        return word[:1].upper() + word[1:]

    return " ".join(upper_initial(word) for word in lower.split())


def key(value: str) -> str:
    value = value.replace("I", "ı").replace("İ", "i").lower()
    value = unicodedata.normalize("NFKD", value)
    return "".join(char for char in value if not unicodedata.combining(char)).replace(" ", "")


def wikidata_coordinates() -> dict[str, tuple[float, float]]:
    query = """
    SELECT ?itemLabel ?coord WHERE {
      ?item wdt:P31/wdt:P279* wd:Q1070380 ; wdt:P625 ?coord .
      SERVICE wikibase:label { bd:serviceParam wikibase:language \"tr\". }
    }
    """
    try:
        data = get_json(f"{WIKIDATA}?{urlencode({'query': query, 'format': 'json'})}", USER_AGENT, 90)
    except Exception as error:  # source is best-effort; Nominatim is the documented fallback
        print(f"Wikidata koordinatları alınamadı: {error}", file=sys.stderr)
        return {}
    coordinates = {}
    for row in data["results"]["bindings"]:
        point = row["coord"]["value"].removeprefix("Point(").removesuffix(")").split()
        if len(point) == 2:
            coordinates[key(row["itemLabel"]["value"])] = (round(float(point[1]), 6), round(float(point[0]), 6))
    return coordinates


def nominatim_coordinate(ilce: str, il: str) -> tuple[float, float] | None:
    params = urlencode({"q": f"{ilce}, {il}, Türkiye", "format": "json", "limit": 1})
    try:
        result = get_json(f"{NOMINATIM}?{params}", USER_AGENT)
    except Exception as error:
        print(f"Nominatim hatası ({ilce}, {il}): {error}", file=sys.stderr)
        return None
    if not result:
        return None
    return (round(float(result[0]["lat"]), 6), round(float(result[0]["lon"]), 6))


def apply_overrides(output: list[dict]) -> list[dict]:
    """Kaynaktaki yazım hatalarını ve eksik koordinatları overrides.json ile düzelt (kimlik bazlı)."""
    path = Path(__file__).resolve().parent.parent / "overrides.json"
    if not path.exists():
        return output
    overrides = json.loads(path.read_text(encoding="utf-8")).get("ilceler", {})
    for il in output:
        for ilce in il["ilceler"]:
            fix = overrides.get(str(ilce["id"]))
            if fix:
                ilce.update(fix)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-nominatim", action="store_true", help="Only use Wikidata (for quick diagnostics).")
    args = parser.parse_args()

    cities = get_json(f"{MIRROR}/sehirler/2", USER_AGENT)
    coordinates = wikidata_coordinates()
    missing = []
    output = []
    for city in cities:
        city_name = turkish_title(city["SehirAdi"])
        districts = get_json(f"{MIRROR}/ilceler/{city['SehirID']}", USER_AGENT)
        records = []
        for district in districts:
            district_name = turkish_title(district["IlceAdi"])
            coordinate = coordinates.get(key(district_name))
            if coordinate is None and not args.skip_nominatim:
                coordinate = nominatim_coordinate(district_name, city_name)
                time.sleep(1)
            record = {"id": str(district["IlceID"]), "ad": district_name}
            if coordinate is None:
                missing.append({"il": city_name, "ilce": district_name, "id": record["id"]})
            else:
                record["lat"], record["lon"] = coordinate
            records.append(record)
        records.sort(key=lambda item: (key(item["ad"]) != key(city_name), key(item["ad"])))
        output.append({"id": str(city["SehirID"]), "ad": city_name, "ilceler": records})

    (ROOT / "iller.json").write_text(
        json.dumps({"version": 1, "generatedAt": date.today().isoformat(), "iller": apply_overrides(output)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = ["# Bootstrap report", "", f"Koordinatsız ilçe sayısı: {len(missing)}", ""]
    report.extend(f"- {item['il']} / {item['ilce']} ({item['id']})" for item in missing)
    (ROOT / "bootstrap_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"{len(output)} il, {sum(len(city['ilceler']) for city in output)} ilçe; {len(missing)} koordinatsız")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
