"""
Cleanup stale entries and update real costs.
- Remove ClickUp (not Jordan's)
- Update ChatGPT GBP to £20
- Update Apify GBP to £25.49
- Google Cloud (sbmdjordan): note charges accruing but not yet billed
- Archive stale Gemini API entries
- Delete orphaned usage log entries with old title format
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))
client = Client(auth=os.getenv("NOTION_TOKEN"))
SUBS_DB_ID = os.getenv("NOTION_SUBSCRIPTIONS_DB_ID")
USAGE_DB_ID = os.getenv("NOTION_USAGE_LOG_DB_ID")


def find_sub(name):
    resp = client.databases.query(
        database_id=SUBS_DB_ID,
        filter={"property": "Name", "title": {"equals": name}}
    )
    results = resp.get("results", [])
    return results[0]["id"] if results else None


def update_sub(name, properties):
    page_id = find_sub(name)
    if not page_id:
        print(f"  NOT FOUND: {name}")
        return
    client.pages.update(page_id=page_id, properties=properties)
    print(f"  Updated: {name}")
    time.sleep(0.35)


def archive_sub(name):
    page_id = find_sub(name)
    if not page_id:
        print(f"  NOT FOUND: {name}")
        return
    client.pages.update(page_id=page_id, archived=True)
    print(f"  Archived: {name}")
    time.sleep(0.35)


# === SUBSCRIPTIONS DATABASE ===
print("=" * 50)
print("SUBSCRIPTIONS & SERVICES DATABASE")
print("=" * 50)

# 1. ChatGPT — £20 GBP bank charge
print("\n1. ChatGPT / OpenAI — setting £20 GBP")
update_sub("ChatGPT / OpenAI", {
    "Monthly Cost GBP": {"number": 20.0},
})

# 2. Apify — £25.49 bank charge (for $34.80 total incl overage)
print("\n2. Apify — setting £25.49 GBP (actual bank charge)")
update_sub("Apify", {
    "Monthly Cost GBP": {"number": 25.49},
})

# 3. Google Cloud (sbmdjordan) — charges accruing, not yet billed
print("\n3. Google Cloud (sbmdjordan) — updating notes")
update_sub("Google Cloud (sbmdjordan)", {
    "Monthly Cost GBP": {"number": 0},  # Not yet billed
    "Notes": {"rich_text": [{"text": {"content": "Includes Gemini API. Free credits exhausted. £4.33 accruing (not yet billed). Will use for Elite Eats."}}]},
})

# 4. Remove ClickUp — not Jordan's
print("\n4. ClickUp — archiving (not yours)")
archive_sub("ClickUp")

# 5. Archive stale Gemini API entries (billing through Google Cloud)
print("\n5. Archiving stale Gemini API entries...")
archive_sub("Gemini API (Oasi)")
archive_sub("Gemini API (sbmdjordan)")

# === USAGE LOG DATABASE ===
print("\n" + "=" * 50)
print("USAGE LOG DATABASE — cleaning orphaned entries")
print("=" * 50)

# Find entries with old title format "Apify - YYYY-MM-DD" (no project name)
resp = client.databases.query(
    database_id=USAGE_DB_ID,
    filter={
        "property": "Entry",
        "title": {"contains": "Apify - 2026"}
    }
)

orphaned = []
for page in resp.get("results", []):
    title_rt = page.get("properties", {}).get("Entry", {}).get("title", [])
    title = title_rt[0].get("plain_text", "") if title_rt else ""
    # Old format: "Apify - 2026-02-13" (no project)
    # New format: "Apify - Content Monitoring - 2026-02-13" (has project)
    parts = title.split(" - ")
    if len(parts) == 2 and parts[0] == "Apify":
        orphaned.append((page["id"], title))

if orphaned:
    for page_id, title in orphaned:
        client.pages.update(page_id=page_id, archived=True)
        print(f"  Archived orphan: '{title}'")
        time.sleep(0.35)
else:
    print("  No orphaned usage entries found.")

# Also check for any "General" project entries from first run
resp2 = client.databases.query(
    database_id=USAGE_DB_ID,
    filter={
        "property": "Entry",
        "title": {"contains": "Apify - General"}
    }
)
for page in resp2.get("results", []):
    title_rt = page.get("properties", {}).get("Entry", {}).get("title", [])
    title = title_rt[0].get("plain_text", "") if title_rt else ""
    client.pages.update(page_id=page["id"], archived=True)
    print(f"  Archived stale: '{title}'")
    time.sleep(0.35)

print("\n=== Cleanup complete ===")
