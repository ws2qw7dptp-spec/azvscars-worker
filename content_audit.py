import re
from datetime import datetime, timezone

import cloudflare_storage as cf
from posting_plan import profile_for


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _normalize_model(name):
    value = re.sub(r"\s+", " ", str(name or "")).strip().lower()
    value = re.sub(r"[^a-z0-9əğıöşçü\s-]", "", value)
    return value


def _extract_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})?,?\s*(\d{4})",
        text.lower(),
    )
    if match:
        month = MONTHS[match.group(1)]
        day = int(match.group(2) or 1)
        year = int(match.group(3))
        return datetime(year, month, day).date()
    match = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})", text.lower())
    if match:
        month = MONTHS[match.group(1)]
        year = int(match.group(2))
        return datetime(year, month, 1).date()
    return None


def _recent_sessions(limit=20):
    index = cf.sessions_index()
    if isinstance(index, list):
        return index[:limit]
    return []


def _market_checks(market_cars):
    issues = []
    details = []
    today = datetime.now(timezone.utc).date()
    for car in market_cars or []:
        source_date = _extract_date(car.get("source_date") or car.get("checked_at") or car.get("note"))
        price_type = str(car.get("price_type") or "").strip()
        source = str(car.get("source_name") or car.get("source") or car.get("note") or "").strip()
        if not price_type:
            issues.append(f"{car.get('name', 'market car')}: qiymət tipi göstərilməyib.")
        if not source:
            issues.append(f"{car.get('name', 'market car')}: mənbə göstərilməyib.")
        if not source_date:
            issues.append(f"{car.get('name', 'market car')}: yoxlanılma tarixi tapılmadı.")
        else:
            age_days = (today - source_date).days
            details.append({
                "name": car.get("name", ""),
                "source_date": source_date.isoformat(),
                "age_days": age_days,
                "price_type": price_type,
            })
            if age_days > 45:
                issues.append(f"{car.get('name', 'market car')}: qiymət məlumatı {age_days} günlükdür.")
    return issues, details


def build_quality_report(data, post_type, media_type, source_assets=None):
    profile = profile_for(post_type)
    recent = _recent_sessions(limit=20)
    recent_models = []
    for session in recent:
        recent_models.extend([
            _normalize_model(session.get("car1")),
            _normalize_model(session.get("car2")),
        ])

    current_models = [
        _normalize_model(data.get("car1_name")),
        _normalize_model(data.get("car2_name")),
    ]
    issues = []
    overused_models = []
    for model in {item for item in current_models if item}:
        count = recent_models.count(model)
        if count >= 3:
            overused_models.append({"model": model, "recent_uses": count})
            issues.append(f"'{model}' son 20 postda {count} dəfə istifadə olunub.")

    recent_visual_family = ""
    if recent:
        recent_visual_family = ((recent[0].get("publish_strategy") or {}).get("visual_family") or "").strip()
    current_visual_family = profile.get("visual_family", "")
    if recent_visual_family and current_visual_family and recent_visual_family == current_visual_family:
        issues.append(f"Vizual ailə təkrarı: ardıcıl '{current_visual_family}'.")

    market_issues, market_details = _market_checks(data.get("market_cars") or [])
    issues.extend(market_issues)
    warnings = []

    rights_status = "original_or_licensed"
    if source_assets:
        if any((asset or {}).get("reused_fallback") for asset in source_assets if isinstance(asset, dict)):
            message = "Fallback asset reuse baş verdi; insan yoxlaması tövsiyə olunur."
            if post_type == "night_supercar":
                warnings.append(message)
            else:
                issues.append(message)
        if any((asset or {}).get("source_url") or (asset or {}).get("url") for asset in source_assets if isinstance(asset, dict)):
            rights_status = "external_licensed_or_platform_source"

    language_text = " ".join(
        str(data.get(key) or "")
        for key in ("caption", "battle_title", "content_hook", "cta_text")
    ).lower()
    if "yorum" in language_text or "gonder" in language_text or "yorumlara" in language_text:
        issues.append("Mətn tam Azərbaycan dilində deyil.")

    confidence = "high"
    if issues:
        confidence = "medium" if len(issues) <= 2 else "low"

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "auto_publish_allowed": not issues,
        "confidence": confidence,
        "issues": issues,
        "warnings": warnings,
        "recent_post_window": 20,
        "overused_models": overused_models,
        "market_source_checks": market_details,
        "visual_family": current_visual_family,
        "rights_status": rights_status,
        "media_type": media_type,
    }
    return report
