import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Human Behavior Timing (seconds)
MIN_ACTION_DELAY = 1.2
MAX_ACTION_DELAY = 3.2
PAGE_TIMEOUT_MS = 60000

# Browser Settings
DEFAULT_VIEWPORT = {"width": 1366, "height": 768}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Critical Error Indicators in HTML
FATAL_ERROR_PATTERNS = [
    "there has been a critical error on this website",
    "fatal error:",
    "parse error:",
    "error establishing a database connection",
    "internal server error",
    "briefly unavailable for scheduled maintenance",
    "cannot redeclare",
    "uncaught error",
    "call to undefined function",
]

