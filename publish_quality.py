import hashlib
import re

from posting_plan import profile_for


AZ_HASHTAGS = [
    "#azvscars",
    "#bakimasin",
    "#avtobazar",
    "#masinqiymeti",
    "#azerbaycan",
    "#avtomobil",
]

AZN_PER_USD = 1.7


def _clean(text):
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    value = value.replace("kommentə", "şərhə").replace("komment", "şərh")
    value = re.sub(r"\.{2,}", ".", value)
    return value


def _question_for(post_type):
    profile = profile_for(post_type)
    if profile.get("cta"):
        return profile["cta"]
    if post_type == "war":
        return "Hansını öz pulunla alardın və niyə? Qısa yox, səbəb yaz."
    if post_type == "night":
        return "Gecə Bakıda açar səndə olsa hansını götürərdin və niyə?"
    if post_type == "quick":
        return "Bu gün sürmək üçün hansını seçərdin və niyə?"
    if post_type == "cinematic":
        return "Bu çılğın maşın seriyasında növbəti nə görmək istərdin?"
    return "Səncə Bakıda daha ağıllı seçim hansıdır və niyə?"


def _non_question_cta(data, post_type):
    car1 = _clean(data.get("car1_name"))
    car2 = _clean(data.get("car2_name"))
    by_type = {
        "quick": [
            f"{car1} tərəfdarını tag et.",
            f"{car2} sevən dosta bunu göndər.",
            "Sabahkı duel üçün səhifəni izləmədə qal.",
        ],
        "war": [
            "Bu savaşı story-də paylaş, tərəfini göstər.",
            f"{car1} və {car2} davası edən dostu tag et.",
            "Şərhlərə baxmaq üçün postu paylaş və geri qayıt.",
        ],
        "night": [
            "Gecə sürüşü sevən dostuna bunu göndər.",
            "Vizual və səs üçün bu postu paylaş.",
            "Bu cütlüyü story-də paylaş, tərəfini göstər.",
        ],
        "cinematic": [
            "Bu seriyanı izləmək üçün səhifəni izləmədə saxla.",
            "Bu çılğın maşını sevən dosta bunu göndər.",
            "Növbəti epizodu qaçırmamaq üçün bu reel-i yadda saxla.",
        ],
        "main": [
            "Qiymət müqayisəsi lazım olarsa postu yadda saxla.",
            f"{car2} tərəfdarı tanıyırsansa bu postu paylaş.",
            "Sabahkı duel üçün səhifəni izləmədə qal.",
        ],
    }
    choices = by_type.get(post_type) or by_type["main"]
    digest = hashlib.sha256(f"{car1}|{car2}|{post_type}".encode("utf-8")).hexdigest()
    return choices[int(digest[:4], 16) % len(choices)]


def _engagement_goal(post_type):
    profile = profile_for(post_type)
    return f"{profile['primary_goal']} və {profile['secondary_goal']} üçün optimizasiya olunub."


def _format_azn(value):
    amount = int(round(float(value)))
    return f"{amount:,}".replace(",", " ") + " AZN"


def normalize_price_label(value):
    text = _clean(value).upper()
    if not text:
        return text
    if "AZN" in text:
        digits = re.findall(r"\d[\d\s,.]*", text)
        if not digits:
            return text
        compact = digits[0].replace(",", "").replace(" ", "")
        try:
            return _format_azn(float(compact))
        except ValueError:
            return f"{digits[0].replace(',', ' ').strip()} AZN"
    usd_match = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)", text)
    if usd_match:
        usd_value = usd_match.group(1).replace(",", "")
        return _format_azn(float(usd_value) * AZN_PER_USD)
    digits = re.findall(r"\d[\d\s,.]*", text)
    if digits:
        compact = digits[0].replace(",", "").replace(" ", "")
        try:
            return _format_azn(float(compact))
        except ValueError:
            return text
    return text


def _buyer_angle(data):
    title = _clean(data.get("battle_title")).lower()
    stats = " ".join([
        _clean(data.get("slide2_car1_stat")),
        _clean(data.get("slide2_car2_stat")),
        _clean(data.get("slide4_car1_stat")),
        _clean(data.get("slide4_car2_stat")),
    ]).lower()
    names = f"{data.get('car1_name', '')} {data.get('car2_name', '')}".lower()
    text = f"{title} {stats} {names}"
    if any(word in text for word in ["land cruiser", "lexus", "toyota", "etibar"]):
        return "Etibarlılıq, servis və uzunmüddətli saxlama xərcini də düşün."
    if any(word in text for word in ["byd", "zeekr", "nio", "li auto", "tesla", "ev", "elektrik"]):
        return "Texnologiya, enerji xərci və ikinci əl dəyəri burada əsas sualdır."
    if any(word in text for word in ["amg", "m3", "m4", "m5", "rs", "v8", "porsche"]):
        return "Burada rəqəmlərdən çox sürüş hissi və xarakter danışır."
    if any(word in text for word in ["range rover", "g-class", "gle", "x5", "suv"]):
        return "Status, rahatlıq və gündəlik istifadə tərəzidədir."
    return "Marka, qiymət, servis və sürüş hissi eyni anda tərəzidədir."


def build_alt_text(data, media_type="carousel"):
    car1 = _clean(data.get("car1_name") or "sol avtomobil")
    car2 = _clean(data.get("car2_name") or "sag avtomobil")
    title = _clean(data.get("battle_title") or "avtomobil müqayisəsi")
    power1 = _clean(data.get("slide2_car1_stat"))
    power2 = _clean(data.get("slide2_car2_stat"))
    speed1 = _clean(data.get("slide3_car1_stat"))
    speed2 = _clean(data.get("slide3_car2_stat"))
    price1 = _clean(data.get("slide4_car1_stat"))
    price2 = _clean(data.get("slide4_car2_stat"))
    kind = "Reel video" if media_type == "reel" else "Karusel post"
    return (
        f"{kind}: {title}. Sol tərəfdə {car1}, sağ tərəfdə {car2}. "
        f"Güc müqayisəsi: {power1} və {power2}. "
        f"0-100 km/s: {speed1.rstrip('.')} və {speed2.rstrip('.')}. "
        f"Qiymət: {price1.rstrip('.')} və {price2.rstrip('.')}. "
        "Dizayn qara fon, qırmızı vurğu və VS formatındadır."
    )


def build_caption(data, post_type="main", media_type="carousel"):
    profile = profile_for(post_type)
    car1 = _clean(data.get("car1_name"))
    car2 = _clean(data.get("car2_name"))
    base = _clean(data.get("caption"))
    question = _question_for(post_type)
    buyer = _buyer_angle(data)
    power = f"{car1}: {_clean(data.get('slide2_car1_stat'))} | {car2}: {_clean(data.get('slide2_car2_stat'))}"
    speed = f"0-100: {_clean(data.get('slide3_car1_stat'))} vs {_clean(data.get('slide3_car2_stat'))}"
    price = f"Təxmini qiymət müqayisəsi: {normalize_price_label(data.get('slide4_car1_stat'))} vs {normalize_price_label(data.get('slide4_car2_stat'))}"
    if post_type == "quick":
        searchable = f"Öz pulunla seçim: {car1} yoxsa {car2}?"
    elif post_type == "war":
        searchable = f"Bakı sürücüləri üçün dava sualı: {car1} yoxsa {car2}?"
    else:
        searchable = f"{car1} və {car2}: Bakı reallığında hansı daha ağıllıdır?"

    if media_type == "reel":
        follow_reason = "Hər həftə real qiymət, servis və sürücü seçimi üçün @azvscars-ı izlə."
        if post_type == "war":
            follow_reason = "Ən sərt Bakı avto debatları üçün @azvscars-ı izlə."
        elif post_type == "quick":
            follow_reason = "Hər gün qısa alıcı seçimi üçün @azvscars-ı izlə."
        lines = [
            searchable,
            "",
            base,
            price,
            buyer,
            question,
            "Ən yaxşı səbəbi növbəti postda istifadə edə bilərik.",
            follow_reason,
            "",
            " ".join((profile.get("hashtags") or AZ_HASHTAGS)[:6]),
        ]
        return "\n".join(line for line in lines if line is not None).strip()[:2150]

    lines = [
        searchable,
        "",
        base,
        price,
        power,
        speed,
        buyer,
        question,
        "",
        " ".join(profile.get("hashtags") or AZ_HASHTAGS),
    ]
    caption = "\n".join(line for line in lines if line is not None).strip()
    return caption[:2150]


def apply_publish_quality(data, post_type="main", media_type="carousel"):
    enriched = dict(data)
    enriched["slide4_title"] = "BAKI QİYMƏTİ"
    enriched["slide4_car1_stat"] = normalize_price_label(enriched.get("slide4_car1_stat"))
    enriched["slide4_car2_stat"] = normalize_price_label(enriched.get("slide4_car2_stat"))
    enriched["alt_text"] = build_alt_text(enriched, media_type)
    enriched["image_description"] = enriched["alt_text"]
    enriched["caption"] = build_caption(enriched, post_type, media_type)
    enriched["engagement_goal"] = _engagement_goal(post_type)
    enriched["target_audience"] = "Azerbaijan car buyers and car enthusiasts"
    enriched["content_series"] = profile_for(post_type)["series"]
    enriched["posting_profile"] = profile_for(post_type)
    enriched["cta_text"] = _question_for(post_type)
    enriched["content_hook"] = enriched.get("battle_title") or f"{enriched.get('car1_name', '')} vs {enriched.get('car2_name', '')}"
    enriched["trust_rules"] = [
        "no_false_hook",
        "short_real_specs",
        "local_baku_context",
        "single_primary_cta",
        "accessibility_description",
    ]
    return enriched
