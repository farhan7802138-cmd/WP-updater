import asyncio
import os
import threading
import webbrowser
from datetime import datetime
import customtkinter as ctk
import config
from core.orchestrator import UpdateOrchestrator

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class WPUpdaterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WordPress Auto-Updater (Human-Like Playwright)")
        self.geometry("980x750")
        self.minsize(850, 600)

        self.orchestrator = None
        self.worker_thread = None
        self.latest_report_path = None

        self._build_ui()

    def _build_ui(self):
        # Grid layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Frame
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="WordPress Plugin & Theme Updater",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_lbl.pack(anchor="w", padx=15, pady=(10, 2))

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Human-like browser automation with pre/post-update visual health check",
            font=ctk.CTkFont(size=13),
            text_color="gray70"
        )
        sub_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        # Main Content Frame (Split: Left input, Right logs)
        content_frame = ctk.CTkFrame(self, corner_radius=10)
        content_frame.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL: INPUT & CONTROLS ---
        left_panel = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_panel.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        left_panel.grid_rowconfigure(1, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        input_title = ctk.CTkLabel(
            left_panel,
            text="Websites & Temporary Login URLs (Line by line):",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        input_title.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.text_input = ctk.CTkTextbox(
            left_panel,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none"
        )
        self.text_input.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # Insert placeholder example
        example_text = (
            "# Enter one site per line.\n"
            "# Format 1 (Direct Temporary Login URL):\n"
            "https://example.com/wp-admin/?wtlwp_token=YOUR_TOKEN_HERE\n\n"
            "# Format 2 (Site URL | Login URL):\n"
            "https://mysite.com | https://mysite.com/wp-login.php?magic_token=xyz\n"
        )
        self.text_input.insert("1.0", example_text)

        # Options Frame
        options_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.headless_var = ctk.BooleanVar(value=False)
        self.headless_switch = ctk.CTkSwitch(
            options_frame,
            text="Headless Mode (Hide Browser)",
            variable=self.headless_var
        )
        self.headless_switch.pack(side="left", padx=5)

        # Buttons Frame
        btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew")

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶ Start Updating",
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.start_process
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹ Stop",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            state="disabled",
            command=self.stop_process
        )
        self.stop_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # --- RIGHT PANEL: LIVE LOGS & STATUS ---
        right_panel = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_panel.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        logs_title = ctk.CTkLabel(
            right_panel,
            text="Live Execution Logs:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        logs_title.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.log_textbox = ctk.CTkTextbox(
            right_panel,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0b1120",
            text_color="#38bdf8",
            wrap="word"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # Bottom Utilities Frame (Open Report / Open Screenshots)
        utils_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        utils_frame.grid(row=2, column=0, sticky="ew")

        self.report_btn = ctk.CTkButton(
            utils_frame,
            text="📄 View Latest HTML Report",
            state="disabled",
            command=self.open_report
        )
        self.report_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.folder_btn = ctk.CTkButton(
            utils_frame,
            text="📁 Screenshots Folder",
            fg_color="#334155",
            hover_color="#475569",
            command=self.open_screenshots_folder
        )
        self.folder_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # Footer Frame (Progress bar & status message)
        footer_frame = ctk.CTkFrame(self, corner_radius=10)
        footer_frame.grid(row=2, column=0, padx=20, pady=(5, 15), sticky="ew")

        self.status_lbl = ctk.CTkLabel(
            footer_frame,
            text="Ready. Add sites and click 'Start Updating'.",
            font=ctk.CTkFont(size=12)
        )
        self.status_lbl.pack(anchor="w", padx=15, pady=(8, 2))

        self.progress_bar = ctk.CTkProgressBar(footer_frame)
        self.progress_bar.pack(fill="x", padx=15, pady=(0, 10))
        self.progress_bar.set(0)

    def log_message(self, message: str):
        def _append():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
            self.log_textbox.see("end")
        self.after(0, _append)

    def update_progress(self, current: int, total: int, text: str):
        def _update():
            fraction = current / total if total > 0 else 0
            self.progress_bar.set(fraction)
            self.status_lbl.configure(text=f"[{current}/{total}] {text}")
        self.after(0, _update)

    def start_process(self):
        raw_text = self.text_input.get("1.0", "end").strip()
        lines = [line.strip() for line in raw_text.splitlines() if line.strip() and not line.startswith("#")]

        if not lines:
            self.log_message("Please add at least one valid site / token URL.")
            return

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.report_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_lbl.configure(text="Initializing Playwright browser...")

        self.log_message(f"Starting updater for {len(lines)} site(s)...")

        headless = self.headless_var.get()
        self.orchestrator = UpdateOrchestrator(
            raw_lines=lines,
            headless=headless,
            log_callback=self.log_message,
            progress_callback=self.update_progress
        )

        def _worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.orchestrator.run())
                self.latest_report_path = result.get("report_path")
                self.after(0, self._on_finish)
            except Exception as e:
                self.log_message(f"Fatal error in execution: {e}")
                self.after(0, self._on_finish)
            finally:
                loop.close()

        self.worker_thread = threading.Thread(target=_worker, daemon=True)
        self.worker_thread.start()

    def stop_process(self):
        if self.orchestrator:
            self.orchestrator.stop()
            self.log_message("Stopping process after current site finishes...")
            self.stop_btn.configure(state="disabled")

    def _on_finish(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_lbl.configure(text="Finished all operations.")
        if self.latest_report_path and os.path.exists(self.latest_report_path):
            self.report_btn.configure(state="normal")
            # Automatically ask or open report
            self.log_message(f"Report ready: {self.latest_report_path}")

    def open_report(self):
        if self.latest_report_path and os.path.exists(self.latest_report_path):
            webbrowser.open(f"file://{os.path.abspath(self.latest_report_path)}")
        else:
            self.log_message("No report generated yet.")

    def open_screenshots_folder(self):
        folder = str(config.SCREENSHOTS_DIR.resolve())
        os.startfile(folder)

