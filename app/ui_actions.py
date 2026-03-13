# app/ui_actions.py
from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
import os
from typing import List
from playwright.sync_api import Page, expect, Locator

def _slug(text: str) -> str:
    """Safe for filenames across OSes: keep alnum, dash, underscore, dot; replace spaces with underscores."""
    return re.sub(r"[^A-Za-z0-9_\-\.]", "", text.strip().replace(" ", "_"))


def get_screenshot_path(filename: str) -> str:
    # Creates 'output/dropdown_screenshots' if it doesn't exist
    base_dir = os.getenv("SCREENSHOT_DIR", "output/dropdown_screenshots")
    folder = Path(base_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return str(folder / f"{_slug(filename)}_{ts}.png")

def select_dropdown(page, selector, value):
    """Handles native <select> elements"""
    element = page.locator(selector)
    element.scroll_into_view_if_needed()
    
    # Select the option
    element.select_option(label=value)
    
    # --- ELEMENT-ONLY SCREENSHOT ---
    # Captures only the menu, not the whole browser window   
    path = get_screenshot_path(f"dropdown_{value}")
    element.screenshot(path=path)
    print(f"[screenshot saved] {path}")

def fill_input(page, selector, value):
    element = page.locator(selector)
    # 1. Click to focus and clear any existing default text
    element.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
 
    # 2. Clear the field manually if .fill() isn't working perfectly
    element.fill("")
    page.wait_for_timeout(50)

    # 3. Type the new value
    element.type(str(value), delay=50) 
    # 4. CRITICAL: Press Tab to trigger the 'onchange' or 'onblur' event
    element.press("Tab")

def set_checkbox(page, selector, checked=True):
    box = page.locator(f"{selector} .ui-chkbox-box")
    class_attr = box.get_attribute("class") or ""
    is_checked = "ui-state-active" in class_attr

    if checked != is_checked:
        box.click()

def _parse_role_selector(selector: str):
    m = re.match(r'^role=(\w+)\[name="(.+)"\]$', selector.strip())
    if not m:
        return None, None
    return m.group(1), m.group(2)


def click_selector(page, selector: str):
    if selector.startswith("role="):
        role, name = _parse_role_selector(selector)
        if role and name:
            page.get_by_role(role, name=name).click()
        else:
            page.locator(selector).click()  # fallback
    elif selector.startswith("text="):
        page.get_by_text(selector.split("=", 1)[1], exact=True).click()
    else:
        page.locator(selector).click()

def select_menu(
    page, menu_selector, expanded_selector=None, screenshot_path=None, wait_ms=500
):
    """
    Click a menu, wait for dropdown expansion, and optionally take a screenshot.
    """
    # --- 1️⃣ Click the menu ---
    if menu_selector.startswith("role="):
        role, name = _parse_role_selector(menu_selector)
        if role and name:
            page.get_by_role(role, name=name).click()
        else:
            page.locator(menu_selector).click()
    elif menu_selector.startswith("text="):
        page.get_by_text(menu_selector.split("=", 1)[1], exact=True).click()
    else:
        page.locator(menu_selector).click()

    # --- 2️⃣ Wait for the menu to expand ---
    page.wait_for_timeout(wait_ms)

    # --- 3️⃣ Take element-only screenshot ---
    if screenshot_path:
        Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)

        if expanded_selector:
            page.locator(expanded_selector).screenshot(path=screenshot_path)
        else:
            page.screenshot(path=screenshot_path, full_page=True)

        print(f"[screenshot saved] {screenshot_path}")

def select_checkbox_menu(page, selector, options):
    # Find the active panel
    panel = page.locator(".ui-selectcheckboxmenu-panel:visible").first
    panel.wait_for(state="visible")

    # --- ELEMENT-ONLY SCREENSHOT ---
    panel.screenshot(path=get_screenshot_path("checkbox_menu"))

    for opt in options:
        # Find the specific row
        item = panel.locator(".ui-selectcheckboxmenu-item").filter(has_text=opt).first
        
        # Verify the item exists to avoid silent skips
        if item.count() == 0:
            print(f"Warning: Option '{opt}' not found in dropdown.")
            continue

        # Target the checkbox box
        checkbox = item.locator(".ui-chkbox-box")
        
        # Check current state
        classes = checkbox.get_attribute("class") or ""
        if "ui-state-active" not in classes:
            # 1. Bring it into view (crucial for long lists)
            item.scroll_into_view_if_needed()
            
            # 2. Correct method for Locator is dispatch_event
            checkbox.dispatch_event("click")
            
            # 3. Give PrimeFaces a moment to update the DOM
            page.wait_for_timeout(300)

def set_dropdown_by_text(page, selector, val):
    # 1. Click the trigger button (the one with the triangle icon)
    trigger = page.locator(selector)
    trigger.click()

    # 2. Find the popup list. 
    # In PrimeFaces, Autocomplete/Select menus usually use these panel classes.
    # We look for the visible one.
    panel = page.locator(".ui-autocomplete-panel:visible, .ui-selectonemenu-panel:visible").first
    panel.wait_for(state="visible", timeout=3000)

    # 3. ELEMENT-ONLY SCREENSHOT of the open panel (preferred)
    path = get_screenshot_path(f"dropdown_{val}")
    panel.screenshot(path=path)
    print(f"[screenshot saved] {path}")

    # 4. Small delay to allow the list to populate/animate
    page.wait_for_timeout(300)

    # 5. Target the <li> item specifically.
    # We can use the class the recorder found: .ui-autocomplete-item
    target_item = panel.locator("li").filter(has_text=val).first
    
    # 6. Click the item
    target_item.click()

    # 7. Wait for the panel to disappear
    panel.wait_for(state="hidden", timeout=2000)

def set_checkbox_by_label(page: Page, label_text: str, desired: bool) -> None:
    """Set checkbox state using label text."""

    # 1. Try standard HTML checkbox
    try:
        cb = page.get_by_label(label_text)
        cb.set_checked(desired)
        return
    except Exception:
        pass

    # 2. PrimeFaces checkbox
    label = page.locator(f'label:has-text("{label_text}")').first
    label.wait_for(state="visible")

    container = label.locator("xpath=ancestor::*[contains(@class,'ui-chkbox')][1]")
    box = container.locator(".ui-chkbox-box")

    # determine current state
    is_checked = "ui-state-active" in (box.get_attribute("class") or "")

    if is_checked != desired:
        box.click()

def select_menu_item(page, item_selector):
    """
    Click an item inside an expanded dropdown menu.
    """
    if item_selector.startswith("role="):
        role, name = _parse_role_selector(item_selector)
        if role and name:
            page.get_by_role(role, name=name).click()
        else:
            page.locator(item_selector).click()
    else:
        page.locator(item_selector).click()