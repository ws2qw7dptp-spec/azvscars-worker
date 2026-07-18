import hashlib
import json
import os
import re
from datetime import datetime

from publish_quality import AZ_HASHTAGS, normalize_price_label


DATA_PATH = os.path.join(os.path.dirname(__file__), "cars.json")


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _km_label(value):
    digits = re.sub(r"[^\d]", "", str(value or ""))
    if not digits:
        return ""
    return f"{int(digits):,}".replace(",", " ") + " km"


def _spec_value(raw, key):
    for item in raw.get("specs", []):
        label = _clean(item.get("label")).lower()
        if key in label:
            return _clean(item.get("value"))
    return ""


def _parse_note_details(note):
    text = _clean(note)
    lower = text.lower()
    price_type = "Elan qiyməti" if "listing" in lower or "elan" in lower else "Bazar aralığı"
    source_name = "İctimai elan"
    if "screenshot" in lower:
        source_name = "İstifadəçi göndərişi"
    elif "listing" in lower:
        source_name = "İctimai elan"
    date_match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{0,2},?\s*\d{4}",
        lower,
    )
    source_date = ""
    if date_match:
        source_date = date_match.group(0).title()
    else:
        month_year = re.search(
            r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}",
            lower,
        )
        if month_year:
            source_date = month_year.group(0).title()
    checked_at = datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "price_type": price_type,
        "source_name": source_name,
        "source_date": source_date,
        "checked_at": checked_at,
    }


def normalize_market_car(raw):
    year = int(raw.get("year") or _spec_value(raw, "year") or 0) or None
    engine = _clean(raw.get("engine") or _spec_value(raw, "engine"))
    mileage = _km_label(raw.get("mileage_km") or _spec_value(raw, "mileage"))
    price_label = normalize_price_label(raw.get("price_azn") or raw.get("price"))
    details = _parse_note_details(raw.get("note"))
    return {
        "name": _clean(raw.get("name")),
        "year": year,
        "engine": engine,
        "mileage": mileage,
        "price_label": price_label,
        "search_query": _clean(raw.get("search_query") or raw.get("name")),
        "note": _clean(raw.get("note")),
        "source": _clean(raw.get("source")),
        "source_name": _clean(raw.get("source_name")) or details["source_name"],
        "source_date": _clean(raw.get("source_date")) or details["source_date"],
        "price_type": _clean(raw.get("price_type")) or details["price_type"],
        "checked_at": _clean(raw.get("checked_at")) or details["checked_at"],
    }


def load_market_cars(path=DATA_PATH):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    cars = [normalize_market_car(item) for item in data]
    return [item for item in cars if item["name"] and item["price_label"]]


def pick_market_batch(seed, count=3):
    cars = load_market_cars()
    if not cars:
        raise RuntimeError("cars.json is empty.")
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    start = int(digest[:8], 16) % len(cars)
    picks = []
    for idx in range(min(count, len(cars))):
        picks.append(cars[(start + idx) % len(cars)])
    return picks


def build_market_caption(cars):
    single = len(cars) == 1
    opener = "Bu pula dəyər?" if single else "Bakıda bu qiymətlər normaldır?"
    utility = "Maşın baxırsansa bunu yadda saxla." if single else "Bu müqayisəni yadda saxla."
    lines = [opener, ""]
    for car in cars:
        meta_bits = [str(car["year"]) if car.get("year") else "", car.get("engine", ""), car.get("mileage", "")]
        meta = " | ".join(bit for bit in meta_bits if bit)
        lines.append(f"{car['name']} — {car['price_label']}")
        if meta:
            lines.append(meta)
        lines.append(f"Qiymət tipi: {car.get('price_type') or 'Elan qiyməti'}")
        source_name = car.get("source_name") or car.get("source") or "Mənbə qeyd olunmayıb"
        source_date = car.get("source_date") or car.get("checked_at") or "Tarix yoxdur"
        lines.append(f"Mənbə: {source_name}")
        lines.append(f"Yoxlanılıb: {source_date}")
    lines.extend([
        "",
        utility,
        "Bu qiymətə alardın, yoxsa keçərdin? Səbəbini yaz." if single else "Sən hansını seçərdin və niyə?",
        "",
        " ".join(AZ_HASHTAGS + ["#masinqiymeti", "#turboaz", "#bakimasinbazari"]),
    ])
    return "\n".join(lines).strip()[:2150]


def build_market_alt_text(cars):
    parts = []
    for car in cars:
        bits = [car["name"], car["price_label"]]
        if car.get("year"):
            bits.append(str(car["year"]))
        if car.get("engine"):
            bits.append(car["engine"])
        if car.get("mileage"):
            bits.append(car["mileage"])
        parts.append(", ".join(bits))
    joined = " / ".join(parts)
    return f"Reel video: Bakı bazarı qiymət seçimi. {joined}."
