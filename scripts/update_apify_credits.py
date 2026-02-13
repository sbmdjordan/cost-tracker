"""Update Apify subscription with plan credit limit."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))
client = Client(auth=os.getenv("NOTION_TOKEN"))
SUBS_DB_ID = os.getenv("NOTION_SUBSCRIPTIONS_DB_ID")

resp = client.databases.query(
    database_id=SUBS_DB_ID,
    filter={"property": "Name", "title": {"equals": "Apify"}}
)
page_id = resp["results"][0]["id"]

client.pages.update(page_id=page_id, properties={
    "Credits Included": {"number": 29},
    "Monthly Cost USD": {"number": 29},
    "Billing Cycle": {"select": {"name": "Monthly"}},
    "Notes": {"rich_text": [{"text": {"content": "STARTER plan: $29/mo in credits. Overage billed separately."}}]},
})
print("Updated Apify: $29/mo credits included")
