"""
Take screenshots of the Discovery Rigor Engine Streamlit app.
Saves PNG files to docs/screenshots/.
Run with: python scripts/take_screenshots.py
Requires the Streamlit app to be running on http://127.0.0.1:8501
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8501"
OUT_DIR = Path("docs/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORT = {"width": 1280, "height": 800}


def wait(page, ms=1500):
    page.wait_for_timeout(ms)


def scroll_to(page, y=0):
    page.evaluate(
        f"document.querySelector('section.stMain')?.scrollTo(0, {y});"
    )
    wait(page, 400)


def nav_to(page, label):
    """Click a sidebar nav item by label text."""
    page.evaluate(
        f"""
        var labels = Array.from(document.querySelectorAll(
            '[data-testid="stSidebarNav"] label, [data-testid="stSidebar"] label'
        ));
        var match = labels.find(l => l.textContent.trim() === '{label}');
        if (match) match.click();
        """
    )
    wait(page, 2500)


def click_button_by_text(page, text):
    """Click a Streamlit button by its visible label."""
    page.evaluate(
        f"""
        var btns = Array.from(document.querySelectorAll('button'));
        var match = btns.find(b => b.textContent.trim() === '{text}');
        if (match) match.click();
        """
    )


def click_tab(page, label):
    page.evaluate(
        f"""
        var tabs = Array.from(document.querySelectorAll('[data-testid="stTab"]'));
        var match = tabs.find(t => t.textContent.trim() === '{label}');
        if (match) match.click();
        """
    )
    wait(page, 800)


def expand_first_visible_expander(page):
    page.evaluate(
        """
        var summaries = Array.from(
            document.querySelectorAll('[data-testid="stExpander"] summary')
        );
        var visible = summaries.filter(s => {
            var r = s.getBoundingClientRect();
            return r.top > 50 && r.width > 0 && r.height > 0;
        });
        if (visible.length > 0) visible[0].click();
        """
    )
    wait(page, 800)


def shot(page, filename):
    path = OUT_DIR / filename
    page.screenshot(path=str(path), full_page=False)
    print(f"  saved: {filename}")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT)

        print("Navigating to app...")
        page.goto(BASE_URL)
        wait(page, 3000)

        # ── 1. HOME PAGE (no study loaded) ───────────────────────────────────
        print("1. Home page (empty state)...")
        scroll_to(page, 0)
        shot(page, "01-home.png")

        # ── 2. LOAD SAMPLE STUDY ─────────────────────────────────────────────
        print("2. Loading sample study...")
        click_button_by_text(page, "Load Sample Study")
        wait(page, 2500)  # wait for state update

        # Scroll down to show the "Currently loaded study" metrics section
        scroll_to(page, 9999)
        wait(page, 600)
        shot(page, "02-home-loaded-study.png")

        # ── 3. ASSUMPTION MAP ────────────────────────────────────────────────
        print("3. Assumption Map...")
        nav_to(page, "Assumption Map")
        scroll_to(page, 0)
        shot(page, "03-assumption-map-top.png")

        # Scroll to first sliders + rationale captions
        scroll_to(page, 450)
        shot(page, "04-assumption-map-sliders.png")

        # ── 4. SCRIPT REVIEW ─────────────────────────────────────────────────
        print("4. Script Review...")
        nav_to(page, "Script Review")
        scroll_to(page, 0)
        shot(page, "05-script-review-input.png")

        # ── 5. SYNTHESIS — run pipeline ──────────────────────────────────────
        print("5. Synthesis — navigating and running pipeline...")
        nav_to(page, "Synthesis")
        scroll_to(page, 0)
        wait(page, 1000)

        # Check if synthesis results already exist
        has_results = page.evaluate(
            "document.querySelectorAll('[data-testid=\"stTab\"]').length >= 3"
        )

        if not has_results:
            # Capture the pre-run state (sessions loaded)
            shot(page, "06-synthesis-prerun.png")

            # Click "Run synthesis"
            print("   Running synthesis pipeline (this takes ~90 seconds)...")
            click_button_by_text(page, "Run synthesis")
            wait(page, 5000)

            # Take a mid-run screenshot showing node progress
            shot(page, "07-synthesis-running.png")

            # Wait for all 5 nodes to complete
            for i in range(24):  # up to 120 seconds (24 x 5s)
                time.sleep(5)
                done = page.evaluate(
                    "document.querySelectorAll('[data-testid=\"stTab\"]').length >= 3"
                )
                if done:
                    print(f"   Pipeline complete after ~{(i+1)*5}s")
                    break
            else:
                print("   WARNING: synthesis timed out, capturing current state")
        else:
            print("   Synthesis results already present, skipping run.")

        # ── 6. SYNTHESIS RESULT SCREENSHOTS ──────────────────────────────────
        # Decision tab
        print("6. Synthesis — Decision tab...")
        click_tab(page, "Decision")
        scroll_to(page, 0)
        wait(page, 600)
        shot(page, "08-synthesis-decision.png")

        # Scroll to confidence breakdown
        scroll_to(page, 650)
        wait(page, 400)
        shot(page, "09-synthesis-confidence.png")

        # Insights tab
        print("7. Synthesis — Insights tab...")
        click_tab(page, "Insights")
        scroll_to(page, 0)
        wait(page, 600)
        shot(page, "10-synthesis-insights.png")

        # Expand first insight card
        expand_first_visible_expander(page)
        shot(page, "11-synthesis-insight-expanded.png")

        # Evidence Chain tab
        print("8. Synthesis — Evidence Chain tab...")
        click_tab(page, "Evidence Chain")
        scroll_to(page, 0)
        wait(page, 600)
        shot(page, "12-evidence-chain.png")

        # Expand first evidence entry
        expand_first_visible_expander(page)
        scroll_to(page, 200)
        wait(page, 400)
        shot(page, "13-evidence-chain-expanded.png")

        browser.close()
        print(f"\nDone. All screenshots saved to {OUT_DIR.resolve()}")


if __name__ == "__main__":
    run()
