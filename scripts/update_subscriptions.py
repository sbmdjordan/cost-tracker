"""
One-time script to update all Notion subscription entries with real data.
Run from project root: python scripts/update_subscriptions.py
"""

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from notion_client import Client

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))

client = Client(auth=os.getenv("NOTION_TOKEN"))
SUBS_DB_ID = os.getenv("NOTION_SUBSCRIPTIONS_DB_ID")


def find_sub(name):
    """Find a subscription by name."""
    resp = client.databases.query(
        database_id=SUBS_DB_ID,
        filter={"property": "Name", "title": {"equals": name}}
    )
    results = resp.get("results", [])
    return results[0]["id"] if results else None


def update_sub(name, properties):
    """Update a subscription's properties."""
    page_id = find_sub(name)
    if not page_id:
        print(f"  NOT FOUND: {name}")
        return
    client.pages.update(page_id=page_id, properties=properties)
    print(f"  Updated: {name}")
    time.sleep(0.35)


def archive_sub(name):
    """Archive (soft-delete) a subscription."""
    page_id = find_sub(name)
    if not page_id:
        print(f"  NOT FOUND for archive: {name}")
        return
    client.pages.update(page_id=page_id, archived=True)
    print(f"  Archived: {name}")
    time.sleep(0.35)


print("=== Updating subscriptions with real data ===\n")

# 1. Claude Code — $109.51/mo, £80.62/mo, renews Mar 5
print("1. Claude Code")
update_sub("Claude Code", {
    "Monthly Cost USD": {"number": 109.51},
    "Monthly Cost GBP": {"number": 80.62},
    "Next Renewal": {"date": {"start": "2026-03-05"}},
    "Notes": {"rich_text": [{"text": {"content": "Claude Max plan"}}]},
})

# 2. ChatGPT / OpenAI — $27.15/mo, renews Mar 6
print("2. ChatGPT / OpenAI")
update_sub("ChatGPT / OpenAI", {
    "Monthly Cost USD": {"number": 27.15},
    "Next Renewal": {"date": {"start": "2026-03-06"}},
})

# 3. Claude API — $21.99 credits purchased, $13.86 remaining
print("3. Claude API")
update_sub("Claude API", {
    "Credits Included": {"number": 21.99},
    "Credits Used": {"number": 8.13},  # 21.99 - 13.86
    "Usage USD": {"number": 8.13},
    "Notes": {"rich_text": [{"text": {"content": "$13.86 remaining as of Feb 13, 2026"}}]},
})

# 4. Perplexity — $8.40 credits purchased, $6.31 remaining
print("4. Perplexity")
update_sub("Perplexity", {
    "Credits Included": {"number": 8.40},
    "Credits Used": {"number": 2.09},  # 8.40 - 6.31
    "Usage USD": {"number": 2.09},
    "Notes": {"rich_text": [{"text": {"content": "$6.31 remaining as of Feb 13, 2026"}}]},
})

# 5. Google Cloud (sbmdjordan) — £218 free credits EXHAUSTED, now £4.33 in charges
print("5. Google Cloud (sbmdjordan)")
update_sub("Google Cloud (sbmdjordan)", {
    "Credits Included": {"number": 218},
    "Credits Used": {"number": 218},
    "Usage GBP": {"number": 4.33},
    "Billing Cycle": {"select": {"name": "Pay-as-you-go"}},
    "Notes": {"rich_text": [{"text": {"content": "Free credits exhausted. Incurring charges as of Feb 12, 2026"}}]},
})

# 6. Google Cloud (Oasi) — £218 free credits, £2 used, expires May 7, 2026
# Gemini API usage is billed through this (same £2)
print("6. Google Cloud (Oasi)")
update_sub("Google Cloud (Oasi)", {
    "Credits Included": {"number": 218},
    "Credits Used": {"number": 2},
    "Usage GBP": {"number": 0},  # covered by free credits
    "Next Renewal": {"date": {"start": "2026-05-07"}},
    "Notes": {"rich_text": [{"text": {"content": "Free trial credits, expires May 7, 2026. Includes Gemini API usage."}}]},
})

# 7. Gemini API (Oasi) — billing goes through Google Cloud, mark as note-only
print("7. Gemini API (Oasi) — merging into Google Cloud (Oasi)")
update_sub("Gemini API (Oasi)", {
    "Status": {"select": {"name": "Cancelled"}},
    "Notes": {"rich_text": [{"text": {"content": "Billed through Google Cloud (Oasi). See that entry for credits/usage."}}]},
})

# 8. Gemini API (sbmdjordan) — 0 usage, billing goes through Google Cloud
print("8. Gemini API (sbmdjordan) — merging into Google Cloud (sbmdjordan)")
update_sub("Gemini API (sbmdjordan)", {
    "Status": {"select": {"name": "Cancelled"}},
    "Notes": {"rich_text": [{"text": {"content": "Billed through Google Cloud (sbmdjordan). See that entry for credits/usage."}}]},
})

# 9. Archive the old generic entries that were replaced by account-specific ones
print("\n9. Archiving old generic entries...")
archive_sub("Gemini API")
archive_sub("Google Cloud")

# 10. Apify — update with current month from spreadsheet ($34.80)
# Our auto-tracker shows $29.00 for current runs. Spreadsheet may include previous billing period.
print("\n10. Apify — keeping auto-tracked value ($29.00)")
print("    Spreadsheet shows $34.80 — checking if this includes previous month...")

print("\n=== Done ===")
