"""Quick check of Apify billing details."""
import os, requests
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env"))

token = os.getenv("APIFY_TOKEN")

# Monthly usage
r = requests.get(f"https://api.apify.com/v2/users/me/usage/monthly?token={token}")
data = r.json()["data"]
total = data.get("totalUsageUsd", 0)
print(f"Total usage USD (current billing month): ${total:.4f}")

# Account info
r2 = requests.get(f"https://api.apify.com/v2/users/me?token={token}")
user = r2.json()["data"]
plan = user.get("plan", {})
cycle = user.get("usageCycle", {})
print(f"Plan: {plan.get('id', '?')}")
print(f"Monthly credits: ${plan.get('monthlyUsageCreditsUsd', 0)}")
print(f"Billing cycle start: {cycle.get('startAt', '?')}")
print(f"Billing cycle end: {cycle.get('endAt', '?')}")

# Check if there's a previous month we might be missing
print(f"\nDaily breakdown this cycle:")
daily = data.get("dailyServiceUsages", [])
if daily:
    for day in daily[:5]:
        print(f"  {day.get('date', '?')}: ${day.get('totalUsd', 0):.4f}")
    print(f"  ... ({len(daily)} total days)")
