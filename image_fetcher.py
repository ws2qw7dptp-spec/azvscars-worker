"""
image_fetcher.py
Fetches the best available image from Wikipedia for a given car search query.
Accepts a full output_path so callers can store images wherever they want
(temp dir, assets/, etc.).
"""
import hashlib
import requests
import os
import urllib.parse
from PIL import Image

HEADERS = {"User-Agent": "AZvsCarsBot/1.0 (islammuradovbusiness@gmail.com)"}


def fetch_wikipedia_image(query: str, output_path: str) -> str:
    """
    Search Wikipedia for `query`, grab the article's main high-res image,
    and save it to `output_path` (a full file path, e.g. /tmp/abc/car1.jpg).
    Returns the output_path on success, or a fallback dummy image path.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    result = fetch_unique_car_image(query, output_path)
    if result:
        return output_path

    search_url = (
        "https://en.wikipedia.org/w/api.php"
        "?action=query&list=search"
        f"&srsearch={urllib.parse.quote(query)}"
        "&utf8=&format=json"
    )

    try:
        search_res = requests.get(search_url, headers=HEADERS, timeout=10).json()
        results = search_res.get("query", {}).get("search", [])
        if not results:
            print(f"⚠️  No Wikipedia page found for: {query}")
            return _dummy(output_path, query)

        title = results[0]["title"]
        print(f"   Wikipedia page: {title}")

        img_api = (
            "https://en.wikipedia.org/w/api.php"
            "?action=query&prop=pageimages&format=json"
            "&piprop=original"
            f"&titles={urllib.parse.quote(title)}"
        )
        img_res = requests.get(img_api, headers=HEADERS, timeout=10).json()
        pages   = img_res.get("query", {}).get("pages", {})
        page    = next(iter(pages.values()))

        if "original" not in page:
            print(f"⚠️  No image on Wikipedia page: {title}")
            return _dummy(output_path, query)

        img_url = page["original"]["source"]
        print(f"   Downloading: {img_url}")

        if _download_and_validate(img_url, output_path):
            return output_path
        print("⚠️  Downloaded file is not a valid image — using dummy.")
        return _dummy(output_path, query)
    except Exception as e:
        print(f"❌ Image fetch error for '{query}': {e}")
        return _dummy(output_path, query)


def fetch_unique_car_image(
    query: str,
    output_path: str,
    *,
    seed: str = "",
    excluded_urls=None,
    excluded_hashes=None,
) -> dict | None:
    """Download a high-resolution Commons image that is new to the recent asset set."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    excluded_urls = set(excluded_urls or [])
    excluded_hashes = set(excluded_hashes or [])
    candidates = _fetch_commons_candidates(query)
    if not candidates:
        return None

    # Stable jitter prevents every run choosing the same hero while preserving relevance.
    for item in candidates:
        jitter = int(hashlib.sha256(f"{seed}:{item['url']}".encode()).hexdigest()[:6], 16) / 0xFFFFFF
        item["rank"] = item["score"] * 100 + min(item["pixels"] / 1_000_000, 18) + jitter * 24
    candidates.sort(key=lambda item: item["rank"], reverse=True)

    for item in candidates[:24]:
        if item["url"] in excluded_urls:
            continue
        if not _download_and_validate(item["url"], output_path):
            continue
        fingerprint = image_fingerprint(output_path)
        if not fingerprint:
            continue
        if any(_hash_distance(fingerprint, old) <= 7 for old in excluded_hashes if old):
            continue
        print(f"   Commons selected: {item['title']} ({item['width']}x{item['height']})")
        return dict(item, fingerprint=fingerprint, path=output_path)

    return None

def _fetch_commons_candidates(query: str) -> list[dict]:
    """Return ranked, photo-only car candidates from Wikimedia Commons."""
    try:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 40,
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "iiurlwidth": 2200,
            "format": "json",
        }
        res = requests.get("https://commons.wikimedia.org/w/api.php", params=params, headers=HEADERS, timeout=10)
        res.raise_for_status()
        pages = res.json().get("query", {}).get("pages", {})
        candidates = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            mime = info.get("mime", "")
            width = int(info.get("width") or 0)
            height = int(info.get("height") or 0)
            url = info.get("thumburl") or info.get("url")
            title = page.get("title", "")
            title_norm = _normalize(title)
            blocked = {
                "logo", "badge", "emblem", "interior", "engine", "diagram", "drawing", "icon", "toy",
                "taxi", "police", "wreck", "damaged", "rally", "race",
            }
            if (
                not url
                or mime not in {"image/jpeg", "image/png"}
                or width < 1200
                or height < 650
                or any(word in title_norm.split() for word in blocked)
            ):
                continue
            score = _title_score(query, title)
            if score <= 0:
                continue
            candidates.append({
                "score": score,
                "pixels": width * height,
                "title": title,
                "url": url,
                "width": width,
                "height": height,
            })
        return candidates
    except Exception as e:
        print(f"⚠️  Commons image search failed for '{query}': {e}")
        return []


def _fetch_commons_image(query: str) -> str | None:
    """Compatibility helper for older callers."""
    candidates = _fetch_commons_candidates(query)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item["score"], item["pixels"]), reverse=True)
    return candidates[0]["url"]


def _title_score(query: str, title: str) -> int:
    ignored = {"side", "view", "car", "cars", "the", "and", "benz", "mercedes-benz"}
    query_tokens = {
        t for t in _normalize(query).split()
        if len(t) > 1 and t not in ignored and not t.isdigit()
    }
    title_norm = _normalize(title)
    return sum(3 if token in title_norm else 0 for token in query_tokens)


def _normalize(text: str) -> str:
    keep = []
    for ch in text.lower():
        keep.append(ch if ch.isalnum() else " ")
    return " ".join("".join(keep).split())


def _download_and_validate(img_url: str, output_path: str) -> bool:
    try:
        img_bytes = requests.get(img_url, headers=HEADERS, timeout=20).content
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        with Image.open(output_path) as test_img:
            test_img.load()
            if test_img.width < 1080 or test_img.height < 600:
                return False
        return True
    except Exception:
        return False


def image_fingerprint(path: str) -> str:
    """64-bit difference hash used to catch resized or recompressed duplicates."""
    try:
        with Image.open(path) as img:
            gray = img.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(gray.getdata())
        bits = []
        for y in range(8):
            row = pixels[y * 9:(y + 1) * 9]
            bits.extend(row[x] > row[x + 1] for x in range(8))
        value = sum((1 << idx) for idx, bit in enumerate(bits) if bit)
        return f"{value:016x}"
    except Exception:
        return ""


def _hash_distance(left: str, right: str) -> int:
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except (TypeError, ValueError):
        return 64


def _dummy(path: str, text: str) -> str:
    """Creates a dark placeholder image when a real photo can't be found."""
    from PIL import ImageDraw, ImageFont
    img  = Image.new("RGB", (1080, 720), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font = ImageFont.truetype(os.path.join(base_dir, "BarlowCondensed-Bold.ttf"), 60)
    except Exception:
        font = ImageFont.load_default()
    draw.text((80, 280), f"IMAGE NOT FOUND\n{text}", font=font, fill=(120, 120, 120))
    img.save(path)
    return path
