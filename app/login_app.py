# app/login_app.py  (replace your function body with this approach)
from __future__ import annotations
import re
from pathlib import Path
from playwright.sync_api import TimeoutError as PWTimeout

AUTH_FILE = Path("config/auth_state.json")
AAD_HOST_RE = re.compile(r"(login\.microsoftonline\.com|login\.microsoft\.com)")
APP_HOST_RE = re.compile(r"(?:^|://)testapps\.nrs\.gov\.bc\.ca(?:/|$)")

def app_login(page, context, app_url, email, password):
    print("Opening application for login...")
    page.goto(app_url, timeout=120_000, wait_until="domcontentloaded")

    # Did we already land on the app? If yes, save and return.
    try:
        page.wait_for_url(APP_HOST_RE, timeout=15_000)
        print("Already signed in.")
        context.storage_state(path=AUTH_FILE)
        print(f"✅ Auth saved to {AUTH_FILE}")
        return
    except PWTimeout:
        pass

    # Otherwise, wait for Azure AD login
    try:
        page.wait_for_url(AAD_HOST_RE, timeout=60_000)
        print("At Microsoft login...")
    except PWTimeout:
        # One more check in case a redirect just happened
        page.wait_for_url(APP_HOST_RE, timeout=60_000)
        print("Reached app without explicit AAD step.")
        context.storage_state(path=AUTH_FILE)
        print(f"✅ Auth saved to {AUTH_FILE}")
        return

    # Enter creds if provided (passwordless or interactive also supported)
    if email and password:
        page.wait_for_selector('input[type="email"]', timeout=60_000)
        page.fill('input[type="email"]', email)
        page.click('input[type="submit"]')

        page.wait_for_selector('input[type="password"]', timeout=60_000)
        page.fill('input[type="password"]', password)
        page.click('input[type="submit"]')

        # Stay signed in?
        try:
            page.wait_for_selector('input[value="Yes"]', timeout=10_000)
            page.click('input[value="Yes"]')
        except PWTimeout:
            pass

        # 🔴 IMPORTANT: Now wait until the APP host is reached (this parks the page during MFA)
        page.wait_for_url(APP_HOST_RE, timeout=180_000)
        print("Login successful; reached the app.")
        context.storage_state(path=AUTH_FILE)
        print(f"✅ Auth saved to {AUTH_FILE}")

    else:
        # Interactive/MFA-only path
        print("➡️  Complete Microsoft sign-in (MFA) in the browser window...")
        page.wait_for_url(APP_HOST_RE, timeout=180_000)
        context.storage_state(path=AUTH_FILE)
        print(f"✅ Auth saved to {AUTH_FILE}")