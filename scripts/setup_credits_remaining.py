"""
One-time script:
1. Add "Credits Remaining" number property to Subscriptions DB
2. Set initial values for each service
3. Add callout blocks to subscription pages with manual check instructions & links
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))
client = Client(auth=os.getenv("NOTION_TOKEN"))
SUBS_DB_ID = os.getenv("NOTION_SUBSCRIPTIONS_DB_ID")

# ============================================================
# 1. ADD "Credits Remaining" NUMBER PROPERTY TO DATABASE
# ============================================================
print("=" * 60)
print("ADDING 'Credits Remaining' PROPERTY")
print("=" * 60)

try:
    client.databases.update(
        database_id=SUBS_DB_ID,
        properties={
            "Credits Remaining": {
                "number": {
                    "format": "number"
                }
            }
        }
    )
    print("  Created 'Credits Remaining' number property")
except Exception as e:
    print(f"  Property may already exist or error: {e}")

time.sleep(0.5)

# ============================================================
# 2. SET INITIAL VALUES
# ============================================================
print(f"\n{'=' * 60}")
print("SETTING INITIAL CREDITS REMAINING VALUES")
print("=" * 60)

# Service name -> initial credits remaining
initial_values = {
    "Claude API": 13.86,       # USD remaining from $35.85 total
    "Perplexity": 6.31,        # USD remaining
    "Google Cloud (Oasi)": 216, # GBP remaining from £218 trial
    "Railway": 4.94,           # USD remaining from trial
    # Apify: auto-tracked, don't set manually
    # Google Cloud (sbmdjordan): pay-as-you-go, no credits to track
}

resp = client.databases.query(database_id=SUBS_DB_ID, page_size=100)
for page in resp.get("results", []):
    props = page.get("properties", {})
    title_rt = props.get("Name", {}).get("title", [])
    name = title_rt[0].get("plain_text", "") if title_rt else ""

    if name in initial_values:
        client.pages.update(
            page_id=page["id"],
            properties={
                "Credits Remaining": {"number": initial_values[name]}
            }
        )
        print(f"  {name}: set Credits Remaining = {initial_values[name]}")
        time.sleep(0.35)

# ============================================================
# 3. ADD CALLOUT BLOCKS WITH MANUAL CHECK INSTRUCTIONS
# ============================================================
print(f"\n{'=' * 60}")
print("ADDING CALLOUT BLOCKS TO SUBSCRIPTION PAGES")
print("=" * 60)

# Service name -> callout content (instruction + link)
callout_instructions = {
    "Claude API": {
        "text": "Check remaining credit balance at ",
        "link_text": "Anthropic Console → Billing",
        "link_url": "https://console.anthropic.com/settings/billing",
        "after": ". Update \"Credits Remaining\" on this row.",
        "emoji": "🔗",
    },
    "Perplexity": {
        "text": "Check remaining credit balance at ",
        "link_text": "Perplexity → API Settings",
        "link_url": "https://www.perplexity.ai/settings/api",
        "after": ". Update \"Credits Remaining\" on this row.",
        "emoji": "🔗",
    },
    "Google Cloud (sbmdjordan)": {
        "text": "Log in with sbmdjordan account. Check accruing charges at ",
        "link_text": "Google Cloud → Billing",
        "link_url": "https://console.cloud.google.com/billing",
        "after": ". Update \"Usage GBP\" in Notion.",
        "emoji": "🔗",
    },
    "Google Cloud (Oasi)": {
        "text": "Log in with jjohnson@stayoasi account. Check remaining free credits (£218 trial expires May 7) at ",
        "link_text": "Google Cloud → Billing",
        "link_url": "https://console.cloud.google.com/billing",
        "after": ". Update \"Credits Remaining\" on this row.",
        "emoji": "🔗",
    },
    "Railway": {
        "text": "Check trial credits remaining at ",
        "link_text": "Railway → Account Usage",
        "link_url": "https://railway.com/account/usage",
        "after": ". Free trial: 28 days or $4.94. Update \"Credits Remaining\" on this row.",
        "emoji": "🔗",
    },
}

resp = client.databases.query(database_id=SUBS_DB_ID, page_size=100)
for page in resp.get("results", []):
    props = page.get("properties", {})
    title_rt = props.get("Name", {}).get("title", [])
    name = title_rt[0].get("plain_text", "") if title_rt else ""

    if name in callout_instructions:
        info = callout_instructions[name]

        # Check if page already has a callout (avoid duplicates)
        children = client.blocks.children.list(block_id=page["id"])
        has_callout = any(
            b.get("type") == "callout" for b in children.get("results", [])
        )
        if has_callout:
            print(f"  {name}: callout already exists, skipping")
            continue

        # Build rich text with link
        rich_text = [
            {"type": "text", "text": {"content": info["text"]}},
            {
                "type": "text",
                "text": {
                    "content": info["link_text"],
                    "link": {"url": info["link_url"]}
                },
                "annotations": {"bold": True}
            },
            {"type": "text", "text": {"content": info["after"]}},
        ]

        client.blocks.children.append(
            block_id=page["id"],
            children=[{
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": rich_text,
                    "icon": {"emoji": info["emoji"]},
                    "color": "blue_background",
                }
            }]
        )
        print(f"  {name}: added callout with link to {info['link_url']}")
        time.sleep(0.35)

print(f"\n{'=' * 60}")
print("DONE")
print("=" * 60)
