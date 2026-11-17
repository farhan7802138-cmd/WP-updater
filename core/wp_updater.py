import asyncio
import re
from urllib.parse import urlparse
import config
from core.human import human_delay, human_move_and_click, human_scroll, dismiss_wp_notices

class WPUpdater:
    def __init__(self, page, log_callback=None):
        self.page = page
        self.log = log_callback or (lambda msg: print(f"[WPUpdater] {msg}"))

    @staticmethod
    def extract_base_url(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    async def login_with_temporary_url(self, temp_login_url: str) -> bool:
        """
        Navigates to the temporary login URL, allows WordPress to authenticate,
        and verifies landing on the WP Admin dashboard.
        """
        self.log(f"Opening temporary login link...")
        await self.page.goto(temp_login_url, wait_until="networkidle", timeout=config.PAGE_TIMEOUT_MS)
        await human_delay(2.0, 3.5)

        # Check if landed in wp-admin
        current_url = self.page.url
        is_admin = "/wp-admin" in current_url

        # Check for admin bar or admin menu
        admin_bar = await self.page.query_selector("#wpadminbar")
        admin_menu = await self.page.query_selector("#adminmenu")

        if is_admin or admin_bar or admin_menu:
            self.log("Successfully logged in via temporary URL!")
            await dismiss_wp_notices(self.page)
            return True
        else:
            self.log(f"Warning: Login might have failed. Current URL: {current_url}")
            return False

    async def update_all_via_update_core(self) -> dict:
        """
        Navigates to /wp-admin/update-core.php to update all available plugins & themes
        in the native WordPress update center.
        """
        base_url = self.extract_base_url(self.page.url)
        update_core_url = f"{base_url}/wp-admin/update-core.php"

        update_summary = {
            "plugins_updated": 0,
            "themes_updated": 0,
            "plugin_details": [],
            "theme_details": [],
            "errors": []
        }

        self.log("Navigating to WordPress Updates center (/wp-admin/update-core.php)...")
        await self.page.goto(update_core_url, wait_until="domcontentloaded", timeout=config.PAGE_TIMEOUT_MS)
        await human_delay(1.5, 3.0)
        await dismiss_wp_notices(self.page)

        # --- 1. UPDATE PLUGINS ---
        plugins_table = await self.page.query_selector("#update-plugins-table")
        if plugins_table:
            self.log("Checking for plugin updates...")
            # Count plugins needing update
            plugin_checkboxes = await self.page.query_selector_all("#update-plugins-table tbody input[name='checked[]']")
            plugin_count = len(plugin_checkboxes)

            if plugin_count > 0:
                self.log(f"Found {plugin_count} plugin(s) needing updates.")
                # Human-like click 'Select All'
                select_all_btn = self.page.locator("#plugins-select-all")
                if await select_all_btn.is_visible():
                    await human_move_and_click(self.page, select_all_btn)
                    await human_delay(1.0, 2.0)

                # Click 'Update Plugins' button
                update_btn = self.page.locator("#upgrade-plugins")
                if await update_btn.is_visible():
                    self.log("Clicking 'Update Plugins' button...")
                    await human_move_and_click(self.page, update_btn)
                    
                    # Wait for update process to finish
                    self.log("Waiting for plugin updates to complete...")
                    try:
                        # Wait for success indicator or return link
                        success_indicator = self.page.locator(
                            "text=/All updates have been completed|Return to WordPress Updates|Return to Plugins page/"
                        )
                        await success_indicator.first.wait_for(timeout=180000)
                        update_summary["plugins_updated"] = plugin_count
                        self.log(f"Successfully finished updating {plugin_count} plugin(s)!")
                    except Exception as e:
                        self.log(f"Timeout or notice while updating plugins: {e}")
                        update_summary["errors"].append(f"Plugin update timeout/notice: {str(e)}")

                    await human_delay(2.0, 3.5)
            else:
                self.log("All plugins are already up to date.")
        else:
            self.log("No pending plugin updates found.")

        # --- 2. UPDATE THEMES ---
        # Go back to update-core.php for themes
        self.log("Checking for theme updates...")
        await self.page.goto(update_core_url, wait_until="domcontentloaded", timeout=config.PAGE_TIMEOUT_MS)
        await human_delay(1.5, 2.5)

        themes_table = await self.page.query_selector("#update-themes-table")
        if themes_table:
            theme_checkboxes = await self.page.query_selector_all("#update-themes-table tbody input[name='checked[]']")
            theme_count = len(theme_checkboxes)

            if theme_count > 0:
                self.log(f"Found {theme_count} theme(s) needing updates.")
                select_all_themes = self.page.locator("#themes-select-all")
                if await select_all_themes.is_visible():
                    await human_move_and_click(self.page, select_all_themes)
                    await human_delay(1.0, 2.0)

                update_themes_btn = self.page.locator("#upgrade-themes")
                if await update_themes_btn.is_visible():
                    self.log("Clicking 'Update Themes' button...")
                    await human_move_and_click(self.page, update_themes_btn)
                    
                    # Wait for theme updates to finish
                    self.log("Waiting for theme updates to complete...")
                    try:
                        theme_indicator = self.page.locator(
                            "text=/All updates have been completed|Return to WordPress Updates|Return to Themes page/"
                        )
                        await theme_indicator.first.wait_for(timeout=180000)
                        update_summary["themes_updated"] = theme_count
                        self.log(f"Successfully finished updating {theme_count} theme(s)!")
                    except Exception as e:
                        self.log(f"Timeout or notice while updating themes: {e}")
                        update_summary["errors"].append(f"Theme update timeout/notice: {str(e)}")

                    await human_delay(2.0, 3.5)
            else:
                self.log("All themes are already up to date.")
        else:
            self.log("No pending theme updates found.")

        # --- 3. PURGE CACHE (IF PRESENT) ---
        await self.try_purge_cache()

        return update_summary

    async def try_purge_cache(self):
        """Attempts to purge cache if popular caching plugins are detected in the admin bar."""
        try:
            # LiteSpeed Cache
            litespeed = self.page.locator("#wp-admin-bar-litespeed-menu")
            if await litespeed.is_visible():
                self.log("Detected LiteSpeed Cache. Purging cache...")
                await litespeed.hover()
                await human_delay(0.5, 1.0)
                purge_all = self.page.locator("#wp-admin-bar-litespeed-purge-all")
                if await purge_all.is_visible():
                    await purge_all.click()
                    self.log("LiteSpeed Cache purged.")
                    await human_delay(1.0, 2.0)
                    return

            # WP Rocket
            wp_rocket = self.page.locator("#wp-admin-bar-wp-rocket-menu")
            if await wp_rocket.is_visible():
                self.log("Detected WP Rocket. Purging cache...")
                await wp_rocket.hover()
                await human_delay(0.5, 1.0)
                clear_cache = self.page.locator("#wp-admin-bar-purge-all")
                if await clear_cache.is_visible():
                    await clear_cache.click()
                    self.log("WP Rocket Cache cleared.")
                    await human_delay(1.0, 2.0)
                    return

        except Exception as e:
            self.log(f"Cache purge notice (skipped): {e}")

