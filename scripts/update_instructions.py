"""Update the Manual Checks section on the Cost Tracker page with check frequencies."""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))
client = Client(auth=os.getenv("NOTION_TOKEN"))

PAGE_ID = "30658d69708880a792ead49c438542d7"

# Delete existing Manual Checks section (divider, heading, intro, callouts)
print("Removing old Manual Checks section...")
children = client.blocks.children.list(block_id=PAGE_ID)
found_divider = False
for block in children.get("results", []):
    btype = block.get("type", "")

    # Once we hit the divider before Manual Checks, delete everything after
    if btype == "divider":
        found_divider = True
        client.blocks.delete(block_id=block["id"])
        print(f"  Deleted: divider")
        continue

    if found_divider:
        client.blocks.delete(block_id=block["id"])
        rt = block.get(btype, {}).get("rich_text", [])
        text = "".join(t.get("plain_text", "") for t in rt)[:40]
        print(f"  Deleted: [{btype}] {text}")

# Rebuild with frequencies
print("\nAdding updated Manual Checks section...")

blocks = [
    {"object": "block", "type": "divider", "divider": {}},
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Manual Checks"}}],
            "color": "default",
        },
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": {"content": "These services can\u2019t be auto-tracked. Check your balances at the frequency below and update the "}, "annotations": {"color": "gray"}},
                {"type": "text", "text": {"content": "Subscriptions & Services"}, "annotations": {"bold": True, "color": "gray"}},
                {"type": "text", "text": {"content": " database above."}, "annotations": {"color": "gray"}},
            ]
        },
    },
    # --- Claude API ---
    {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [
                {"type": "text", "text": {"content": "Claude API"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": "  \u2014  "}},
                {"type": "text", "text": {"content": "Check weekly"}, "annotations": {"bold": True, "italic": True, "color": "orange"}},
                {"type": "text", "text": {"content": "\n1. Go to "}},
                {"type": "text", "text": {"content": "Anthropic Console \u2192 Billing", "link": {"url": "https://console.anthropic.com/settings/billing"}}, "annotations": {"bold": True, "color": "blue"}},
                {"type": "text", "text": {"content": "\n2. Note your remaining credit balance\n3. Open the "}},
                {"type": "text", "text": {"content": "Claude API"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " row in Subscriptions & Services\n4. Update "}},
                {"type": "text", "text": {"content": "Credits Remaining"}, "annotations": {"bold": True, "code": True}},
                {"type": "text", "text": {"content": " with the balance you see"}},
            ],
            "icon": {"emoji": "\U0001f916"},
            "color": "purple_background",
        },
    },
    # --- Perplexity ---
    {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [
                {"type": "text", "text": {"content": "Perplexity"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": "  \u2014  "}},
                {"type": "text", "text": {"content": "Check weekly"}, "annotations": {"bold": True, "italic": True, "color": "orange"}},
                {"type": "text", "text": {"content": "\n1. Go to "}},
                {"type": "text", "text": {"content": "Perplexity \u2192 API Settings", "link": {"url": "https://www.perplexity.ai/settings/api"}}, "annotations": {"bold": True, "color": "blue"}},
                {"type": "text", "text": {"content": "\n2. Note your remaining credit balance\n3. Open the "}},
                {"type": "text", "text": {"content": "Perplexity"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " row in Subscriptions & Services\n4. Update "}},
                {"type": "text", "text": {"content": "Credits Remaining"}, "annotations": {"bold": True, "code": True}},
                {"type": "text", "text": {"content": " with the balance you see"}},
            ],
            "icon": {"emoji": "\U0001f50d"},
            "color": "blue_background",
        },
    },
    # --- Google Cloud (sbmdjordan) ---
    {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [
                {"type": "text", "text": {"content": "Google Cloud (sbmdjordan)"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": "  \u2014  "}},
                {"type": "text", "text": {"content": "Check monthly"}, "annotations": {"bold": True, "italic": True, "color": "green"}},
                {"type": "text", "text": {"content": "\n1. Go to "}},
                {"type": "text", "text": {"content": "Google Cloud \u2192 Billing", "link": {"url": "https://console.cloud.google.com/billing"}}, "annotations": {"bold": True, "color": "blue"}},
                {"type": "text", "text": {"content": " (log in with "}},
                {"type": "text", "text": {"content": "sbmdjordan"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " account)\n2. Note the accruing charges for the current month\n3. Open the "}},
                {"type": "text", "text": {"content": "Google Cloud (sbmdjordan)"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " row in Subscriptions & Services\n4. Update "}},
                {"type": "text", "text": {"content": "Usage GBP"}, "annotations": {"bold": True, "code": True}},
                {"type": "text", "text": {"content": " with the amount shown"}},
            ],
            "icon": {"emoji": "\u2601\ufe0f"},
            "color": "yellow_background",
        },
    },
    # --- Google Cloud (Oasi) ---
    {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [
                {"type": "text", "text": {"content": "Google Cloud (Oasi)"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": "  \u2014  "}},
                {"type": "text", "text": {"content": "Check monthly"}, "annotations": {"bold": True, "italic": True, "color": "green"}},
                {"type": "text", "text": {"content": "\n1. Go to "}},
                {"type": "text", "text": {"content": "Google Cloud \u2192 Billing", "link": {"url": "https://console.cloud.google.com/billing"}}, "annotations": {"bold": True, "color": "blue"}},
                {"type": "text", "text": {"content": " (log in with "}},
                {"type": "text", "text": {"content": "jjohnson@stayoasi"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " account)\n2. Note remaining free trial credits (\u00a3218 trial, expires May 7 2026)\n3. Open the "}},
                {"type": "text", "text": {"content": "Google Cloud (Oasi)"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " row in Subscriptions & Services\n4. Update "}},
                {"type": "text", "text": {"content": "Credits Remaining"}, "annotations": {"bold": True, "code": True}},
                {"type": "text", "text": {"content": " with the balance you see"}},
            ],
            "icon": {"emoji": "\u2601\ufe0f"},
            "color": "yellow_background",
        },
    },
    # --- Railway ---
    {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [
                {"type": "text", "text": {"content": "Railway"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": "  \u2014  "}},
                {"type": "text", "text": {"content": "Check weekly"}, "annotations": {"bold": True, "italic": True, "color": "orange"}},
                {"type": "text", "text": {"content": " (small trial balance)"}},
                {"type": "text", "text": {"content": "\n1. Go to "}},
                {"type": "text", "text": {"content": "Railway \u2192 Account Usage", "link": {"url": "https://railway.com/account/usage"}}, "annotations": {"bold": True, "color": "blue"}},
                {"type": "text", "text": {"content": "\n2. Note your remaining trial balance (started at $4.94)\n3. Open the "}},
                {"type": "text", "text": {"content": "Railway"}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": " row in Subscriptions & Services\n4. Update "}},
                {"type": "text", "text": {"content": "Credits Remaining"}, "annotations": {"bold": True, "code": True}},
                {"type": "text", "text": {"content": " with the balance you see"}},
            ],
            "icon": {"emoji": "\U0001f682"},
            "color": "green_background",
        },
    },
]

result = client.blocks.children.append(block_id=PAGE_ID, children=blocks)
print(f"Added {len(blocks)} blocks with check frequencies")
print("Done!")
