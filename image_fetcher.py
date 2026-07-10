"""
image_fetcher.py
Fetches the best available image from Wikipedia for a given car search query.
Accepts a full output_path so callers can store images wherever they want
(temp dir, assets/, etc.).
"""
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

    commons_url = _fetch_commons_image(query)
    if commons_url:
        print(f"   Wikimedia Commons match: {commons_url}")
        if _download_and_validate(commons_url, output_path):
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


def _fetch_commons_image(query: str) -> str | None:
    """Find a relevant car image on Wikimedia Commons before Wikipedia fallback."""
    try:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 12,
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
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
            url = info.get("url")
            if not url or mime not in {"image/jpeg", "image/png"} or width < 600 or height < 400:
                continue
            title = page.get("title", "")
            score = _title_score(query, title)
            if "side" in query.lower() and width > height:
                score += 2
            candidates.append((score, width * height, title, url))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        print(f"   Commons page: {candidates[0][2]}")
        return candidates[0][3]
    except Exception as e:
        print(f"⚠️  Commons image search failed for '{query}': {e}")
        return None


def _title_score(query: str, title: str) -> int:
    ignored = {"side", "view", "car", "cars", "the", "and", "benz", "mercedes-benz"}
    query_tokens = {
        t for t in _normalize(query).split()
        if len(t) > 1 and t not in ignored
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
        return True
    except Exception:
        return False


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
