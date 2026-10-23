"""List HubSpot owners and print the line to paste into .env.

    docker compose exec api python scripts/list_owners.py

Uses HUBSPOT_TOKEN (needs the crm.objects.owners.read scope).
"""

import sys

import httpx

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.hubspot_token:
        sys.exit("HUBSPOT_TOKEN is empty; set it in .env and restart the api container.")

    resp = httpx.get(
        "https://api.hubapi.com/crm/v3/owners",
        headers={"Authorization": f"Bearer {settings.hubspot_token}"},
        timeout=15,
    )
    if resp.status_code != 200:
        sys.exit(f"HubSpot {resp.status_code}: {resp.text[:300]}")

    owners = resp.json().get("results", [])
    if not owners:
        sys.exit("No owners returned.")

    print("HubSpot owners:")
    for o in owners:
        name = f"{o.get('firstName', '')} {o.get('lastName', '')}".strip()
        print(f"  {o['id']}  {name}  <{o.get('email', '')}>")

    print("\nPut this in .env, then restart the api and worker containers:\n")
    print(f"HUBSPOT_DEFAULT_OWNER_ID={owners[0]['id']}")


if __name__ == "__main__":
    main()
