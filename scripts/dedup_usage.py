"""Remove duplicate usage log entries, keeping only the most recently updated."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))
client = Client(auth=os.getenv("NOTION_TOKEN"))
USAGE_DB_ID = os.getenv("NOTION_USAGE_LOG_DB_ID")

# Get ALL entries
resp = client.databases.query(database_id=USAGE_DB_ID, page_size=100)
pages = resp.get("results", [])

print(f"Found {len(pages)} total entries in Usage Log\n")

# Group by title
by_title = {}
for page in pages:
    title_rt = page.get("properties", {}).get("Entry", {}).get("title", [])
    title = title_rt[0].get("plain_text", "") if title_rt else ""
    last_edited = page.get("last_edited_time", "")

    if title not in by_title:
        by_title[title] = []
    by_title[title].append({
        "id": page["id"],
        "title": title,
        "last_edited": last_edited,
    })

# Find duplicates and archive all but the newest
archived_count = 0
for title, entries in by_title.items():
    if len(entries) > 1:
        # Sort by last_edited descending — keep the newest
        entries.sort(key=lambda e: e["last_edited"], reverse=True)
        print(f"'{title}' — {len(entries)} copies, keeping newest ({entries[0]['last_edited']})")
        for entry in entries[1:]:
            client.pages.update(page_id=entry["id"], archived=True)
            print(f"  Archived: {entry['id']} (edited {entry['last_edited']})")
            archived_count += 1
            time.sleep(0.35)
    elif len(entries) == 1:
        print(f"'{title}' — OK (1 copy)")

print(f"\nArchived {archived_count} duplicates.")
