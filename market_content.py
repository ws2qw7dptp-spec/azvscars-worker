import hashlib
import json
import os
import re

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


def normalize_market_car(raw):
    year = int(raw.get("year") or _spec_value(raw, "year") or 0) or None
    engine = _clean(raw.get("engine") or _spec_value(raw, "engine"))
    mileage = _km_label(raw.get("mileage_km") or _spec_value(raw, "mileage"))
    price_label = normalize_price_label(raw.get("price_azn") or raw.get("price"))
    return {
        "name": _clean(raw.get("name")),
        "year": year,
        "engine": engine,
        "mileage": mileage,
        "price_label": price_label,
        "search_query": _clean(raw.get("search_query") or raw.get("name")),
        "note": _clean(raw.get("note")),
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
    opener = "Bakıda bu maşın hazırda təxminən bu qiymətə çıxır." if single else "Bakıda bu maşınlar hazırda təxminən bu qiymətə çıxır."
    utility = "Qiyməti saxla ki, real seçim vaxtı yenidən baxa biləsən." if single else "Qiymətləri saxla ki, real seçim vaxtı yenidən müqayisə edə biləsən."
    lines = [opener, ""]
    for car in cars:
        meta_bits = [str(car["year"]) if car.get("year") else "", car.get("engine", ""), car.get("mileage", "")]
        meta = " | ".join(bit for bit in meta_bits if bit)
        lines.append(f"{car['name']} — {car['price_label']}")
        if meta:
            lines.append(meta)
    lines.extend([
        "",
        utility,
        "Bu qiymətə alınar, yoxsa pass? Səbəbini yaz." if single else "Sən hansını seçərdin və niyə?",
        "Reel-i maşın axtaran dosta göndər: bu deal ona uyğundur?" if single else "Reel-i maşın sevən dosta göndər: ikiniz də eyni maşını seçirsiniz?",
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
