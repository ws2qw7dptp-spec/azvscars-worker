import re


AZ_HASHTAGS = [
    "#azvscars",
    "#azerbaycan",
    "#baku",
    "#avto",
    "#masin",
    "#avtomobil",
    "#avtobazar",
    "#bakucars",
    "#azerbaijancars",
]


def _clean(text):
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    value = value.replace("kommentə", "şərhə").replace("komment", "şərh")
    value = re.sub(r"\.{2,}", ".", value)
    return value


def _question_for(post_type):
    if post_type == "war":
        return "Sol yoxsa sağ? 1 sözlə şərhdə yaz."
    if post_type == "night":
        return "Gecə Bakıda açar səndə olsa hansını götürərdin?"
    if post_type == "quick":
        return "Bu gün sürmək üçün hansını seçərdin?"
    if post_type == "cinematic":
        return "Səsə, görüntüyə və hissə görə sənin tərəfin hansıdır?"
    return "Səncə Bakıda daha ağıllı seçim hansıdır?"


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
    car1 = _clean(data.get("car1_name"))
    car2 = _clean(data.get("car2_name"))
    base = _clean(data.get("caption"))
    question = _question_for(post_type)
    buyer = _buyer_angle(data)
    power = f"{car1}: {_clean(data.get('slide2_car1_stat'))} | {car2}: {_clean(data.get('slide2_car2_stat'))}"
    speed = f"0-100: {_clean(data.get('slide3_car1_stat'))} vs {_clean(data.get('slide3_car2_stat'))}"

    lines = [
        base,
        "",
        power,
        speed,
        buyer,
        question,
        "Real seçim edənlər üçün: qiymətə yox, gündəlik istifadə + servis + xarakterə bax.",
        "",
        "Təsvir: " + build_alt_text(data, media_type)[:420],
        "",
        " ".join(AZ_HASHTAGS),
    ]
    caption = "\n".join(line for line in lines if line is not None).strip()
    return caption[:2150]


def apply_publish_quality(data, post_type="main", media_type="carousel"):
    enriched = dict(data)
    enriched["alt_text"] = build_alt_text(enriched, media_type)
    enriched["image_description"] = enriched["alt_text"]
    enriched["caption"] = build_caption(enriched, post_type, media_type)
    enriched["target_audience"] = "Azerbaijan car buyers and car enthusiasts"
    enriched["trust_rules"] = [
        "no_false_hook",
        "short_real_specs",
        "local_baku_context",
        "comment_question",
        "accessibility_description",
    ]
    return enriched
