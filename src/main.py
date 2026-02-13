"""
Main orchestrator for Cost & Subscription Tracker.
Fetches API usage data, creates/updates Notion entries.
"""

import os
import sys
import time
import yaml
from datetime import date
from dotenv import load_dotenv

from .utils.logger import setup_logger
from .notion_client import NotionClient
from .apify_client import ApifyUsageClient
from .anthropic_client import AnthropicUsageClient
from .currency import usd_to_gbp
from .models import SubscriptionEntry
from .dashboard import generate_dashboard


class CostTrackerApp:
    """Main application class."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir

        # Load environment variables (from .env locally, or injected by GitHub Actions)
        env_file = os.path.join(config_dir, ".env")
        if os.path.exists(env_file):
            load_dotenv(env_file)

        # Load YAML config
        config_file = os.path.join(config_dir, "config.yaml")
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)

        # Setup logger
        log_level = self.config["logging"]["level"]
        log_file = self.config["logging"]["file"]
        self.logger = setup_logger("cost_tracker", log_file, log_level)

        self.logger.info("=" * 60)
        self.logger.info(
            f"Starting {self.config['app']['name']} v{self.config['app']['version']}"
        )
        self.logger.info("=" * 60)

        # Stats
        self.stats = {
            "usage_entries_created": 0,
            "subscriptions_updated": 0,
            "subscriptions_seeded": 0,
            "errors": 0,
            "apify_total_usd": 0.0,
            "anthropic_total_usd": 0.0,
        }

        # Initialize clients
        self._init_clients()

    def _init_clients(self):
        """Initialize all API clients."""
        # Notion (required)
        notion_token = os.getenv("NOTION_TOKEN")
        subs_db_id = os.getenv("NOTION_SUBSCRIPTIONS_DB_ID")
        usage_db_id = os.getenv("NOTION_USAGE_LOG_DB_ID")

        if not all([notion_token, subs_db_id, usage_db_id]):
            self.logger.error(
                "Missing required env vars: NOTION_TOKEN, "
                "NOTION_SUBSCRIPTIONS_DB_ID, NOTION_USAGE_LOG_DB_ID"
            )
            sys.exit(1)

        self.notion = NotionClient(
            token=notion_token,
            subscriptions_db_id=subs_db_id,
            usage_log_db_id=usage_db_id,
            default_icon=self.config["notion"]["default_icon"],
        )

        if not self.notion.test_connection():
            self.logger.error("Failed to connect to Notion databases")
            sys.exit(1)

        # Apify (optional but enabled by default)
        self.apify_client = None
        apify_config = self.config["services"]["apify"]
        if apify_config.get("enabled"):
            apify_token = os.getenv("APIFY_TOKEN")
            if apify_token:
                self.apify_client = ApifyUsageClient(
                    token=apify_token,
                    actor_project_map=apify_config.get("actor_project_map", {}),
                    default_project=apify_config.get("default_project", "General"),
                    default_category=apify_config.get("default_category", "Work"),
                    project_categories=self.config.get("project_categories", {}),
                )
                self.logger.info("Apify usage client initialized")
            else:
                self.logger.warning("APIFY_TOKEN not set, skipping Apify tracking")

        # Anthropic (optional, disabled by default)
        self.anthropic_client = None
        anthropic_config = self.config["services"]["anthropic"]
        if anthropic_config.get("enabled"):
            admin_key = os.getenv("ANTHROPIC_ADMIN_API_KEY")
            if admin_key:
                self.anthropic_client = AnthropicUsageClient(
                    admin_api_key=admin_key,
                    default_project=anthropic_config.get("default_project", "General"),
                    default_category=anthropic_config.get("default_category", "Work"),
                )
                self.logger.info("Anthropic usage client initialized")
            else:
                self.logger.info("ANTHROPIC_ADMIN_API_KEY not set, skipping")

        self.logger.info("All clients initialized")

    def seed_subscriptions(self):
        """Create subscription entries from config if they don't exist."""
        subs_config = self.config.get("subscriptions", [])
        if not subs_config:
            return

        self.logger.info(f"Checking {len(subs_config)} subscriptions from config...")

        for sub_conf in subs_config:
            try:
                sub = SubscriptionEntry(
                    name=sub_conf["name"],
                    service_type=sub_conf["service_type"],
                    project=sub_conf["project"],
                    category=sub_conf["category"],
                    billed_currency=sub_conf.get("billed_currency", "USD"),
                    monthly_cost_usd=sub_conf.get("monthly_cost_usd", 0),
                    monthly_cost_gbp=sub_conf.get("monthly_cost_gbp", 0),
                    billing_cycle=sub_conf.get("billing_cycle", "Monthly"),
                    status=sub_conf.get("status", "Active"),
                    auto_tracked=sub_conf.get("auto_tracked", False),
                    notes=sub_conf.get("notes", ""),
                )

                result = self.notion.create_subscription(sub)
                if result:
                    self.stats["subscriptions_seeded"] += 1

                time.sleep(0.35)

            except Exception as e:
                self.logger.error(f"Error seeding subscription '{sub_conf.get('name')}': {e}")
                self.stats["errors"] += 1

    def fetch_apify_usage(self):
        """Fetch Apify usage and create log entries."""
        if not self.apify_client:
            return

        self.logger.info("Fetching Apify usage data...")

        try:
            entries, total_usd, credits_used = self.apify_client.build_usage_entries()
            self.stats["apify_total_usd"] = total_usd
            total_gbp = usd_to_gbp(total_usd)

            # Create usage log entries
            for entry in entries:
                result = self.notion.create_usage_entry(entry)
                if result:
                    self.stats["usage_entries_created"] += 1
                time.sleep(0.35)

            # Update Apify subscription row
            sub_page = self.notion.find_subscription_by_name("Apify")
            if sub_page:
                self.notion.update_subscription_usage(
                    page_id=sub_page["id"],
                    credits_used=credits_used,
                    usage_usd=total_usd,
                    usage_gbp=total_gbp,
                )
                self.stats["subscriptions_updated"] += 1
                self.logger.info(f"Updated Apify: ${total_usd:.2f} / \u00a3{total_gbp:.2f}")

        except Exception as e:
            self.logger.error(f"Error fetching Apify usage: {e}", exc_info=True)
            self.stats["errors"] += 1

    def fetch_anthropic_usage(self):
        """Fetch Anthropic usage and create log entries."""
        if not self.anthropic_client:
            return

        self.logger.info("Fetching Anthropic usage data...")

        try:
            entries, total_cost = self.anthropic_client.build_usage_entries()
            self.stats["anthropic_total_usd"] = total_cost
            total_gbp = usd_to_gbp(total_cost)

            for entry in entries:
                result = self.notion.create_usage_entry(entry)
                if result:
                    self.stats["usage_entries_created"] += 1
                time.sleep(0.35)

            # Update Claude API subscription row
            sub_page = self.notion.find_subscription_by_name("Claude API")
            if sub_page:
                self.notion.update_subscription_usage(
                    page_id=sub_page["id"],
                    credits_used=0,
                    usage_usd=total_cost,
                    usage_gbp=total_gbp,
                )
                self.stats["subscriptions_updated"] += 1

        except Exception as e:
            self.logger.error(f"Error fetching Anthropic usage: {e}", exc_info=True)
            self.stats["errors"] += 1

    def build_dashboard(self):
        """Generate the HTML dashboard from current Notion data."""
        self.logger.info("Generating dashboard...")

        try:
            subscriptions = self.notion.get_all_subscriptions()
            usage_entries = self.notion.get_current_month_usage()

            # Output to docs/ for GitHub Pages
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(script_dir)
            output_path = os.path.join(project_dir, "docs", "index.html")

            generate_dashboard(subscriptions, usage_entries, output_path)
            self.logger.info(f"Dashboard written to {output_path}")

        except Exception as e:
            self.logger.error(f"Error generating dashboard: {e}", exc_info=True)
            self.stats["errors"] += 1

    def run(self):
        """Run the main application."""
        start_time = time.time()

        try:
            self.seed_subscriptions()
            self.fetch_apify_usage()
            self.fetch_anthropic_usage()
            self.build_dashboard()

            elapsed = time.time() - start_time
            self.logger.info("=" * 60)
            self.logger.info("EXECUTION SUMMARY")
            self.logger.info("=" * 60)
            self.logger.info(f"Subscriptions seeded: {self.stats['subscriptions_seeded']}")
            self.logger.info(f"Subscriptions updated: {self.stats['subscriptions_updated']}")
            self.logger.info(f"Usage entries created: {self.stats['usage_entries_created']}")
            self.logger.info(f"Apify total: ${self.stats['apify_total_usd']:.2f}")
            self.logger.info(f"Anthropic total: ${self.stats['anthropic_total_usd']:.2f}")
            self.logger.info(f"Errors: {self.stats['errors']}")
            self.logger.info(f"Execution time: {elapsed:.1f}s")
            self.logger.info("=" * 60)

        except KeyboardInterrupt:
            self.logger.warning("Interrupted by user")

        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Main entry point."""
    try:
        # Determine config directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(os.path.dirname(script_dir), "config")

        app = CostTrackerApp(config_dir=config_dir)
        app.run()

        sys.exit(1 if app.stats["errors"] > 0 else 0)

    except SystemExit:
        raise
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
