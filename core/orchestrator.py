import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import config
from core.health_checker import HealthChecker
from core.wp_updater import WPUpdater
from utils.reporter import Reporter

class UpdateOrchestrator:
    def __init__(self, raw_lines: list[str], headless: bool = False, log_callback=None, progress_callback=None, site_update_callback=None):
        self.raw_lines = raw_lines
        self.headless = headless
        self.log = log_callback or (lambda msg: print(f"[Orchestrator] {msg}"))
        self.progress = progress_callback or (lambda current, total, msg: None)
        self.site_update = site_update_callback or (lambda site_info: None)
        self.is_running = True

    def stop(self):
        self.is_running = False

    @staticmethod
    def parse_entry(line: str) -> dict:
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        if "|" in line:
            parts = [p.strip() for p in line.split("|", 1)]
            site_url = parts[0]
            temp_url = parts[1]
        else:
            temp_url = line
            parsed = urlparse(temp_url)
            site_url = f"{parsed.scheme}://{parsed.netloc}"

        return {
            "site_url": site_url.rstrip("/"),
            "temp_url": temp_url
        }

    async def _launch_browser(self, p):
        """
        Smart browser launcher:
        Uses real Google Chrome or Edge to prevent 'spawn UNKNOWN' errors and evade bot detection.
        Falls back to Chromium if needed.
        """
        channels = ["chrome", "msedge", None]
        for ch in channels:
            try:
                self.log(f"Launching browser engine (channel: {ch or 'chromium'}, headless: {self.headless})...")
                browser = await p.chromium.launch(
                    channel=ch,
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--start-maximized",
                        "--no-sandbox"
                    ]
                )
                self.log(f"Browser successfully initialized ({ch or 'chromium'}).")
                return browser
            except Exception as e:
                self.log(f"Channel {ch} unavailable ({e}), trying next...")
                continue

        # Ultimate fallback
        self.log("Falling back to headless Chromium...")
        return await p.chromium.launch(headless=True)

    async def run(self) -> dict:
        targets = []
        for line in self.raw_lines:
            parsed = self.parse_entry(line)
            if parsed:
                targets.append(parsed)

        total_sites = len(targets)
        if total_sites == 0:
            self.log("No valid site entries provided.")
            return {"results": [], "report_path": None}

        self.log(f"Starting professional update pipeline for {total_sites} website(s)...")
        results = []

        async with async_playwright() as p:
            browser = await self._launch_browser(p)

            for index, target in enumerate(targets, start=1):
                if not self.is_running:
                    self.log("Process stopped by user.")
                    break

                site_url = target["site_url"]
                temp_url = target["temp_url"]

                self.progress(index, total_sites, f"Processing {site_url}")
                self.log(f"\n=======================================================")
                self.log(f"[{index}/{total_sites}] Processing: {site_url}")
                self.log(f"=======================================================")

                site_result = {
                    "url": site_url,
                    "temp_url": temp_url,
                    "pre_check": {},
                    "update_summary": {},
                    "post_check": {},
                    "success": False
                }

                # Dedicated fresh browser context
                context = await browser.new_context(
                    viewport=config.DEFAULT_VIEWPORT,
                    user_agent=config.USER_AGENT
                )
                page = await context.new_page()

                try:
                    # --- STEP 1: PRE-CHECK HOMEPAGE ---
                    self.log("[Step 1/4] Running pre-update health check & taking baseline screenshot...")
                    pre_check = await HealthChecker.check_homepage(page, site_url, phase="before")
                    site_result["pre_check"] = pre_check
                    if not pre_check["is_healthy"]:
                        self.log(f"Notice: Homepage pre-check warnings: {pre_check['detected_errors']}")
                    else:
                        self.log(f"Pre-check passed! Homepage operational (HTTP {pre_check['status_code']}).")

                    self.site_update(site_result)

                    # --- STEP 2: LOGIN VIA TEMPORARY URL ---
                    self.log("[Step 2/4] Authenticating via temporary login URL...")
                    updater = WPUpdater(page, log_callback=self.log)
                    logged_in = await updater.login_with_temporary_url(temp_url)

                    if not logged_in:
                        self.log("Authentication failed. Skipping update for this site.")
                        site_result["update_summary"] = {"error": "Authentication failed"}
                    else:
                        # --- STEP 3: PERFORM UPDATES ---
                        self.log("[Step 3/4] Updating WordPress plugins & themes...")
                        update_summary = await updater.update_all_via_update_core()
                        site_result["update_summary"] = update_summary

                    # --- STEP 4: POST-CHECK HOMEPAGE ---
                    self.log("[Step 4/4] Verifying homepage after updates (Visual & Health Check)...")
                    await context.close()

                    # Independent fresh context to verify public frontend
                    pub_context = await browser.new_context(
                        viewport=config.DEFAULT_VIEWPORT,
                        user_agent=config.USER_AGENT
                    )
                    pub_page = await pub_context.new_page()

                    post_check = await HealthChecker.check_homepage(pub_page, site_url, phase="after")
                    site_result["post_check"] = post_check
                    site_result["success"] = post_check["is_healthy"]

                    if post_check["is_healthy"]:
                        self.log(f"VERIFIED SUCCESS: {site_url} is fully operational!")
                    else:
                        self.log(f"CRITICAL ALERT: Issues detected on {site_url} after updates: {post_check['detected_errors']}")

                    await pub_context.close()
                    self.site_update(site_result)

                except Exception as e:
                    self.log(f"Error encountered on {site_url}: {str(e)}")
                    site_result["error"] = str(e)
                    try:
                        await context.close()
                    except Exception:
                        pass

                results.append(site_result)

            try:
                await browser.close()
            except Exception:
                pass

        # Generate HTML Report
        report_path = Reporter.generate_html_report(results)
        self.log(f"\nAll operations complete! Report available at: {report_path}")

        return {
            "results": results,
            "report_path": report_path
        }
