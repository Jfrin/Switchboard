"""Generate eval/dataset.jsonl: synthetic labeled inquiries (no real customer data).

    docker compose run --rm api python scripts/make_dataset.py

Expected team labels are derived from the same rules as config/routing.yaml
(territory + 500-employee enterprise threshold), so keep them in sync.
"""

import json
import random
from pathlib import Path

random.seed(7)

TERRITORIES = {
    "APAC": ["SG", "PH", "AU", "JP"],
    "EMEA": ["GB", "DE", "FR"],
    "AMER": ["US", "CA", "BR"],
}
IN_TERRITORY = [c for cs in TERRITORIES.values() for c in cs]
OUT_OF_TERRITORY = ["IN", "ZA", "MX", "AE"]
THRESHOLD = 500

COUNTRY_NAME = {
    "SG": "Singapore", "PH": "the Philippines", "AU": "Australia", "JP": "Japan",
    "GB": "the United Kingdom", "DE": "Germany", "FR": "France",
    "US": "the United States", "CA": "Canada", "BR": "Brazil",
    "IN": "India", "ZA": "South Africa", "MX": "Mexico", "AE": "the United Arab Emirates",
}

COMPANIES = [
    "Northwind Freight", "Bluepeak Analytics", "Harborline Logistics", "Quillstone Labs",
    "Redwood Dental Group", "Tidewater Foods", "Lumen Robotics", "Ashgrove Insurance",
    "Copperfield Retail", "Vantage Marine", "Sunridge Solar", "Ironbark Construction",
    "Pinecrest Health", "Meridian Travel", "Foxglove Bakery", "Granite Peak Mining",
    "Orchid Pharma", "Skyline Couriers", "Evergreen Education", "Driftwood Studios",
    "Cobalt Payments", "Maple Ridge Realty", "Silverleaf Hotels", "Falcon Aviation Services",
    "Brightwater Utilities", "Stonebridge Capital", "Kestrel Security", "Lakeshore Textiles",
    "Moonrise Gaming", "Palisade Software", "Quarry Lane Media", "Riverbend Agritech",
    "Saffron Kitchens", "Thistle Energy", "Umber Design", "Verdant Farms",
    "Wexford Engineering", "Yarrow Wellness", "Zephyr Telecom", "Altamira Biotech",
]
FIRST = ["Jane", "Marco", "Aiko", "Priya", "Lars", "Chloe", "Diego", "Nadia", "Tom", "Mei",
         "Omar", "Sofia", "Kenji", "Hannah", "Luis", "Grace"]
LAST = ["Doe", "Rossi", "Tanaka", "Nair", "Berg", "Martin", "Silva", "Haddad", "Reyes", "Lim",
        "Khan", "Moreau", "Sato", "Fischer", "Cruz", "Tan"]

INTENT = {
    "pricing": ("Pricing question", "Could you send over pricing for our team?"),
    "demo": ("Request for a demo", "We would like to book a product demo this week."),
    "support": ("Help with our account", "We are having trouble logging in and need help."),
    "partnership": ("Partnership opportunity", "We would like to discuss a reseller partnership."),
}

VAGUE = [
    "Hi, can someone call me back?",
    "interested in your product",
    "Please send more info.",
    "Hello, is this the right place to ask a question?",
    "need help asap",
    "Can we talk sometime?",
    "Hi there, saw your website.",
    "Following up on my earlier message.",
]
SPAM = [
    ("RANK #1 ON GOOGLE", "Buy our SEO packages now!!! Guaranteed traffic."),
    ("You won a prize", "Click here to claim your free gift card today."),
    ("Cheap followers", "Get 10k followers for $5. Limited offer."),
    ("Urgent invoice", "Your invoice is attached. Open the link to pay immediately."),
    ("Make money fast", "Work from home and earn $500 a day. No experience needed."),
    ("Crypto opportunity", "Double your coins in 24 hours, send to our wallet."),
]


def expected_team(country: str | None, size: int | None) -> str:
    if country in IN_TERRITORY and size is not None:
        return "enterprise" if size >= THRESHOLD else "smb"
    return "review"


def slug(name: str) -> str:
    return name.lower().replace(" ", "")


def person() -> tuple[str, str]:
    first, last = random.choice(FIRST), random.choice(LAST)
    return f"{first} {last}", f"{first}.{last}".lower()


def row(sender, subject, body, company, intent, country, size) -> dict:
    return {
        "from": sender,
        "subject": subject,
        "body": body,
        "expected": {
            "company": company,
            "intent": intent,
            "country": country,
            "team": expected_team(country, size),
        },
    }


def business(intent=None, country=None, size=None, *, with_size=True, free=False,
             hq_note=None) -> dict:
    intent = intent or random.choice(list(INTENT))
    country = country or random.choice(IN_TERRITORY)
    company = random.choice(COMPANIES)
    name, handle = person()
    subject, ask = INTENT[intent]
    verb = "headquartered in" if hq_note else "based in"
    where = f"{verb} {COUNTRY_NAME[country]}"
    parts = [f"Hi, we are {company}, {where}."]
    if hq_note:
        parts.append(f"We also have small satellite offices in {hq_note}.")
    if with_size:
        parts.append(f"We have about {size} employees.")
    parts.append(ask)
    parts.append(f"Regards, {name}")
    domain = random.choice(["gmail.com", "outlook.com"]) if free else f"{slug(company)}.example"
    return row(f"{handle}@{domain}", subject, " ".join(parts), company, intent, country,
               size if with_size else None)


def build() -> list[dict]:
    rows: list[dict] = []
    for _ in range(30):  # clear SMB
        rows.append(business(size=random.choice([5, 12, 25, 40, 80, 150, 200, 320, 450])))
    for _ in range(30):  # clear enterprise
        rows.append(business(size=random.choice([500, 800, 1500, 3000, 8000, 20000])))
    for _ in range(5):  # boundary: 499 vs 500
        country = random.choice(IN_TERRITORY)
        rows.append(business(country=country, size=499))
        rows.append(business(country=country, size=500))
    for _ in range(12):  # free email providers, details in the body
        rows.append(business(size=random.choice([30, 90, 600, 2500]), free=True))
    for _ in range(12):  # missing company size
        rows.append(business(with_size=False))
    for _ in range(10):  # outside every territory
        rows.append(business(country=random.choice(OUT_OF_TERRITORY),
                             size=random.choice([40, 700])))
    for _ in range(8):  # several regions mentioned, HQ decides
        hq = random.choice(IN_TERRITORY)
        other = random.choice([c for c in IN_TERRITORY + OUT_OF_TERRITORY if c != hq])
        rows.append(business(country=hq, size=random.choice([60, 900]),
                             hq_note=COUNTRY_NAME[other]))
    for text in VAGUE:  # vague messages
        _, handle = person()
        rows.append(row(f"{handle}@gmail.com", "hi", text, None, "other", None, None))
    for i in range(12):  # spam
        subject, body = SPAM[i % len(SPAM)]
        rows.append(row(f"promo{i}@bulk-mailer.example", subject, body, None, "spam", None, None))
    rows += random.sample(rows, 6)  # exact duplicates
    random.shuffle(rows)
    return rows


if __name__ == "__main__":
    data = build()
    out = Path(__file__).resolve().parent.parent / "eval" / "dataset.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in data) + "\n")
    print(f"wrote {len(data)} rows to {out}")
