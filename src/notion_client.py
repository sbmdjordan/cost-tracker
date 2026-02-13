"""
Notion API client for cost tracking databases.
Manages Subscriptions & Services and Usage Log databases.
"""

from notion_client import Client
from notion_client.errors import APIResponseError
from typing import Optional
import logging

from .utils.rate_limiter import notion_rate_limited_call
from .models import SubscriptionEntry, UsageLogEntry


class NotionClient:
    """Client for interacting with Notion cost tracking databases."""

    def __init__(
        self,
        token: str,
        subscriptions_db_id: str,
        usage_log_db_id: str,
        default_icon: str = "\U0001f4b0",
    ):
        self.subscriptions_db_id = subscriptions_db_id
        self.usage_log_db_id = usage_log_db_id
        self.default_icon = default_icon
        self.logger = logging.getLogger(__name__)

        self.client = Client(auth=token)
        self.logger.info("Notion client initialized")

    def _rate_limited_create(self, **kwargs) -> dict:
        """Create page with rate limiting."""
        def create_page():
            return self.client.pages.create(**kwargs)
        return notion_rate_limited_call(create_page)

    def _rate_limited_update(self, page_id: str, **kwargs) -> dict:
        """Update page with rate limiting."""
        def update_page():
            return self.client.pages.update(page_id=page_id, **kwargs)
        return notion_rate_limited_call(update_page)

    # --- Subscriptions Database Methods ---

    def find_subscription_by_name(self, name: str) -> Optional[dict]:
        """Query Subscriptions DB for a row by Name (title)."""
        try:
            response = self.client.databases.query(
                database_id=self.subscriptions_db_id,
                filter={
                    "property": "Name",
                    "title": {"equals": name}
                }
            )
            results = response.get("results", [])
            return results[0] if results else None
        except Exception as e:
            self.logger.warning(f"Error finding subscription '{name}': {e}")
            return None

    def create_subscription(self, sub: SubscriptionEntry) -> Optional[dict]:
        """Create a new subscription entry. Skip if name already exists."""
        existing = self.find_subscription_by_name(sub.name)
        if existing:
            self.logger.info(f"Subscription '{sub.name}' already exists, skipping")
            return None

        try:
            response = self._rate_limited_create(
                parent={"database_id": self.subscriptions_db_id},
                icon={"emoji": self.default_icon},
                properties=sub.to_notion_properties()
            )
            self.logger.info(f"Created subscription: {sub.name}")
            return response
        except APIResponseError as e:
            self.logger.error(f"Notion API error creating '{sub.name}': {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating subscription '{sub.name}': {e}")
            return None

    def update_subscription_usage(
        self,
        page_id: str,
        usage_usd: float,
        usage_gbp: float = 0.0,
        credits_remaining: float = None,
    ) -> Optional[dict]:
        """Update Usage USD, Usage GBP, and optionally Credits Remaining on a subscription row."""
        try:
            properties = {
                "Usage USD": {"number": round(usage_usd, 4)},
                "Usage GBP": {"number": round(usage_gbp, 4)},
            }
            if credits_remaining is not None:
                properties["Credits Remaining"] = {"number": round(credits_remaining, 4)}
            response = self._rate_limited_update(page_id, properties=properties)
            self.logger.info(f"Updated subscription usage: ${usage_usd:.2f} / \u00a3{usage_gbp:.2f}")
            return response
        except Exception as e:
            self.logger.error(f"Error updating subscription usage: {e}")
            return None

    # --- Usage Log Database Methods ---

    def find_usage_entry_by_title(self, entry_title: str) -> Optional[dict]:
        """Check if a usage log entry already exists by its full title."""
        try:
            response = self.client.databases.query(
                database_id=self.usage_log_db_id,
                filter={
                    "property": "Entry",
                    "title": {"equals": entry_title}
                }
            )
            results = response.get("results", [])
            return results[0] if results else None
        except Exception as e:
            self.logger.warning(f"Error finding usage entry '{entry_title}': {e}")
            return None

    def create_usage_entry(self, entry: UsageLogEntry) -> Optional[dict]:
        """Create a usage log entry. If exists for same date/service/project, update it."""
        existing = self.find_usage_entry_by_title(entry.entry_title)

        try:
            if existing:
                self.logger.info(f"Updating existing entry: {entry.entry_title}")
                return self._rate_limited_update(
                    existing["id"],
                    properties=entry.to_notion_properties()
                )

            response = self._rate_limited_create(
                parent={"database_id": self.usage_log_db_id},
                icon={"emoji": self.default_icon},
                properties=entry.to_notion_properties()
            )
            self.logger.info(f"Created usage entry: {entry.entry_title}")
            return response
        except APIResponseError as e:
            self.logger.error(f"Notion API error for '{entry.entry_title}': {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating usage entry '{entry.entry_title}': {e}")
            return None

    # --- Read Methods (for dashboard generation) ---

    def get_all_subscriptions(self) -> list:
        """Query all subscriptions. Returns list of dicts with parsed properties."""
        try:
            results = []
            response = self.client.databases.query(
                database_id=self.subscriptions_db_id,
                page_size=100,
            )
            for page in response.get("results", []):
                props = page.get("properties", {})
                results.append(self._parse_subscription(props))
            self.logger.info(f"Loaded {len(results)} subscriptions")
            return results
        except Exception as e:
            self.logger.error(f"Error loading subscriptions: {e}")
            return []

    def _parse_subscription(self, props: dict) -> dict:
        """Parse a Notion subscription page's properties into a plain dict."""
        title_rt = props.get("Name", {}).get("title", [])
        name = title_rt[0].get("plain_text", "") if title_rt else ""

        notes_rt = props.get("Notes", {}).get("rich_text", [])
        notes = notes_rt[0].get("plain_text", "") if notes_rt else ""

        project_ms = props.get("Project", {}).get("multi_select", [])
        projects = [p.get("name", "") for p in project_ms]

        return {
            "name": name,
            "service_type": props.get("Service Type", {}).get("select", {}).get("name", ""),
            "projects": projects,
            "category": props.get("Category", {}).get("select", {}).get("name", ""),
            "billed_currency": props.get("Billed Currency", {}).get("select", {}).get("name", "USD"),
            "monthly_cost_usd": props.get("Monthly Cost USD", {}).get("number") or 0,
            "monthly_cost_gbp": props.get("Monthly Cost GBP", {}).get("number") or 0,
            "billing_cycle": props.get("Billing Cycle", {}).get("select", {}).get("name", ""),
            "next_renewal": props.get("Next Renewal", {}).get("date", {}).get("start") if props.get("Next Renewal", {}).get("date") else None,
            "status": props.get("Status", {}).get("select", {}).get("name", ""),
            "credits_included": props.get("Credits Included", {}).get("number") or 0,
            "credits_remaining": props.get("Credits Remaining", {}).get("number") or 0,
            "usage_usd": props.get("Usage USD", {}).get("number") or 0,
            "usage_gbp": props.get("Usage GBP", {}).get("number") or 0,
            "auto_tracked": props.get("Auto Tracked", {}).get("checkbox", False),
            "notes": notes,
        }

    def get_current_month_usage(self) -> list:
        """Query usage log entries for the current month."""
        from datetime import date
        month_start = date.today().replace(day=1).isoformat()

        try:
            results = []
            response = self.client.databases.query(
                database_id=self.usage_log_db_id,
                filter={
                    "property": "Date",
                    "date": {"on_or_after": month_start}
                },
                sorts=[{"property": "Date", "direction": "descending"}],
                page_size=100,
            )
            for page in response.get("results", []):
                props = page.get("properties", {})
                results.append(self._parse_usage_entry(props))
            self.logger.info(f"Loaded {len(results)} usage entries this month")
            return results
        except Exception as e:
            self.logger.error(f"Error loading usage entries: {e}")
            return []

    def _parse_usage_entry(self, props: dict) -> dict:
        """Parse a Notion usage log page's properties into a plain dict."""
        title_rt = props.get("Entry", {}).get("title", [])
        entry = title_rt[0].get("plain_text", "") if title_rt else ""

        notes_rt = props.get("Notes", {}).get("rich_text", [])
        notes = notes_rt[0].get("plain_text", "") if notes_rt else ""

        project_ms = props.get("Project", {}).get("multi_select", [])
        projects = [p.get("name", "") for p in project_ms]

        return {
            "entry": entry,
            "date": props.get("Date", {}).get("date", {}).get("start") if props.get("Date", {}).get("date") else None,
            "service": props.get("Service", {}).get("select", {}).get("name", ""),
            "projects": projects,
            "category": props.get("Category", {}).get("select", {}).get("name", ""),
            "usage_amount": props.get("Usage Amount", {}).get("number") or 0,
            "unit": props.get("Unit", {}).get("select", {}).get("name", ""),
            "cost_usd": props.get("Cost USD", {}).get("number") or 0,
            "cost_gbp": props.get("Cost GBP", {}).get("number") or 0,
            "source": props.get("Source", {}).get("select", {}).get("name", ""),
            "notes": notes,
        }

    # --- Connection Test ---

    def test_connection(self) -> bool:
        """Test connections to both databases."""
        try:
            sub_db = self.client.databases.retrieve(
                database_id=self.subscriptions_db_id
            )
            usage_db = self.client.databases.retrieve(
                database_id=self.usage_log_db_id
            )
            if sub_db and usage_db:
                sub_title = sub_db.get("title", [{}])[0].get("plain_text", "?")
                usage_title = usage_db.get("title", [{}])[0].get("plain_text", "?")
                self.logger.info(f"Connected: '{sub_title}' + '{usage_title}'")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
