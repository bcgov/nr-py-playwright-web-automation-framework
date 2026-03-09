# app/ui_actions.py
from __future__ import annotations

import re
import time
import os
from typing import List
from playwright.sync_api import Page, expect, Locator

def get_screenshot_path(filename):
    # Creates 'output/dropdown_screenshots' if it doesn't exist
    folder = os.path.join("output", "dropdown_screenshots")
    if not os.path.exists(folder):
        os.makedirs(folder)
    return os.path.join(folder, f"{filename}_{int(time.time())}.png")

def select_dropdown(page, selector, value):
    """Handles native <select> elements"""
    element = page.locator(selector)
    element.scroll_into_view_if_needed()
    
    # Select the option
    element.select_option(label=value)
    
    # --- ELEMENT-ONLY SCREENSHOT ---
    # Captures only the menu, not the whole browser window
    panel.screenshot(path=get_screenshot_path(f"dropdown_{val}"))

def fill_input(page, selector, value):
    element = page.locator(selector)
    # 1. Click to focus and clear any existing default text
    element.click() 
    # 2. Clear the field manually if .fill() isn't working perfectly
    element.fill("") 
    # 3. Type the new value
    element.type(str(value), delay=50) 
    # 4. CRITICAL: Press Tab to trigger the 'onchange' or 'onblur' event
    element.press("Tab")

def set_checkbox(page, selector, checked=True):
    # Works for direct checkbox selectors; for labels, use click_selector('label:has-text("...")')
    if page.is_checked(selector) != checked:
        page.click(selector)

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

    # --- SCREENSHOT ---
    page.screenshot(path=f"dropdown_{val}_{int(time.time())}.png")

    # 3. Small delay to allow the list to populate/animate
    page.wait_for_timeout(300)

    # 4. Target the <li> item specifically.
    # We can use the class the recorder found: .ui-autocomplete-item
    target_item = panel.locator("li").filter(has_text=val).first
    
    # 5. Click the item
    target_item.click()

    # 6. Wait for the panel to disappear
    panel.wait_for(state="hidden", timeout=2000)