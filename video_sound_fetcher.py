import hashlib
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


def _seeded_choice(items, seed):
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return items[int(digest[:8], 16) % len(items)]


def choose_reel_type(seed: str) -> str:
    override = os.environ.get("CINEMATIC_REEL_TYPE", "").strip()
    if override in REEL_TYPES:
        return override
    return _seeded_choice(REEL_TYPES, seed)


def cinematic_script(reel_type, car1, car2):
    if reel_type == "sound_battle":
        return {
            "title": "QULAĞIN HANSINI SEÇİR?",
            "cues": ["SOYUQ START", "REV", "DRIVE-BY", "TUNEL SƏSİ", f"{car1} YOXSA {car2}?"],
            "caption": f"Qulağın hansını seçir: {car1} yoxsa {car2}? Səsi hiss et, tərəfini şərhdə yaz.",
        }
    if reel_type == "night_pov":
        return {
            "title": "BİR GECƏLİK AÇAR",
            "cues": ["GECƏ POV", "SÜKAN", "DASHBOARD", "SƏS", "HANSINI GÖTÜRƏRDİN?"],
            "caption": f"Bir gecəlik açar səndə olsa hansını götürərdin: {car1} yoxsa {car2}? Sol yoxsa sağ?",
        }
    if reel_type == "hidden_features":
        return {
            "title": "GİZLİ FUNKSİYALAR",
            "cues": ["BUNU BİLİRDİN?", "LAUNCH", "DRIFT MODE", "AMBIENT", "HANSI DAHA MARAQLIDIR?"],
            "caption": f"{car1} və {car2} sadəcə rəqəm deyil. Hansının gizli funksiyaları sənə daha maraqlı gəldi?",
        }
    if reel_type == "owner_experience":
        return {
            "title": "SAHİB TƏCRÜBƏSİ",
            "cues": ["YANACAQ", "SERVİS", "ETİBAR", "GÜNDƏLİK RAHATLIQ", "HƏR GÜN HANSI?"],
            "caption": f"Kağız üzərində yox, real istifadə üçün hansını seçərdin: {car1} yoxsa {car2}?",
        }
    if reel_type == "guess_the_car":
        return {
            "title": "HANSI MAŞINDIR?",
            "cues": ["FƏRƏLƏRƏ BAX", "SƏSİ DİNLƏ", "SALONU TANIDIN?", "3...2...1", "CAVABI ŞƏRHƏ YAZ"],
            "caption": "Səsi və detalları tanıdın? Maşını şərhdə yaz, sonra cavabı yoxla.",
        }
    if reel_type == "supercar_facts":
        return {
            "title": "5 SƏRT FAKT",
            "cues": ["1 FAKT", "2 FAKT", "3 FAKT", "4 FAKT", "BUNU BİLİRDİN?"],
            "caption": "Supercar dünyasında rəqəmlərdən də maraqlı detallar var. Hansı fakt səni təəccübləndirdi?",
        }
    if reel_type == "expensive_mistakes":
        return {
            "title": "BAHALI SƏHVLƏR",
            "cues": ["ALMAMIŞDAN ƏVVƏL", "SERVİSİ YOXLAT", "TARİXÇƏ VACİBDİR", "SƏSƏ ALDANMA", "BUNU SAXLA"],
            "caption": "Bahalı maşın alanda ən böyük səhv təkcə qiymətə baxmaqdır. Hansı səhvi ən çox görmüsən?",
        }
    if reel_type == "which_buy":
        return {
            "title": "HANSINI ALARDIN?",
            "cues": ["$30K", "$50K", "$80K", "$150K", "QƏRARINI YAZ"],
            "caption": f"Büdcə səndə olsa hansını alardın: {car1} yoxsa {car2}? Cavabı qısa yaz.",
        }
    if reel_type == "engine_sound_quiz":
        return {
            "title": "SƏSİ TANIDIN?",
            "cues": ["3 SANİYƏ DİNLƏ", "HANSI MÜHƏRRİK?", "V8?", "TURBO?", "CAVABI YAZ"],
            "caption": "Mühərrik səsini tanıdın? Cavabı şərhdə yaz.",
        }
    if reel_type == "drag_race_result":
        return {
            "title": "DRAG NƏTİCƏSİ",
            "cues": ["3", "2", "1", "LAUNCH", "SƏNİN QALİBİN?"],
            "caption": f"Start xəttində hansına güvənərdin: {car1} yoxsa {car2}?",
        }
    if reel_type == "interior_battle":
        return {
            "title": "SALON QALİBİ?",
            "cues": ["SÜKAN", "EKRAN", "AMBIENT", "OTURACAQ", f"{car1} YOXSA {car2}?"],
            "caption": f"Salon qalibi hansıdır: {car1} yoxsa {car2}? Premium hissi hansı daha yaxşı verir?",
        }
    if reel_type == "exterior_details":
        return {
            "title": "DETAL DÖYÜŞÜ",
            "cues": ["FƏRƏLƏR", "DİSKLƏR", "ARXA İŞIQLAR", "EGZOZ", "DİZAYN QALİBİ?"],
            "caption": f"Detallarda hansı daha güclüdür: {car1} yoxsa {car2}?",
        }
    if reel_type == "satisfaction":
        return {
            "title": "AVTO ASMR",
            "cues": ["QAPI SƏSİ", "START", "DÜYMƏLƏR", "GEAR", "BU HİSSİ SEVİRSƏN?"],
            "caption": "Maşın adamı bu səsləri başa düşür. Ən xoş səs hansıdır?",
        }
    if reel_type == "what_change":
        return {
            "title": "NƏYİ DƏYİŞƏRDİN?",
            "cues": ["BU SƏNİN OLSA", "İLK MOD?", "DİSK?", "SƏS?", "ŞƏRHƏ YAZ"],
            "caption": f"{car1} və ya {car2} sənin olsa ilk nəyi dəyişərdin?",
        }
    if reel_type == "history":
        return {
            "title": "NİYƏ HÖRMƏT EDİRLƏR?",
            "cues": ["KÖKÜ", "NƏSİLLƏR", "SÜRÜŞ", "STATUS", "SƏN RAZISAN?"],
            "caption": "Bəzi maşınlara sadəcə performansa görə yox, tarixə görə hörmət edirlər. Sən razısan?",
        }
    if reel_type == "surprising_fact":
        return {
            "title": "GÖZLƏNMƏZ FAKT",
            "cues": ["BUNU ÇOXU BİLMİR", "RƏQƏMƏ BAX", "HİSS BAŞQADIR", "SÜRPRİZ", "RAZISAN?"],
            "caption": "Bəzən ən güclü görünən maşın ən ağıllı seçim olmur. Sən razısan?",
        }
    if reel_type == "dream_garage":
        return {
            "title": "DREAM GARAGE",
            "cues": ["$500K BÜDCƏ", "3 MAŞIN SEÇ", "GÜNDƏLİK", "HƏFTƏSONU", "SİYAHINI YAZ"],
            "caption": "$500K büdcən olsa qarajına hansı 3 maşını qoyardın?",
        }
    if reel_type == "fail_vs_win":
        return {
            "title": "FAIL YOXSA WIN?",
            "cues": ["ƏN YAXŞI DETAL", "ƏN ZƏİF DETAL", "DİZAYN", "SƏS", "SƏNİN FİKRİN?"],
            "caption": "Bu dizayn win-dir, yoxsa fail? Sənin fikrin daha maraqlıdır.",
        }
    if reel_type == "real_verdict":
        return {
            "title": "REAL VERDICT",
            "cues": ["MƏN OLSAYDIM", "1 SƏBƏB", "2 SƏBƏB", "3 SƏBƏB", "RAZISAN?"],
            "caption": f"Mən olsaydım seçimimi 3 səbəblə edərdim. Sən razısan, yoxsa {car1}/{car2} arasında başqa qalib var?",
        }
    if reel_type == "pov_buying":
        return {
            "title": "$120K SƏNDƏDİR",
            "cues": ["PUL SƏNDƏDİR", "5", "4", "3", "TƏK BİRİNİ SEÇ"],
            "caption": f"Sənə $120K verdim. Tək birini seç: {car1} yoxsa {car2}?",
        }
    return {
        "title": "$100K SEÇİM",
        "cues": ["SƏNƏ $100K VERDİM", "5 SANİYƏ", "SOL?", "SAĞ?", "QƏRARINI YAZ"],
        "caption": f"$100K səndə olsa hansını alardın: {car1} yoxsa {car2}? Qərarını şərhdə yaz.",
    }


def download_cinematic_assets(reel_type, output_dir, max_videos=3, max_sfx=3):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    seed = f"{reel_type}:{int(time.time() // 3600)}"
    queries = list(VIDEO_QUERIES.get(reel_type, VIDEO_QUERIES["pov_decision"]))
    random.Random(seed).shuffle(queries)

    videos = []
    errors = []
    for query in queries:
        if len(videos) >= max_videos:
            break
        for provider in (_download_pexels_video, _download_pixabay_video):
            try:
                path = provider(query, out, len(videos))
                if path and path not in videos:
                    videos.append(path)
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
        "videos": videos[:max_videos],
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
    for item in videos:
        files = item.get("video_files", [])
        ranked = sorted(
            [f for f in files if f.get("file_type") == "video/mp4" and f.get("link")],
            key=lambda f: (
                0 if int(f.get("height") or 0) > int(f.get("width") or 0) else 1,
                -int(f.get("height") or 0),
            ),
        )
        for file_info in ranked:
            path = output_dir / f"pexels_{index}.mp4"
            if _download_file(file_info["link"], path, max_bytes=80 * 1024 * 1024):
                return str(path)
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
                return str(path)
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
                "filter": "duration:[1 TO 15]",
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
