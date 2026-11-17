import os
import sys
import json
import time
import asyncio
import threading
import webbrowser
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, send_from_directory

import config
from core.orchestrator import UpdateOrchestrator
import test_local_server

app = Flask(__name__)

# Global state
execution_state = {
    "is_running": False,
    "current": 0,
    "total": 0,
    "status_msg": "Ready to update.",
    "logs": [],
    "latest_report": None,
    "results": []
}

orchestrator_instance = None
mock_server_running = False

def append_log(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    execution_state["logs"].append(entry)
    print(entry)

def update_progress(current: int, total: int, msg: str):
    execution_state["current"] = current
    execution_state["total"] = total
    execution_state["status_msg"] = f"[{current}/{total}] {msg}"

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WordPress Auto-Updater Dashboard</title>
    <style>
        :root {
            --bg-dark: #0f172a;
            --panel-bg: #1e293b;
            --border: #334155;
            --primary: #38bdf8;
            --primary-hover: #0284c7;
            --success: #22c55e;
            --danger: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            padding: 24px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            background: var(--panel-bg);
            border: 1px solid var(--border);
            padding: 20px 24px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { font-size: 24px; color: var(--primary); font-weight: 700; }
        .tagline { color: var(--text-muted); font-size: 14px; margin-top: 4px; }
        .badge-live {
            background: rgba(34, 197, 94, 0.15);
            color: var(--success);
            padding: 6px 14px;
            border-radius: 20px;
            border: 1px solid var(--success);
            font-weight: 600;
            font-size: 13px;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .panel {
            background: var(--panel-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
        }
        .panel h2 {
            font-size: 16px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        textarea {
            width: 100%;
            height: 240px;
            background: #090d16;
            color: #e2e8f0;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            font-family: "Consolas", monospace;
            font-size: 13px;
            resize: vertical;
            outline: none;
        }
        textarea:focus { border-color: var(--primary); }
        .terminal {
            width: 100%;
            height: 240px;
            background: #000;
            color: #38bdf8;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            font-family: "Consolas", monospace;
            font-size: 12px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .controls {
            margin-top: 14px;
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }
        button {
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .btn-start {
            background: var(--success);
            color: white;
        }
        .btn-start:hover { filter: brightness(1.1); }
        .btn-start:disabled { background: #475569; cursor: not-allowed; }
        .btn-stop {
            background: var(--danger);
            color: white;
        }
        .btn-stop:disabled { background: #475569; cursor: not-allowed; }
        .btn-secondary {
            background: #334155;
            color: #f8fafc;
        }
        .btn-secondary:hover { background: #475569; }
        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--text-muted);
            cursor: pointer;
        }
        .status-bar {
            background: var(--panel-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .progress-text { font-size: 14px; font-weight: 600; color: var(--primary); }
        .report-link {
            color: var(--primary);
            text-decoration: underline;
            font-weight: 600;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>WordPress Plugins & Themes Auto-Updater</h1>
                <div class="tagline">Playwright Human-Like Automation &amp; Visual Verification Engine</div>
            </div>
            <div class="badge-live">&#9679; Browser Ready</div>
        </header>

        <div class="grid">
            <!-- Left Panel: Input -->
            <div class="panel">
                <h2>
                    <span>Websites &amp; Temporary Login URLs</span>
                    <button class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="loadDemoUrl()">Load Local Demo URL</button>
                </h2>
                <textarea id="siteInput" placeholder="Enter one Temporary Login URL per line:&#10;https://example.com/wp-admin/?wtlwp_token=xyz123...&#10;https://mysite.com | https://mysite.com/wp-admin/?wtlwp_token=abc456..."></textarea>
                <div class="controls">
                    <button id="startBtn" class="btn-start" onclick="startUpdate()">&#9654; Start Updating</button>
                    <button id="stopBtn" class="btn-stop" onclick="stopUpdate()" disabled>&#9632; Stop</button>
                    <label class="checkbox-label">
                        <input type="checkbox" id="headlessMode">
                        Headless Mode (Hide Browser Window)
                    </label>
                </div>
            </div>

            <!-- Right Panel: Live Terminal -->
            <div class="panel">
                <h2>
                    <span>Live Execution Logs</span>
                    <button class="btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="clearLogs()">Clear</button>
                </h2>
                <div id="terminal" class="terminal">[Ready] Add temporary login URLs and click 'Start Updating'...</div>
            </div>
        </div>

        <div class="status-bar">
            <div>
                <span style="color: var(--text-muted); margin-right: 8px;">Status:</span>
                <span id="statusMsg" class="progress-text">Ready.</span>
            </div>
            <div>
                <a id="reportLink" class="report-link" href="#" target="_blank">&#128196; View HTML Verification Report</a>
            </div>
        </div>
    </div>

    <script>
        let isPolling = false;

        function loadDemoUrl() {
            document.getElementById('siteInput').value = "http://127.0.0.1:8765/wp-admin/?wtlwp_token=demo_test_token_123";
            appendLocalLog("Loaded local demo test URL. Click 'Start Updating' to test safely!");
        }

        function appendLocalLog(msg) {
            const term = document.getElementById('terminal');
            const time = new Date().toTimeString().split(' ')[0];
            term.innerText += `\\n[${time}] ${msg}`;
            term.scrollTop = term.scrollHeight;
        }

        function clearLogs() {
            document.getElementById('terminal').innerText = "[Terminal cleared]";
        }

        async function startUpdate() {
            const rawText = document.getElementById('siteInput').value.trim();
            if (!rawText) {
                alert("Please paste at least one Temporary Login URL.");
                return;
            }

            const lines = rawText.split('\\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'));
            const headless = document.getElementById('headlessMode').checked;

            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('reportLink').style.display = 'none';

            try {
                const res = await fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ lines: lines, headless: headless })
                });
                const data = await res.json();
                if (data.status === 'started') {
                    if (!isPolling) startPolling();
                } else {
                    alert(data.message);
                    document.getElementById('startBtn').disabled = false;
                    document.getElementById('stopBtn').disabled = true;
                }
            } catch (err) {
                alert("Error starting update: " + err);
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
            }
        }

        async function stopUpdate() {
            await fetch('/api/stop', { method: 'POST' });
            document.getElementById('stopBtn').disabled = true;
        }

        function startPolling() {
            isPolling = true;
            const timer = setInterval(async () => {
                try {
                    const res = await fetch('/api/status');
                    const data = await res.json();

                    document.getElementById('statusMsg').innerText = data.status_msg;
                    document.getElementById('terminal').innerText = data.logs.join('\\n');
                    document.getElementById('terminal').scrollTop = document.getElementById('terminal').scrollHeight;

                    if (data.latest_report) {
                        const rLink = document.getElementById('reportLink');
                        rLink.href = data.latest_report;
                        rLink.style.display = 'inline-block';
                    }

                    if (!data.is_running) {
                        document.getElementById('startBtn').disabled = false;
                        document.getElementById('stopBtn').disabled = true;
                        clearInterval(timer);
                        isPolling = false;
                    }
                } catch (e) {
                    console.error("Polling error", e);
                }
            }, 1000);
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_DASHBOARD)

@app.route("/api/start", methods=["POST"])
def api_start():
    global orchestrator_instance
    if execution_state["is_running"]:
        return jsonify({"status": "error", "message": "Updater is already running."}), 400

    payload = request.get_json() or {}
    lines = payload.get("lines", [])
    headless = payload.get("headless", False)

    if not lines:
        return jsonify({"status": "error", "message": "No URLs provided."}), 400

    # Check if local demo URL is included, ensure mock server is running
    for line in lines:
        if "127.0.0.1:8765" in line:
            start_local_mock_server_if_needed()

    execution_state["is_running"] = True
    execution_state["logs"] = []
    execution_state["latest_report"] = None
    execution_state["current"] = 0
    execution_state["total"] = len(lines)
    execution_state["status_msg"] = f"Starting updates for {len(lines)} site(s)..."

    orchestrator_instance = UpdateOrchestrator(
        raw_lines=lines,
        headless=headless,
        log_callback=append_log,
        progress_callback=update_progress
    )

    def _worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(orchestrator_instance.run())
            report_p = res.get("report_path")
            if report_p:
                filename = os.path.basename(report_p)
                execution_state["latest_report"] = f"/reports/{filename}"
            execution_state["results"] = res.get("results", [])
            execution_state["status_msg"] = "Finished all operations."
        except Exception as e:
            append_log(f"Fatal error: {e}")
            execution_state["status_msg"] = f"Error: {e}"
        finally:
            execution_state["is_running"] = False
            loop.close()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    return jsonify({"status": "started"})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    global orchestrator_instance
    if orchestrator_instance:
        orchestrator_instance.stop()
        append_log("Stop signal sent. Stopping after current task...")
    return jsonify({"status": "stopping"})

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(execution_state)

@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(str(config.REPORTS_DIR.resolve()), filename)

@app.route("/screenshots/<path:filename>")
def serve_screenshot(filename):
    return send_from_directory(str(config.SCREENSHOTS_DIR.resolve()), filename)

def start_local_mock_server_if_needed():
    global mock_server_running
    if not mock_server_running:
        t = threading.Thread(target=test_local_server.run_server, daemon=True)
        t.start()
        mock_server_running = True
        append_log("Auto-started background mock WordPress test server on http://127.0.0.1:8765")

def launch_server():
    port = 5050
    # Auto-open browser in 1.2 seconds
    def _open():
        time.sleep(1.2)
        webbrowser.open(f"http://127.0.0.1:{port}")
    threading.Thread(target=_open, daemon=True).start()

    print(f"Starting Web Dashboard at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    launch_server()

