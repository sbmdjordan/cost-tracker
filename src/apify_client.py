"""
Apify API client for fetching usage and cost data.
Endpoints used:
  - GET /v2/users/me/usage/monthly — monthly + daily usage breakdown
  - GET /v2/users/me/limits — plan limits and current usage
  - GET /v2/actor-runs — individual runs with actId and usageTotalUsd
  - GET /v2/acts/{actorId} — resolve tilde IDs to hash IDs
"""

import logging
from datetime import date
from typing import Optional, List

from .utils.rate_limiter import robust_api_call
from .models import UsageLogEntry
from .currency import usd_to_gbp


APIFY_API_URL = "https://api.apify.com/v2"


class ApifyUsageClient:
    """Client for fetching Apify account usage data."""

    def __init__(
        self,
        token: str,
        actor_project_map: dict,
        default_project: str = "General",
        default_category: str = "Work",
        project_categories: dict = None,
    ):
        self.token = token
        self.actor_project_map = actor_project_map
        self.default_project = default_project
        self.default_category = default_category
        self.project_categories = project_categories or {}
        self.logger = logging.getLogger(__name__)
        self._resolved_ids = None

    def _get(self, path: str, params: dict = None) -> Optional[dict]:
        """Make authenticated GET request to Apify API."""
        url = f"{APIFY_API_URL}{path}"
        all_params = {"token": self.token}
        if params:
            all_params.update(params)
        try:
            return robust_api_call(url, params=all_params)
        except Exception as e:
            self.logger.error(f"Apify API error ({path}): {e}")
            return None

    def fetch_monthly_usage(self) -> Optional[dict]:
        """GET /v2/users/me/usage/monthly"""
        return self._get("/users/me/usage/monthly")

    def fetch_account_limits(self) -> Optional[dict]:
        """GET /v2/users/me/limits"""
        return self._get("/users/me/limits")

    def fetch_actor_runs(
        self,
        started_after: str = None,
        status: str = "SUCCEEDED",
        limit: int = 1000,
    ) -> Optional[list]:
        """GET /v2/actor-runs — returns list of run objects."""
        params = {"limit": limit, "desc": 1}
        if started_after:
            params["startedAfter"] = started_after
        if status:
            params["status"] = status

        result = self._get("/actor-runs", params=params)
        if result:
            return result.get("data", {}).get("items", [])
        return None

    def resolve_actor_ids(self) -> dict:
        """Resolve tilde-notation actor IDs to actual hash IDs.
        Returns mapping: hash_id -> project_name."""
        if self._resolved_ids is not None:
            return self._resolved_ids

        resolved = {}
        for tilde_id, project in self.actor_project_map.items():
            try:
                result = self._get(f"/acts/{tilde_id}")
                if result:
                    actual_id = result.get("data", {}).get("id", "")
                    if actual_id:
                        resolved[actual_id] = project
                        self.logger.info(f"Resolved {tilde_id} -> {actual_id} -> {project}")
            except Exception as e:
                self.logger.warning(f"Could not resolve {tilde_id}: {e}")

        self._resolved_ids = resolved
        return resolved

    def build_usage_entries(self, target_date: date = None) -> tuple:
        """Fetch Apify data and build UsageLogEntry objects.

        Returns:
            (entries: List[UsageLogEntry], total_usd: float, credits_used: float)
        """
        if target_date is None:
            target_date = date.today()

        entries = []
        total_usd = 0.0
        credits_used = 0.0

        # Step 1: Get monthly overview
        monthly = self.fetch_monthly_usage()
        if monthly:
            data = monthly.get("data", {})
            total_usd = (
                data.get("totalUsageCreditsUsdAfterVolumeDiscount", 0.0)
                or data.get("totalUsageCreditsUsdBeforeVolumeDiscount", 0.0)
                or 0.0
            )

        # Step 2: Get account limits for credit usage
        limits_data = self.fetch_account_limits()
        if limits_data:
            current = limits_data.get("data", {}).get("current", {})
            credits_used = current.get("monthlyUsageUsd", 0.0) or 0.0

        # Step 3: Get actor runs for project attribution
        cycle_start = None
        if monthly:
            cycle = monthly.get("data", {}).get("usageCycle", {})
            cycle_start = cycle.get("startAt")

        runs = self.fetch_actor_runs(started_after=cycle_start)

        if runs:
            id_map = self.resolve_actor_ids()

            # Group costs by project
            project_costs = {}
            project_run_count = {}

            for run in runs:
                act_id = run.get("actId", "")
                cost = run.get("usageTotalUsd", 0) or 0
                project = id_map.get(act_id, self.default_project)

                project_costs[project] = project_costs.get(project, 0) + cost
                project_run_count[project] = project_run_count.get(project, 0) + 1

            # Create one UsageLogEntry per project
            for project, cost in project_costs.items():
                run_count = project_run_count.get(project, 0)
                category = self.project_categories.get(project, self.default_category)
                entry = UsageLogEntry(
                    service="Apify",
                    usage_date=target_date,
                    project=[project],
                    category=category,
                    usage_amount=run_count,
                    unit="API Calls",
                    cost_usd=round(cost, 4),
                    cost_gbp=usd_to_gbp(cost),
                    source="Auto",
                    notes=f"{run_count} actor runs, cycle total ${total_usd:.2f}",
                )
                entries.append(entry)
                self.logger.info(f"  {project}: {run_count} runs, ${cost:.4f}")

        elif total_usd > 0:
            # Fallback: single entry if runs unavailable
            entry = UsageLogEntry(
                service="Apify",
                usage_date=target_date,
                project=[self.default_project],
                category=self.default_category,
                usage_amount=total_usd,
                unit="USD",
                cost_usd=round(total_usd, 4),
                cost_gbp=usd_to_gbp(total_usd),
                source="Auto",
                notes="Monthly total (run-level breakdown unavailable)",
            )
            entries.append(entry)

        return entries, total_usd, credits_used
