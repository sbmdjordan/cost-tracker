"""
Data models for cost tracking.
Plain Python classes (no pydantic).
"""

from datetime import date
from typing import Optional, List


class SubscriptionEntry:
    """Model for a subscription/service in the Subscriptions database."""

    def __init__(
        self,
        name: str,
        service_type: str,
        project: List[str],
        category: str,
        billed_currency: str = "USD",
        monthly_cost_usd: float = 0.0,
        monthly_cost_gbp: float = 0.0,
        billing_cycle: str = "Monthly",
        next_renewal: Optional[date] = None,
        status: str = "Active",
        credits_included: float = 0,
        credits_used: float = 0,
        usage_usd: float = 0.0,
        usage_gbp: float = 0.0,
        auto_tracked: bool = False,
        notes: str = "",
    ):
        self.name = name
        self.service_type = service_type
        self.project = project
        self.category = category
        self.billed_currency = billed_currency
        self.monthly_cost_usd = monthly_cost_usd
        self.monthly_cost_gbp = monthly_cost_gbp
        self.billing_cycle = billing_cycle
        self.next_renewal = next_renewal
        self.status = status
        self.credits_included = credits_included
        self.credits_used = credits_used
        self.usage_usd = usage_usd
        self.usage_gbp = usage_gbp
        self.auto_tracked = auto_tracked
        self.notes = notes

    def to_notion_properties(self) -> dict:
        """Convert to Notion database properties format."""
        properties = {
            "Name": {"title": [{"text": {"content": self.name}}]},
            "Service Type": {"select": {"name": self.service_type}},
            "Project": {"multi_select": [{"name": p} for p in self.project]},
            "Category": {"select": {"name": self.category}},
            "Billed Currency": {"select": {"name": self.billed_currency}},
            "Monthly Cost USD": {"number": self.monthly_cost_usd},
            "Monthly Cost GBP": {"number": self.monthly_cost_gbp},
            "Billing Cycle": {"select": {"name": self.billing_cycle}},
            "Status": {"select": {"name": self.status}},
            "Credits Included": {"number": self.credits_included},
            "Credits Used": {"number": self.credits_used},
            "Usage USD": {"number": self.usage_usd},
            "Usage GBP": {"number": self.usage_gbp},
            "Auto Tracked": {"checkbox": self.auto_tracked},
            "Notes": {"rich_text": [{"text": {"content": self.notes[:2000]}}]},
        }

        if self.next_renewal:
            properties["Next Renewal"] = {
                "date": {"start": self.next_renewal.isoformat()}
            }

        return properties

    def __str__(self):
        return f"{self.name} ({self.service_type}) - ${self.monthly_cost_usd}/mo"


class UsageLogEntry:
    """Model for a single usage log entry."""

    def __init__(
        self,
        service: str,
        usage_date: date,
        project: List[str],
        category: str,
        usage_amount: float = 0.0,
        unit: str = "USD",
        cost_usd: float = 0.0,
        cost_gbp: float = 0.0,
        source: str = "Auto",
        notes: str = "",
    ):
        self.service = service
        self.usage_date = usage_date
        self.project = project
        self.category = category
        self.usage_amount = usage_amount
        self.unit = unit
        self.cost_usd = cost_usd
        self.cost_gbp = cost_gbp
        self.source = source
        self.notes = notes

    @property
    def entry_title(self) -> str:
        """Auto-generate title: 'Service - Project - YYYY-MM-DD'."""
        project_str = self.project[0] if self.project else "General"
        return f"{self.service} - {project_str} - {self.usage_date.isoformat()}"

    def to_notion_properties(self) -> dict:
        """Convert to Notion database properties format."""
        return {
            "Entry": {"title": [{"text": {"content": self.entry_title}}]},
            "Date": {"date": {"start": self.usage_date.isoformat()}},
            "Service": {"select": {"name": self.service}},
            "Project": {"multi_select": [{"name": p} for p in self.project]},
            "Category": {"select": {"name": self.category}},
            "Usage Amount": {"number": self.usage_amount},
            "Unit": {"select": {"name": self.unit}},
            "Cost USD": {"number": round(self.cost_usd, 4)},
            "Cost GBP": {"number": round(self.cost_gbp, 4)},
            "Source": {"select": {"name": self.source}},
            "Notes": {"rich_text": [{"text": {"content": self.notes[:2000]}}]},
        }

    def __str__(self):
        return f"{self.entry_title}: ${self.cost_usd:.4f} / \u00a3{self.cost_gbp:.4f}"
