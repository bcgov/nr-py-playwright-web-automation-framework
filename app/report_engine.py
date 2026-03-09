# app/report_engine.py
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
import os

from app.pdf_tools import pdf_to_images
from app.ui_actions import (
    click_selector,
    fill_input,
    select_dropdown,       # native <select>
    set_checkbox,
    set_dropdown_by_text,  # PrimeFaces dropdown
    select_checkbox_menu,  # PrimeFaces multi-checkbox menu
)


def _apply_input(page, spec: Dict[str, Any]):

    itype = (spec.get("type") or "").lower()
    sel = spec.get("selector")
    val = spec.get("value")

    # ---------- TEXT INPUT ----------
    if itype == "input":
        fill_input(page, sel, val)

    # ---------- PRIMEFACES DROPDOWN ----------
    elif itype == "dropdown":
        set_dropdown_by_text(page, sel, val)

    # ---------- NATIVE <select> ----------
    elif itype == "native_select":
        select_dropdown(page, sel, val)

    # ---------- SINGLE CHECKBOX ----------
    elif itype == "checkbox":

        desired = bool(spec.get("value", True))

        # if selector targets label
        if sel and sel.startswith('label:has-text("'):
            click_selector(page, sel)
        else:
            set_checkbox(page, sel, checked=desired)

    # ---------- PRIMEFACES CHECKBOX DROPDOWN ----------
    elif itype == "checkbox_dropdown":
        options = spec.get("values", [])
        select_all = spec.get("select_all", False)

        # ONLY proceed if we actually have work to do
        if options or select_all:
            # open dropdown
            click_selector(page, sel)

            panel = page.locator(".ui-selectcheckboxmenu-panel:visible").first
            panel.wait_for(state="visible", timeout=5000)
            page.wait_for_timeout(300)

            if select_all:
                # ... (your select all logic)
                pass 
            else:
                select_checkbox_menu(page, sel, options)

            # Close panel
            page.keyboard.press("Escape")
            
            # Use a shorter timeout for hidden to avoid 30s hangs
            try:
                panel.wait_for(state="hidden", timeout=2000)
            except:
                # If Escape didn't work, try clicking the trigger again or clicking outside
                click_selector(page, sel) 
        else:
            print(f"Skipping {sel} because no values were provided.")

    # ---------- GENERIC CLICK ----------
    elif itype == "click":
        click_selector(page, sel)

    # ---------- FALLBACK ----------
    else:
        if sel:
            click_selector(page, sel)


def _run_single(page, name: str, entry: Dict[str, Any], downloads: Path, shots: Path):

    # Navigate to report
    click_selector(page, entry["menu_selector"])
    click_selector(page, entry["report_selector"])

    # 1. Wait for the report page to load stable
    page.wait_for_load_state("networkidle")

    # 2. Setup the Page Screenshots folder directly under 'output'
    # 'downloads.parent' gets the 'output' directory if downloads is 'output/downloads'
    output_root = downloads.parent 
    page_shots_dir = output_root / "page_screenshots"
    page_shots_dir.mkdir(parents=True, exist_ok=True)
        
    # FIX: Use 'name' instead of 'report_name'
    screenshot_path = page_shots_dir / f"{name}_initial.png"
    
    # 3. Take the WHOLE PAGE screenshot
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"Captured initial page for {name}: {screenshot_path}")

    # Fill inputs
    inputs = entry.get("inputs") or {}

    for _, spec in inputs.items():
        _apply_input(page, spec)

    # Download PDF
    with page.expect_download() as dl:
        click_selector(page, entry["download_button"])

    pdf_path = downloads / f"{name}_{int(time.time())}.pdf"
    dl.value.save_as(str(pdf_path))

    # 4. Convert PDF → images and save to 'output/PDF_screenshots'
    # We rename the folder usage here
    pdf_shots_dir = output_root / "PDF_screenshots"
    pdf_shots_dir.mkdir(parents=True, exist_ok=True)
    
    images = pdf_to_images(pdf_path, pdf_shots_dir)

    return str(pdf_path), images


def run_reports_from_yaml(
    page,
    yaml_path: str,
    which: Optional[List[str]] = None,
    output_dir: str = "output",
):

    """
    Load config/reports.yaml and run one or more reports.
    """

    cfg = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))

    app_url = cfg["app_url"]
    reports = cfg["reports"]

    # Output directories
    out = Path(output_dir)
    downloads = out / "downloads"
    screenshots = out / "screenshots"

    downloads.mkdir(parents=True, exist_ok=True)
    screenshots.mkdir(parents=True, exist_ok=True)

    # Open app
    page.goto(app_url)
    page.wait_for_load_state("domcontentloaded")

    targets = which or list(reports.keys())

    results: Dict[str, Dict[str, Any]] = {}

    for name in targets:

        pdf, imgs = _run_single(
            page,
            name,
            reports[name],
            downloads,
            screenshots,
        )

        results[name] = {
            "pdf": pdf,
            "screenshots": imgs,
        }

    return results