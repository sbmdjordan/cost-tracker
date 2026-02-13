"""
Anthropic API client for fetching usage and cost data.
Uses Admin API (requires sk-ant-admin... key):
  - GET /v1/organizations/cost_report — USD costs

Requires org-level admin API key. If unavailable, gracefully returns empty.
"""

import requests
import logging
from datetime import date
from typing import Optional, List

from .models import UsageLogEntry
from .currency import usd_to_gbp


ANTHROPIC_API_URL = "https://api.anthropic.com"


class AnthropicUsageClient:
    """Client for fetching Anthropic usage data via Admin API."""

    def __init__(
        self,
        admin_api_key: str,
        default_project: str = "General",
        default_category: str = "Work",
    ):
        self.admin_api_key = admin_api_key
        self.default_project = default_project
        self.default_category = default_category
        self.logger = logging.getLogger(__name__)

        self.headers = {
            "x-api-key": admin_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> Optional[dict]:
        """Make authenticated GET to Anthropic Admin API."""
        url = f"{ANTHROPIC_API_URL}{path}"
        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                self.logger.warning(
                    "Anthropic Admin API returned 403 -- "
                    "key may not have admin permissions"
                )
            else:
                self.logger.error(f"Anthropic API error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Anthropic API request error: {e}")
            return None

    def fetch_cost_report(self, start_date: date, end_date: date = None) -> Optional[dict]:
        """GET /v1/organizations/cost_report"""
        params = {
            "starting_at": f"{start_date.isoformat()}T00:00:00Z",
            "bucket_width": "1d",
            "group_by[]": "description",
        }
        if end_date:
            params["ending_at"] = f"{end_date.isoformat()}T23:59:59Z"

        return self._get("/v1/organizations/cost_report", params=params)

    def build_usage_entries(self, target_date: date = None) -> tuple:
        """Fetch Anthropic data and build UsageLogEntry objects.

        Returns:
            (entries: List[UsageLogEntry], total_cost_usd: float)
        """
        if target_date is None:
            target_date = date.today()

        entries = []
        total_cost = 0.0

        month_start = target_date.replace(day=1)
        cost_data = self.fetch_cost_report(month_start, target_date)

        if cost_data:
            for bucket in cost_data.get("data", []):
                for result in bucket.get("results", []):
                    amount_cents = float(result.get("amount", "0"))
                    amount_usd = amount_cents / 100.0
                    total_cost += amount_usd

            if total_cost > 0:
                entry = UsageLogEntry(
                    service="Anthropic",
                    usage_date=target_date,
                    project=[self.default_project],
                    category=self.default_category,
                    usage_amount=total_cost,
                    unit="USD",
                    cost_usd=round(total_cost, 4),
                    cost_gbp=usd_to_gbp(total_cost),
                    source="Auto",
                    notes=f"Month-to-date API cost as of {target_date}",
                )
                entries.append(entry)

        return entries, total_cost
