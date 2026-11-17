import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import config
from core.human import human_delay, human_scroll

class HealthChecker:
    @staticmethod
    def _sanitize_filename(url: str) -> str:
        parsed = urlparse(url)
        domain = parsed.netloc.replace(":", "_").replace(".", "_")
        if not domain:
            domain = re.sub(r"[^a-zA-Z0-9_-]", "_", url)
        return domain

    @classmethod
    async def check_homepage(cls, page, homepage_url: str, phase: str = "before") -> dict:
        """
        Visits the homepage, scrolls like a human, checks for critical/fatal errors,
        and captures a high-resolution screenshot.
        """
        result = {
            "phase": phase,
            "url": homepage_url,
            "status_code": 0,
            "is_healthy": True,
            "detected_errors": [],
            "screenshot_path": None,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        try:
            # Navigate to homepage
            response = await page.goto(
                homepage_url,
                wait_until="domcontentloaded",
                timeout=config.PAGE_TIMEOUT_MS,
            )

            if response:
                result["status_code"] = response.status
                if response.status >= 400:
                    result["is_healthy"] = False
                    result["detected_errors"].append(f"HTTP Status {response.status}")

            await human_delay(1.0, 2.0)
            await human_scroll(page, "down", 350)
            await human_delay(0.5, 1.0)
            await human_scroll(page, "up", 350)

            # Retrieve text content of page to scan for PHP fatal/critical errors
            content = await page.content()
            content_lower = content.lower()

            for pattern in config.FATAL_ERROR_PATTERNS:
                if pattern in content_lower:
                    result["is_healthy"] = False
                    result["detected_errors"].append(f"Fatal error string found: '{pattern}'")

            # Check for White Screen of Death (empty body)
            body_text = await page.inner_text("body")
            if not body_text or len(body_text.strip()) < 10:
                result["is_healthy"] = False
                result["detected_errors"].append("White Screen of Death detected (body is empty).")

            # Capture Screenshot
            safe_name = cls._sanitize_filename(homepage_url)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_{phase}_{timestamp}.png"
            screenshot_file = config.SCREENSHOTS_DIR / filename

            await page.screenshot(path=str(screenshot_file), full_page=False)
            result["screenshot_path"] = str(screenshot_file)

        except Exception as e:
            result["is_healthy"] = False
            result["detected_errors"].append(f"Navigation/Check Exception: {str(e)}")

        return result

