"""
One-time script:
1. Rename "Content Monitoring" -> "Healthy Living Competitor Content Tracking" in Notion
2. Add manual usage entries for Claude API ($21.99) and Perplexity ($8.40)
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from notion_client import Client
from datetime import date

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))
client = Client(auth=os.getenv("NOTION_TOKEN"))
SUBS_DB_ID = os.getenv("NOTION_SUBSCRIPTIONS_DB_ID")
USAGE_DB_ID = os.getenv("NOTION_USAGE_LOG_DB_ID")

OLD_NAME = "Content Monitoring"
NEW_NAME = "Healthy Living Competitor Content Tracking"

# ============================================================
# 1. RENAME PROJECT IN SUBSCRIPTIONS
# ============================================================
print("=" * 60)
print("RENAMING PROJECT IN SUBSCRIPTIONS")
print("=" * 60)

resp = client.databases.query(database_id=SUBS_DB_ID, page_size=100)
for page in resp.get("results", []):
    props = page.get("properties", {})
    projects = [p.get("name", "") for p in props.get("Project", {}).get("multi_select", [])]
    name = props.get("Name", {}).get("title", [{}])[0].get("plain_text", "") if props.get("Name", {}).get("title") else ""

    if OLD_NAME in projects:
        new_projects = [{"name": NEW_NAME if p == OLD_NAME else p} for p in projects]
        client.pages.update(
            page_id=page["id"],
            properties={"Project": {"multi_select": new_projects}}
        )
        print(f"  Updated sub '{name}': {projects} -> {[p['name'] for p in new_projects]}")
        time.sleep(0.35)

# ============================================================
# 2. RENAME PROJECT IN USAGE LOG
# ============================================================
print(f"\n{'=' * 60}")
print("RENAMING PROJECT IN USAGE LOG")
print("=" * 60)

resp = client.databases.query(database_id=USAGE_DB_ID, page_size=100)
for page in resp.get("results", []):
    props = page.get("properties", {})
    projects = [p.get("name", "") for p in props.get("Project", {}).get("multi_select", [])]
    title_rt = props.get("Entry", {}).get("title", [])
    title = title_rt[0].get("plain_text", "") if title_rt else ""

    if OLD_NAME in projects or OLD_NAME in title:
        updates = {}
        if OLD_NAME in projects:
            new_projects = [{"name": NEW_NAME if p == OLD_NAME else p} for p in projects]
            updates["Project"] = {"multi_select": new_projects}

        if OLD_NAME in title:
            new_title = title.replace(OLD_NAME, NEW_NAME)
            updates["Entry"] = {"title": [{"text": {"content": new_title}}]}

        client.pages.update(page_id=page["id"], properties=updates)
        print(f"  Updated usage '{title}' -> project renamed")
        time.sleep(0.35)

# ============================================================
# 3. ADD MANUAL USAGE ENTRIES
# ============================================================
print(f"\n{'=' * 60}")
print("ADDING MANUAL USAGE ENTRIES")
print("=" * 60)

today = date.today().isoformat()

# USD to GBP conversion
import requests
try:
    r = requests.get("https://api.frankfurter.app/latest", params={"from": "USD", "to": "GBP"}, timeout=10)
    rate = r.json().get("rates", {}).get("GBP", 0.80)
except Exception:
    rate = 0.80
print(f"  Exchange rate: $1 = £{rate:.4f}")

manual_entries = [
    {
        "name": "Claude API",
        "cost_usd": 21.99,
        "project": "General",
        "category": "Work",
        "unit": "USD",
        "notes": "Total API credits used. Manual entry from Anthropic console.",
    },
    {
        "name": "Perplexity",
        "cost_usd": 8.40,
        "project": "General",
        "category": "Work",
        "unit": "USD",
        "notes": "Total API credits used. Manual entry from Perplexity settings.",
    },
]

for entry in manual_entries:
    entry_title = f"{entry['name']} - {entry['project']} - {today}"

    # Check if already exists
    check = client.databases.query(
        database_id=USAGE_DB_ID,
        filter={"property": "Entry", "title": {"equals": entry_title}}
    )
    if check.get("results"):
        print(f"  Already exists: '{entry_title}' — skipping")
        continue

    cost_gbp = round(entry["cost_usd"] * rate, 2)
    props = {
        "Entry": {"title": [{"text": {"content": entry_title}}]},
        "Date": {"date": {"start": today}},
        "Service": {"select": {"name": entry["name"]}},
        "Project": {"multi_select": [{"name": entry["project"]}]},
        "Category": {"select": {"name": entry["category"]}},
        "Usage Amount": {"number": entry["cost_usd"]},
        "Unit": {"select": {"name": entry["unit"]}},
        "Cost USD": {"number": entry["cost_usd"]},
        "Cost GBP": {"number": cost_gbp},
        "Source": {"select": {"name": "Manual"}},
        "Notes": {"rich_text": [{"text": {"content": entry["notes"]}}]},
    }
    client.pages.create(parent={"database_id": USAGE_DB_ID}, properties=props)
    print(f"  Created: '{entry_title}' — ${entry['cost_usd']:.2f} / £{cost_gbp:.2f}")
    time.sleep(0.35)

print(f"\n{'=' * 60}")
print("DONE")
print("=" * 60)
