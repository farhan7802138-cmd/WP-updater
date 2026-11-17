import sys
import argparse
import asyncio
from ui.app_window import WPUpdaterApp
from core.orchestrator import UpdateOrchestrator

def run_gui():
    app = WPUpdaterApp()
    app.mainloop()

def run_cli(file_path: str, headless: bool = True):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    orchestrator = UpdateOrchestrator(
        raw_lines=lines,
        headless=headless,
        log_callback=print,
        progress_callback=lambda cur, tot, msg: print(f"[{cur}/{tot}] {msg}")
    )
    asyncio.run(orchestrator.run())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WordPress Plugin & Theme Updater with Playwright")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode instead of GUI")
    parser.add_argument("--file", type=str, help="Path to text file containing sites/tokens (for CLI mode)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")

    args = parser.parse_args()

    if args.cli and args.file:
        run_cli(args.file, headless=args.headless)
    else:
        run_gui()

