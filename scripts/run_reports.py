
# scripts/run_reports.py
from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from app.login_app import app_login
from app.report_engine import run_reports_from_yaml

# --- Paths ---
ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
REPORTS_YAML = CONFIG_DIR / "reports.yaml"
AUTH_FILE = CONFIG_DIR / "auth_state.json"
OUTPUT_DIR = ROOT / "output"

# ---- .env (only used for first-time login if needed) ----
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

NAV_TIMEOUT_MS = 120_000  # 120s for SSO redirects

def safe_goto(page, url: str, *, timeout_ms: int = NAV_TIMEOUT_MS, attempts: int = 2):
    last_err = None
    for i in range(1, attempts + 1):
        try:
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            return
        except Exception as e:
            last_err = e
            print(f"[goto] attempt {i}/{attempts} failed: {e}")
    raise last_err

def load_app_url_from_yaml(yaml_path: Path) -> str:
    """Read app_url from reports.yaml."""
    cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return cfg["app_url"]


def main():   
    parser = argparse.ArgumentParser(
        description="Run ISP reports defined in config/reports.yaml"
    )
    parser.add_argument(
        "--reports",
        nargs="*",
        help=(
            "Report keys to run (default: all in YAML). "
            "Example: r10_mill_table_audit r11_lumber_chip_summary"
        ),
    )
    parser.add_argument(
        "--fresh-login",
        action="store_true",
        help="Force a fresh Microsoft login and save storage to config/auth_state.json.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless (default: headed).",
    )
    args = parser.parse_args()


    if not REPORTS_YAML.exists():
        raise FileNotFoundError(f"Missing YAML: {REPORTS_YAML}")
 
    APP_URL = load_app_url_from_yaml(REPORTS_YAML)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        
        # First-time or forced fresh login
        if args.fresh_login or not AUTH_FILE.exists():
            # Fresh login path: create a clean context and let app_login handle auth + storage save.
            context = browser.new_context()
            page = context.new_page()       

            if not EMAIL or not PASSWORD:
                print(
                    "ℹ️  EMAIL/PASSWORD not in environment; complete the Microsoft sign-in in the browser window."
                )
            app_login(page, context, APP_URL, EMAIL, PASSWORD)
            context.close()

        # Use the saved storage for actual report runs
        context = browser.new_context(storage_state=str(AUTH_FILE)) if AUTH_FILE.exists() else browser.new_context()
        page = context.new_page()
        
        # Navigate to the app before the engine runs
        safe_goto(page, APP_URL)
        print("Current URL after goto:", page.url)
        
        # Run reports from reports.yaml (all or selected)
        results = run_reports_from_yaml(
            page=page,
            yaml_path=str(REPORTS_YAML),
            which=args.reports,             # None => run all
            output_dir=str(OUTPUT_DIR),
        )

        # Friendly summary
        print("\n=== Run Summary ===")
        for name, info in results.items():
            print(f"✅ {name}")
            print(f"   PDF: {info['pdf']}")
            for img in info["screenshots"]:
                print(f"   IMG: {img}")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()