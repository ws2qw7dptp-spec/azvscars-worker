import hashlib
import json
import os
import random
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests


VIDEO_QUERIES = {
    "sound_battle": ["car burnout night", "muscle car burnout", "car drifting smoke"],
    "night_pov": ["night driving car interior", "car driving at night", "sports car night"],
    "hidden_features": ["luxury car interior buttons", "sports car dashboard", "car launch control"],
    "owner_experience": ["car mechanic garage", "luxury car service", "car fuel dashboard"],
    "guess_the_car": ["car headlights night", "sports car wheel close up", "car dashboard night"],
    "supercar_facts": ["supercar close up", "race car track", "sports car detail"],
    "expensive_mistakes": ["luxury car garage", "car mechanic inspection", "sports car engine"],
    "which_buy": ["luxury car road", "sports car city", "car showroom"],
    "engine_sound_quiz": ["sports car exhaust", "car engine start", "car tachometer"],
    "drag_race_result": ["race car track", "car racing action", "sports car acceleration"],
    "interior_battle": ["luxury car interior night", "sports car dashboard", "ambient lights car"],
    "exterior_details": ["sports car headlights", "car wheel close up", "sports car exhaust"],
    "satisfaction": ["sports car exhaust", "car start button", "gear selector car"],
    "pov_decision": ["fast car driving", "supercar road", "sports car acceleration"],
    "pov_buying": ["luxury car showroom", "sports car road", "car buying"],
    "what_change": ["modified car", "tuner car night", "sports car garage"],
    "history": ["classic sports car", "bmw m3", "mercedes amg"],
    "surprising_fact": ["supercar road", "sports car detail", "race car track"],
    "dream_garage": ["luxury car garage", "supercar showroom", "sports cars"],
    "fail_vs_win": ["car design detail", "luxury car exterior", "sports car front"],
    "real_verdict": ["car driving night", "sports car road", "luxury car city"],
}

CAR_SPECIFIC_TYPES = {
    "sound_battle", "night_pov", "hidden_features", "owner_experience",
    "guess_the_car", "engine_sound_quiz", "drag_race_result",
    "interior_battle", "exterior_details", "satisfaction", "what_change",
    "history", "real_verdict",
}

SFX_QUERIES = [
    "car engine rev",
    "sports car acceleration",
    "v8 engine rev",
    "car drive by",
    "tire screech",
]

REEL_TYPES = [
    "sound_battle",
    "night_pov",
    "hidden_features",
    "owner_experience",
    "guess_the_car",
    "supercar_facts",
    "expensive_mistakes",
    "which_buy",
    "engine_sound_quiz",
    "drag_race_result",
    "interior_battle",
    "exterior_details",
    "satisfaction",
    "pov_decision",
    "pov_buying",
    "what_change",
    "history",
    "surprising_fact",
    "dream_garage",
    "fail_vs_win",
    "real_verdict",
]

CRAZY_REEL_TYPES = [
    "supercar_facts",
    "expensive_mistakes",
    "guess_the_car",
    "surprising_fact",
    "dream_garage",
    "satisfaction",
    "what_change",
]

COMPARISON_REEL_TYPES = {
    "sound_battle",
    "owner_experience",
    "which_buy",
    "drag_race_result",
    "interior_battle",
    "exterior_details",
    "pov_decision",
    "pov_buying",
    "fail_vs_win",
    "real_verdict",
}


def _seeded_choice(items, seed):
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return items[int(digest[:8], 16) % len(items)]


def choose_reel_type(seed: str, mode: str = "mixed") -> str:
    override = os.environ.get("CINEMATIC_REEL_TYPE", "").strip()
    if override in REEL_TYPES:
        return override
    if mode == "crazy":
        return _seeded_choice(CRAZY_REEL_TYPES, seed)
    return _seeded_choice(REEL_TYPES, seed)


def _script(reel_type, title, cues, caption, compare=None):
    is_comparison = reel_type in COMPARISON_REEL_TYPES if compare is None else compare
    return {
        "title": title,
        "cues": cues,
        "caption": caption,
        "is_comparison": is_comparison,
        "theme": "crazy" if not is_comparison else "versus",
        "mystery_label": "ADI NƏDİR?",
        "hook_rule": "Do not reveal car names before the final reveal card.",
    }


def cinematic_script(reel_type, car1, car2):
    if reel_type == "sound_battle":
        return _script(reel_type, "QULAĞIN HANSINI SEÇİR?",
            ["SOYUQ START", "REV", "DRIVE-BY", "TUNEL SƏSİ", "ADI NƏDİR?"],
            f"Qulağın hansını seçir: {car1} yoxsa {car2}? Səsi hiss et, tərəfini şərhdə yaz.")
    if reel_type == "night_pov":
        return _script(reel_type, "BİR GECƏLİK AÇAR",
            ["GECƏ POV", "SÜKAN", "DASHBOARD", "SƏS", "ADI NƏDİR?"],
            f"Bir gecəlik açar səndə olsa hansını götürərdin: {car1} yoxsa {car2}? Sol yoxsa sağ?", compare=False)
    if reel_type == "hidden_features":
        return _script(reel_type, "GİZLİ FUNKSİYALAR",
            ["BUNU BİLİRDİN?", "GİZLİ DÜYMƏ", "SÜRÜŞ MODU", "RAHATLIQ", "ADI NƏDİR?"],
            f"{car1} və {car2} sadəcə rəqəm deyil. Hansının gizli funksiyaları sənə daha maraqlı gəldi?", compare=False)
    if reel_type == "owner_experience":
        return _script(reel_type, "SAHİB TƏCRÜBƏSİ",
            ["YANACAQ", "SERVİS", "ETİBAR", "GÜNDƏLİK RAHATLIQ", "HƏR GÜN HANSI?"],
            f"Kağız üzərində yox, real istifadə üçün hansını seçərdin: {car1} yoxsa {car2}?")
    if reel_type == "guess_the_car":
        return _script(reel_type, "HANSI MAŞINDIR?",
            ["FƏRƏLƏRƏ BAX", "SƏSİ DİNLƏ", "SALONU TANIDIN?", "3...2...1", "ADI NƏDİR?"],
            "Səsi və detalları tanıdın? Maşını şərhdə yaz, sabah cavab və yeni maşın gəlir.", compare=False)
    if reel_type == "supercar_facts":
        return _script(reel_type, "DƏLİ MAŞIN FAKTLARI",
            ["1 ŞOK FAKT", "2 ŞOK FAKT", "BU NORMAL DEYİL", "BUNU GÖRDÜN?", "ADI NƏDİR?"],
            "Bəzi maşınlar artıq avtomobil yox, dəlilik layihəsidir. Hansı detal səni saxladı?", compare=False)
    if reel_type == "expensive_mistakes":
        return _script(reel_type, "DƏLİ MAŞIN SƏHVLƏRİ",
            ["ALMAMIŞDAN ƏVVƏL", "BU SƏSƏ ALDANMA", "SERVİS BOMBASI", "PULU YANDIRIR", "BUNU SAXLA"],
            "Bəzi çılğın maşınlar showroom-da xəyal, servisdə kabus olur. Ən böyük səhv hansıdır?", compare=False)
    if reel_type == "which_buy":
        return _script(reel_type, "HANSINI ALARDIN?",
            ["$30K", "$50K", "$80K", "$150K", "QƏRARINI YAZ"],
            f"Büdcə səndə olsa hansını alardın: {car1} yoxsa {car2}? Cavabı qısa yaz.")
    if reel_type == "engine_sound_quiz":
        return _script(reel_type, "SƏSİ TANIDIN?",
            ["3 SANİYƏ DİNLƏ", "HANSI MÜHƏRRİK?", "V8?", "TURBO?", "ADI NƏDİR?"],
            "Mühərrik səsini tanıdın? Cavabı şərhdə yaz.", compare=False)
    if reel_type == "drag_race_result":
        return _script(reel_type, "DRAG NƏTİCƏSİ",
            ["3", "2", "1", "LAUNCH", "SƏNİN QALİBİN?"],
            f"Start xəttində hansına güvənərdin: {car1} yoxsa {car2}?")
    if reel_type == "interior_battle":
        return _script(reel_type, "SALON QALİBİ?",
            ["SÜKAN", "EKRAN", "AMBIENT", "OTURACAQ", "HANSI SALON?"],
            f"Salon qalibi hansıdır: {car1} yoxsa {car2}? Premium hissi hansı daha yaxşı verir?")
    if reel_type == "exterior_details":
        return _script(reel_type, "DETAL DÖYÜŞÜ",
            ["FƏRƏLƏR", "DİSKLƏR", "ARXA İŞIQLAR", "EGZOZ", "DİZAYN QALİBİ?"],
            f"Detallarda hansı daha güclüdür: {car1} yoxsa {car2}?")
    if reel_type == "satisfaction":
        return _script(reel_type, "DƏLİ MAŞIN ASMR",
            ["QAPI SƏSİ", "START", "REV", "DETAL", "BU HİSSİ SEVİRSƏN?"],
            "Bu artıq normal maşın contenti deyil. Ən çox hansı detalı bir də izlədin?", compare=False)
    if reel_type == "what_change":
        return _script(reel_type, "BU DƏLİDƏ NƏYİ DƏYİŞƏRDİN?",
            ["BU SƏNİN OLSA", "İLK MOD?", "AERODİNAMİKA?", "SƏS?", "ŞƏRHƏ YAZ"],
            "Bu maşın sənin olsa ilk nəyi dəyişərdin? Səbəbi ilə yaz.", compare=False)
    if reel_type == "history":
        return _script(reel_type, "NİYƏ HÖRMƏT EDİRLƏR?",
            ["KÖKÜ", "NƏSİLLƏR", "SÜRÜŞ", "STATUS", "ADI NƏDİR?"],
            "Bəzi maşınlara sadəcə performansa görə yox, tarixə görə hörmət edirlər. Sən razısan?", compare=False)
    if reel_type == "surprising_fact":
        return _script(reel_type, "DƏLİ MAŞIN SÜRPRİZİ",
            ["BUNU ÇOXU BİLMİR", "RƏQƏMƏ BAX", "BU HİSSƏ BAX", "SÜRPRİZ", "RAZISAN?"],
            "Bu maşınla bağlı ən dəlisi gücü deyil. Hansı detal səni daha çox təəccübləndirdi?", compare=False)
    if reel_type == "dream_garage":
        return _script(reel_type, "DƏLİ QARAJ",
            ["$500K BÜDCƏ", "1 DƏLİ MAŞIN", "1 GÜNDƏLİK", "1 ŞOU", "SİYAHINI YAZ"],
            "$500K büdcən olsa qarajına hansı dəlilik maşınını qoyardın? Səbəbi ilə yaz.", compare=False)
    if reel_type == "fail_vs_win":
        return _script(reel_type, "UĞUR YOXSA SƏHV?",
            ["ƏN YAXŞI DETAL", "ƏN ZƏİF DETAL", "DİZAYN", "SƏS", "SƏNİN FİKRİN?"],
            "Bu dizayn win-dir, yoxsa fail? Sənin fikrin daha maraqlıdır.")
    if reel_type == "real_verdict":
        return _script(reel_type, "YEKUN QƏRAR",
            ["MƏN OLSAYDIM", "1 SƏBƏB", "2 SƏBƏB", "3 SƏBƏB", "RAZISAN?"],
            f"Mən olsaydım seçimimi 3 səbəblə edərdim. Sən razısan, yoxsa {car1}/{car2} arasında başqa qalib var?")
    if reel_type == "pov_buying":
        return _script(reel_type, "$120K SƏNDƏDİR",
            ["PUL SƏNDƏDİR", "5", "4", "3", "TƏK BİRİNİ SEÇ"],
            f"Sənə $120K verdim. Tək birini seç: {car1} yoxsa {car2}?")
    return _script(reel_type, "$100K SEÇİM",
        ["SƏNƏ $100K VERDİM", "5 SANİYƏ", "SOL?", "SAĞ?", "QƏRARINI YAZ"],
        f"$100K səndə olsa hansını alardın: {car1} yoxsa {car2}? Qərarını şərhdə yaz.")

def _search_queries(reel_type, car1="", car2=""):
    generic = list(VIDEO_QUERIES.get(reel_type, VIDEO_QUERIES["pov_decision"]))
    if reel_type not in CAR_SPECIFIC_TYPES:
        return generic
    suffixes = {
        "sound_battle": "exhaust rev drive by",
        "night_pov": "night POV interior driving",
        "hidden_features": "interior features",
        "owner_experience": "review driving",
        "guess_the_car": "headlights interior detail",
        "engine_sound_quiz": "engine exhaust sound",
        "drag_race_result": "launch acceleration",
        "interior_battle": "interior ambient lights",
        "exterior_details": "exterior cinematic details",
        "satisfaction": "start button exhaust ASMR",
        "what_change": "modified cinematic",
        "history": "generations history",
        "real_verdict": "review cinematic",
    }
    suffix = suffixes.get(reel_type, "cinematic driving")
    exact = [f"{name} {suffix}" for name in (car1, car2) if name]
    return exact + generic


def download_cinematic_assets(reel_type, output_dir, max_videos=3, max_sfx=3, car1="", car2=""):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    seed = f"{reel_type}:{int(time.time() // 3600)}"
    queries = _search_queries(reel_type, car1, car2)
    exact_count = min(2, len([name for name in (car1, car2) if name]))
    generic = queries[exact_count:]
    random.Random(seed).shuffle(generic)
    queries = queries[:exact_count] + generic

    videos = []
    errors = []
    for query in queries:
        if len(videos) >= max_videos:
            break
        for provider in (_download_pexels_video, _download_pixabay_video):
            try:
                item = provider(query, out, len(videos))
                path = item.get("path") if item else None
                if path and path not in [video["path"] for video in videos]:
                    videos.append(item)
                    break
            except Exception as exc:
                errors.append(f"{provider.__name__}:{query}:{exc}")

    sfx = _local_sfx_files(max_sfx)
    if len(sfx) < max_sfx:
        try:
            sfx.extend(_download_freesound_sfx(out, max_sfx - len(sfx)))
        except Exception as exc:
            errors.append(f"freesound:{exc}")

    return {
        "videos": [item["path"] for item in videos[:max_videos]],
        "sources": [{k: v for k, v in item.items() if k != "path"} for item in videos[:max_videos]],
        "sfx": sfx[:max_sfx],
        "errors": errors[-6:],
    }


def _download_pexels_video(query, output_dir, index):
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        return None
    res = requests.get(
        "https://api.pexels.com/videos/search",
        params={"query": query, "per_page": 8, "orientation": "portrait", "size": "medium"},
        headers={"Authorization": key},
        timeout=20,
    )
    res.raise_for_status()
    videos = res.json().get("videos", [])
    candidates = []
    for item in videos:
        files = item.get("video_files", [])
        ranked = sorted(
            [f for f in files if f.get("file_type") == "video/mp4" and f.get("link")],
            key=lambda f: (
                0 if int(f.get("height") or 0) > int(f.get("width") or 0) else 1,
                -int(f.get("height") or 0),
            ),
        )
        for file_info in ranked[:2]:
            height = int(file_info.get("height") or 0)
            width = int(file_info.get("width") or 0)
            duration = float(item.get("duration") or 0)
            score = (40 if height > width else 0) + min(height, 1920) / 100 + min(duration, 20)
            candidates.append((score, item, file_info))
    for _, item, file_info in sorted(candidates, key=lambda row: row[0], reverse=True):
        path = output_dir / f"pexels_{index}.mp4"
        if _download_file(file_info["link"], path, max_bytes=80 * 1024 * 1024):
            return {
                "path": str(path), "provider": "pexels", "id": str(item.get("id")),
                "query": query, "source_url": item.get("url", ""),
                "creator": (item.get("user") or {}).get("name", ""),
                "width": file_info.get("width"), "height": file_info.get("height"),
                "duration": item.get("duration"),
            }
    return None


def _download_pixabay_video(query, output_dir, index):
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        return None
    res = requests.get(
        "https://pixabay.com/api/videos/",
        params={
            "key": key,
            "q": query,
            "video_type": "film",
            "safesearch": "true",
            "per_page": 10,
            "order": "popular",
        },
        timeout=20,
    )
    res.raise_for_status()
    for item in res.json().get("hits", []):
        video_map = item.get("videos") or {}
        ranked = [video_map.get(k) for k in ("large", "medium", "small", "tiny")]
        ranked = [v for v in ranked if v and v.get("url")]
        ranked.sort(key=lambda v: (0 if int(v.get("height") or 0) > int(v.get("width") or 0) else 1, -int(v.get("height") or 0)))
        for file_info in ranked:
            path = output_dir / f"pixabay_{index}.mp4"
            if _download_file(file_info["url"], path, max_bytes=80 * 1024 * 1024):
                return {
                    "path": str(path), "provider": "pixabay", "id": str(item.get("id")),
                    "query": query, "source_url": item.get("pageURL", ""),
                    "creator": item.get("user", ""), "width": file_info.get("width"),
                    "height": file_info.get("height"), "duration": item.get("duration"),
                }
    return None


def _download_freesound_sfx(output_dir, limit):
    token = os.environ.get("FREESOUND_API_KEY", "").strip()
    if not token or limit <= 0:
        return []
    found = []
    for query in SFX_QUERIES:
        if len(found) >= limit:
            break
        res = requests.get(
            "https://freesound.org/apiv2/search/",
            params={
                "query": query,
                "filter": 'duration:[1 TO 15] license:"Creative Commons 0"',
                "sort": "rating_desc",
                "page_size": 5,
                "fields": "id,name,previews,license,duration,username,url",
            },
            headers={"Authorization": f"Token {token}"},
            timeout=20,
        )
        res.raise_for_status()
        for item in res.json().get("results", []):
            preview = (item.get("previews") or {}).get("preview-hq-mp3")
            if not preview:
                continue
            path = output_dir / f"sfx_{len(found)}.mp3"
            if _download_file(preview, path, max_bytes=10 * 1024 * 1024):
                found.append(str(path))
                break
    return found


def _local_sfx_files(limit):
    base = Path("assets/sfx")
    if not base.exists():
        return []
    files = sorted([p for p in base.iterdir() if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac"}])
    return [str(p) for p in files[:limit]]


def _download_file(url, path, max_bytes):
    with requests.get(url, stream=True, timeout=45) as res:
        res.raise_for_status()
        total = 0
        with open(path, "wb") as f:
            for chunk in res.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    path.unlink(missing_ok=True)
                    return False
                f.write(chunk)
    return path.exists() and path.stat().st_size > 1024
