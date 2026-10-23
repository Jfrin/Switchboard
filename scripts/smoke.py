"""Post a sample lead and print the result. Runs inside the api container.

    python scripts/smoke.py          # post a sample lead, wait, print the outcome
    python scripts/smoke.py --list   # list recent leads
"""

import json
import sys
import time

import httpx

API = "http://localhost:8000"
SAMPLE = {
    "from": "jane.doe@acme.com",
    "subject": "Pricing for 200 seats",
    "body": "Hi, we are a logistics company in Singapore looking for pricing on 200 seats.",
}


def main() -> None:
    if "--list" in sys.argv:
        print(json.dumps(httpx.get(f"{API}/leads").json(), indent=2))
        return

    print("health:", httpx.get(f"{API}/health").json())
    res = httpx.post(f"{API}/leads", json=SAMPLE)
    res.raise_for_status()
    lead_id = res.json()["id"]
    print("lead id:", lead_id)

    lead = {}
    for _ in range(40):  # Gemini calls are spaced out by GEMINI_RPM, so allow ~80s
        lead = httpx.get(f"{API}/leads/{lead_id}").json()
        if lead["status"] not in ("queued", "processing"):
            break
        time.sleep(2)
    print(json.dumps(lead, indent=2))


if __name__ == "__main__":
    main()
