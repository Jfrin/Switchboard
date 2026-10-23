import re

EMAIL_RE = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def regex_extract(sender: str, body: str) -> dict[str, str | None]:
    """Deterministic fields used to backfill or sanity-check LLM output."""
    m = EMAIL_RE.search(sender) or EMAIL_RE.search(body)
    phone = PHONE_RE.search(body)
    return {
        "email": m.group(0) if m else None,
        "domain": m.group(1).lower() if m else None,
        "phone": phone.group(0).strip() if phone else None,
    }
