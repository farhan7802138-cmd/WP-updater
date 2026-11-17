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

# Execution Global State
execution_state = {
    "is_running": False,
    "current": 0,
    "total": 0,
    "status_msg": "Ready to launch update pipeline.",
    "active_site": None,
    "logs": [],
    "latest_report": None,
    "stats": {
        "total": 0,
        "healthy": 0,
        "failed": 0,
        "plugins_updated": 0,
        "themes_updated": 0
    },
    "recent_screenshots": []
}

orchestrator_instance = None
mock_server_running = False

def append_log(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    entry = {"time": timestamp, "text": msg}
    execution_state["logs"].append(entry)
    print(f"[{timestamp}] {msg}")

def update_progress(current: int, total: int, msg: str):
    execution_state["current"] = current
    execution_state["total"] = total
    execution_state["status_msg"] = f"[{current}/{total}] {msg}"
    execution_state["stats"]["total"] = total

def on_site_updated(site_result: dict):
    # Update live stats
    pre = site_result.get("pre_check", {})
    post = site_result.get("post_check", {})
    upd = site_result.get("update_summary", {})

    execution_state["stats"]["plugins_updated"] += upd.get("plugins_updated", 0)
    execution_state["stats"]["themes_updated"] += upd.get("themes_updated", 0)

    if post.get("is_healthy"):
        execution_state["stats"]["healthy"] += 1
    elif "is_healthy" in post:
        execution_state["stats"]["failed"] += 1

    # Add screenshots to live gallery
    before_p = pre.get("screenshot_path")
    after_p = post.get("screenshot_path")

    if before_p or after_p:
        item = {
            "url": site_result.get("url"),
            "before": f"/screenshots/{os.path.basename(before_p)}" if before_p else None,
            "after": f"/screenshots/{os.path.basename(after_p)}" if after_p else None,
            "healthy": post.get("is_healthy", False),
            "status_code": post.get("status_code", pre.get("status_code", 200))
        }
        # Replace or append
        existing = [i for i, x in enumerate(execution_state["recent_screenshots"]) if x["url"] == item["url"]]
        if existing:
            execution_state["recent_screenshots"][existing[0]] = item
        else:
            execution_state["recent_screenshots"].insert(0, item)

HTML_PROFESSIONAL_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WP Auto-Updater Enterprise &bull; Playwright</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #090d16;
            --bg-card: #0f172a;
            --bg-card-hover: #131d35;
            --bg-subtle: #1e293b;
            --border-color: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(56, 189, 248, 0.3);
            
            --primary: #38bdf8;
            --primary-gradient: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
            --accent-green: #22c55e;
            --accent-green-glow: rgba(34, 197, 94, 0.25);
            --accent-red: #f43f5e;
            --accent-yellow: #fbbf24;
            --text-title: #f8fafc;
            --text-body: #94a3b8;
            --text-muted: #64748b;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-title);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Top Bar */
        .navbar {
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-color);
            padding: 14px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 50;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .logo-icon {
            width: 40px;
            height: 40px;
            background: var(--primary-gradient);
            border-radius: 10px;
            display: grid;
            place-items: center;
            font-weight: 800;
            font-size: 20px;
            color: #fff;
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
        }
        .brand-text h1 {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.3px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .brand-text span.version {
            font-size: 11px;
            background: rgba(56, 189, 248, 0.15);
            color: var(--primary);
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 600;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }
        .brand-text p {
            font-size: 12px;
            color: var(--text-muted);
        }
        .nav-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
            border-radius: 30px;
            font-size: 12px;
            font-weight: 600;
            color: var(--accent-green);
        }
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-green);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        /* Container Layout */
        .main-content {
            max-width: 1440px;
            width: 100%;
            margin: 0 auto;
            padding: 24px 32px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        /* Metrics Row */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 16px;
        }
        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px 20px;
            transition: all 0.2s ease;
        }
        .metric-card:hover {
            border-color: var(--border-hover);
            transform: translateY(-2px);
        }
        .metric-label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: var(--text-title);
        }
        .metric-value.highlight-blue { color: var(--primary); }
        .metric-value.highlight-green { color: var(--accent-green); }
        .metric-value.highlight-red { color: var(--accent-red); }

        /* Workspace Grid (Two Columns) */
        .workspace-grid {
            display: grid;
            grid-template-columns: 480px 1fr;
            gap: 20px;
            flex-grow: 1;
        }

        /* Common Panel */
        .panel {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);
        }
        .panel-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255, 255, 255, 0.015);
        }
        .panel-header h2 {
            font-size: 14px;
            font-weight: 700;
            letter-spacing: -0.2px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .panel-body {
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            flex-grow: 1;
        }

        /* Editor Area */
        .editor-wrapper {
            position: relative;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
        }
        textarea.code-editor {
            width: 100%;
            height: 220px;
            background: #060911;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 14px;
            color: #e2e8f0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12.5px;
            line-height: 1.6;
            resize: vertical;
            outline: none;
            transition: border 0.2s;
        }
        textarea.code-editor:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
        }

        /* Toolbar Chips */
        .chips-bar {
            display: flex;
            gap: 8px;
            margin-top: 8px;
            align-items: center;
        }
        .chip {
            background: var(--bg-subtle);
            border: 1px solid var(--border-color);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-body);
            cursor: pointer;
            transition: all 0.2s;
        }
        .chip:hover {
            color: #fff;
            border-color: var(--primary);
            background: rgba(56, 189, 248, 0.1);
        }

        /* Config Card */
        .config-box {
            background: #060911;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 14px 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .switch-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
        }
        .switch-row span.label {
            font-weight: 600;
            color: var(--text-title);
        }
        .switch-row span.desc {
            font-size: 11px;
            color: var(--text-muted);
            display: block;
        }

        /* Custom Toggle Switch */
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
        }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: #334155;
            transition: .3s;
            border-radius: 24px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }
        input:checked + .slider { background-color: var(--primary); }
        input:checked + .slider:before { transform: translateX(20px); }

        /* Action Buttons */
        .action-btns {
            display: grid;
            grid-template-columns: 1fr 100px;
            gap: 10px;
        }
        .btn-launch {
            background: var(--primary-gradient);
            color: #fff;
            border: none;
            padding: 13px 20px;
            border-radius: 10px;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
            transition: all 0.2s;
        }
        .btn-launch:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(56, 189, 248, 0.5);
            filter: brightness(1.1);
        }
        .btn-launch:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            box-shadow: none;
        }
        .btn-abort {
            background: rgba(244, 63, 94, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(244, 63, 94, 0.3);
            border-radius: 10px;
            font-weight: 700;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-abort:hover:not(:disabled) {
            background: var(--accent-red);
            color: white;
        }
        .btn-abort:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }

        /* Right Panel: Tabs */
        .tabs-header {
            display: flex;
            gap: 4px;
        }
        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tab-btn.active {
            background: rgba(56, 189, 248, 0.12);
            color: var(--primary);
        }

        /* Live Terminal */
        .terminal-container {
            background: #030712;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            flex-grow: 1;
            height: 400px;
            padding: 16px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            line-height: 1.7;
        }
        .log-entry {
            display: flex;
            gap: 10px;
            margin-bottom: 3px;
        }
        .log-time { color: var(--text-muted); user-select: none; }
        .log-text { color: #e2e8f0; word-break: break-all; }
        .log-text.info { color: #38bdf8; }
        .log-text.success { color: #4ade80; font-weight: 600; }
        .log-text.warning { color: #facc15; }
        .log-text.error { color: #f87171; font-weight: 600; }

        /* Visual Gallery Tab */
        .gallery-container {
            display: none;
            flex-grow: 1;
            overflow-y: auto;
            max-height: 480px;
            gap: 16px;
            flex-direction: column;
        }
        .gallery-item {
            background: #060911;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 14px;
        }
        .gallery-item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            font-size: 13px;
            font-weight: 600;
        }
        .gallery-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .shot-box {
            background: #030712;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            overflow: hidden;
            text-align: center;
        }
        .shot-label {
            font-size: 11px;
            font-weight: 600;
            padding: 6px;
            background: var(--bg-subtle);
            color: var(--text-muted);
        }
        .shot-box img {
            width: 100%;
            height: 160px;
            object-fit: cover;
            object-position: top;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .shot-box img:hover { transform: scale(1.02); }

        /* Progress Footer */
        .footer-progress {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .progress-details {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .spinner {
            width: 18px;
            height: 18px;
            border: 2px solid rgba(56, 189, 248, 0.2);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            display: none;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .footer-status-text {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-title);
        }
        .report-btn {
            background: rgba(56, 189, 248, 0.15);
            color: var(--primary);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            display: none;
            transition: all 0.2s;
        }
        .report-btn:hover {
            background: var(--primary);
            color: #030712;
        }
    </style>
</head>
<body>

    <!-- Navigation Header -->
    <header class="navbar">
        <div class="brand">
            <div class="logo-icon">&#9881;</div>
            <div class="brand-text">
                <h1>WordPress Sentinel Updater <span class="version">v2.5 Pro</span></h1>
                <p>Playwright Autonomous Engine &bull; Human-Like Emulation &bull; Visual Verification</p>
            </div>
        </div>
        <div class="nav-actions">
            <button class="chip" onclick="openReportsFolder()">&#128193; Open Reports Folder</button>
            <button class="chip" onclick="openScreenshotsFolder()">&#128247; Screenshots Folder</button>
            <div class="status-badge">
                <div class="pulse-dot"></div>
                <span id="engineBadge">Engine Ready (Chrome Verified)</span>
            </div>
        </div>
    </header>

    <!-- Main Workspace -->
    <main class="main-content">

        <!-- Top Metrics Row -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Target Queue</div>
                <div class="metric-value highlight-blue" id="kpiTotal">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Healthy &amp; Verified</div>
                <div class="metric-value highlight-green" id="kpiHealthy">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Critical Issues</div>
                <div class="metric-value highlight-red" id="kpiFailed">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Plugins Updated</div>
                <div class="metric-value" id="kpiPlugins">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Themes Updated</div>
                <div class="metric-value" id="kpiThemes">0</div>
            </div>
        </div>

        <!-- Dual Column Workspace -->
        <div class="workspace-grid">

            <!-- Left Column: Input & Controls -->
            <div class="panel">
                <div class="panel-header">
                    <h2>&#128279; Target Websites &amp; Temporary Logins</h2>
                    <span style="font-size: 11px; color: var(--text-muted);">One URL per line</span>
                </div>
                <div class="panel-body">
                    <div class="editor-wrapper">
                        <textarea id="siteInput" class="code-editor" spellcheck="false" placeholder="# Paste your Temporary Login URLs here:&#10;https://example.com/wp-admin/?wtlwp_token=xyz123...&#10;&#10;# Or with explicit site label:&#10;https://mysite.com | https://mysite.com/wp-admin/?wtlwp_token=abc456..."></textarea>
                        <div class="chips-bar">
                            <span class="chip" onclick="loadDemoUrl()">+ Load Demo Test Link</span>
                            <span class="chip" onclick="clearInput()">Clear</span>
                        </div>
                    </div>

                    <!-- Browser & Automation Settings -->
                    <div class="config-box">
                        <div class="switch-row">
                            <div>
                                <span class="label">Interactive Browser Window (Headed)</span>
                                <span class="desc">Open real Google Chrome on screen to watch updates live</span>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" id="interactiveMode" checked>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="switch-row">
                            <div>
                                <span class="label">Natural Human Emulation</span>
                                <span class="desc">Randomized mouse paths, scroll pauses, popup dismissals</span>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" checked disabled>
                                <span class="slider" style="background-color: var(--accent-green);"></span>
                            </label>
                        </div>
                    </div>

                    <!-- Action Controls -->
                    <div class="action-btns">
                        <button id="launchBtn" class="btn-launch" onclick="startUpdate()">
                            &#9654; Run Autonomous Updater
                        </button>
                        <button id="abortBtn" class="btn-abort" onclick="stopUpdate()" disabled>
                            &#9632; Stop
                        </button>
                    </div>
                </div>
            </div>

            <!-- Right Column: Command Center & Live Monitor -->
            <div class="panel">
                <div class="panel-header">
                    <div class="tabs-header">
                        <button id="tabLogs" class="tab-btn active" onclick="switchTab('logs')">&#128187; Live Console</button>
                        <button id="tabVisual" class="tab-btn" onclick="switchTab('visual')">&#128248; Visual Health Monitor</button>
                    </div>
                    <button class="chip" onclick="clearConsole()">Clear Logs</button>
                </div>
                <div class="panel-body" style="padding: 16px;">
                    <!-- Terminal Tab -->
                    <div id="terminal" class="terminal-container">
                        <div class="log-entry">
                            <span class="log-time">[System]</span>
                            <span class="log-text info">WP Auto-Updater Enterprise engine online.</span>
                        </div>
                        <div class="log-entry">
                            <span class="log-time">[System]</span>
                            <span class="log-text">Paste temporary login URLs on the left and click 'Run Autonomous Updater'.</span>
                        </div>
                    </div>

                    <!-- Visual Gallery Tab -->
                    <div id="gallery" class="gallery-container">
                        <div style="text-align: center; padding: 40px 0; color: var(--text-muted); font-size: 13px;" id="noScreenshotsNotice">
                            No screenshots captured yet. Run an update to view Before &amp; After health comparisons.
                        </div>
                    </div>
                </div>
            </div>

        </div>

        <!-- Footer Status & Report Link -->
        <div class="footer-progress">
            <div class="progress-details">
                <div class="spinner" id="loadingSpinner"></div>
                <div class="footer-status-text" id="footerStatus">Ready. Add temporary login URLs to begin.</div>
            </div>
            <div>
                <a id="viewReportBtn" class="report-btn" href="#" target="_blank">&#128196; View Full HTML Report</a>
            </div>
        </div>

    </main>

    <script>
        let isPolling = false;

        function loadDemoUrl() {
            document.getElementById('siteInput').value = "http://127.0.0.1:8765/wp-admin/?wtlwp_token=demo_test_token_123";
            appendLocalLog("Loaded local demo WordPress test link. Click 'Run Autonomous Updater' to test without touching live sites!");
        }

        function clearInput() {
            document.getElementById('siteInput').value = "";
        }

        function clearConsole() {
            document.getElementById('terminal').innerHTML = '<div class="log-entry"><span class="log-time">[System]</span><span class="log-text">Console cleared.</span></div>';
        }

        function switchTab(tab) {
            const tabLogs = document.getElementById('tabLogs');
            const tabVisual = document.getElementById('tabVisual');
            const term = document.getElementById('terminal');
            const gallery = document.getElementById('gallery');

            if (tab === 'logs') {
                tabLogs.classList.add('active');
                tabVisual.classList.remove('active');
                term.style.display = 'block';
                gallery.style.display = 'none';
            } else {
                tabLogs.classList.remove('active');
                tabVisual.classList.add('active');
                term.style.display = 'none';
                gallery.style.display = 'flex';
            }
        }

        function appendLocalLog(msg) {
            const term = document.getElementById('terminal');
            const time = new Date().toTimeString().split(' ')[0];
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerHTML = `<span class="log-time">[${time}]</span><span class="log-text info">${msg}</span>`;
            term.appendChild(div);
            term.scrollTop = term.scrollHeight;
        }

        async function startUpdate() {
            const rawText = document.getElementById('siteInput').value.trim();
            if (!rawText) {
                alert("Please paste at least one Temporary Login URL in the target list.");
                return;
            }

            const lines = rawText.split('\\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'));
            const interactive = document.getElementById('interactiveMode').checked;
            const headless = !interactive; // Checked means interactive (headless = false)

            document.getElementById('launchBtn').disabled = true;
            document.getElementById('abortBtn').disabled = false;
            document.getElementById('loadingSpinner').style.display = 'block';
            document.getElementById('viewReportBtn').style.display = 'none';

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
                    resetUIState();
                }
            } catch (err) {
                alert("Error starting pipeline: " + err);
                resetUIState();
            }
        }

        async function stopUpdate() {
            await fetch('/api/stop', { method: 'POST' });
            document.getElementById('abortBtn').disabled = true;
        }

        function resetUIState() {
            document.getElementById('launchBtn').disabled = false;
            document.getElementById('abortBtn').disabled = true;
            document.getElementById('loadingSpinner').style.display = 'none';
        }

        function startPolling() {
            isPolling = true;
            const timer = setInterval(async () => {
                try {
                    const res = await fetch('/api/status');
                    const data = await res.json();

                    // Update Status text
                    document.getElementById('footerStatus').innerText = data.status_msg;

                    // Update Metrics
                    document.getElementById('kpiTotal').innerText = data.stats.total;
                    document.getElementById('kpiHealthy').innerText = data.stats.healthy;
                    document.getElementById('kpiFailed').innerText = data.stats.failed;
                    document.getElementById('kpiPlugins').innerText = data.stats.plugins_updated;
                    document.getElementById('kpiThemes').innerText = data.stats.themes_updated;

                    // Render Logs with coloring
                    renderLogs(data.logs);

                    // Render Screenshots
                    renderGallery(data.recent_screenshots);

                    // Report button
                    if (data.latest_report) {
                        const rBtn = document.getElementById('viewReportBtn');
                        rBtn.href = data.latest_report;
                        rBtn.style.display = 'inline-block';
                    }

                    if (!data.is_running) {
                        resetUIState();
                        clearInterval(timer);
                        isPolling = false;
                    }
                } catch (e) {
                    console.error("Polling error", e);
                }
            }, 1000);
        }

        function renderLogs(logs) {
            const term = document.getElementById('terminal');
            term.innerHTML = '';
            logs.forEach(log => {
                const div = document.createElement('div');
                div.className = 'log-entry';

                let textClass = '';
                const lower = log.text.toLowerCase();
                if (lower.includes('success') || lower.includes('healthy') || lower.includes('verified')) {
                    textClass = 'success';
                } else if (lower.includes('alert') || lower.includes('error') || lower.includes('critical') || lower.includes('fatal')) {
                    textClass = 'error';
                } else if (lower.includes('warning') || lower.includes('notice')) {
                    textClass = 'warning';
                } else if (lower.includes('step') || lower.includes('processing')) {
                    textClass = 'info';
                }

                div.innerHTML = `<span class="log-time">[${log.time}]</span><span class="log-text ${textClass}">${log.text}</span>`;
                term.appendChild(div);
            });
            term.scrollTop = term.scrollHeight;
        }

        function renderGallery(shots) {
            const gallery = document.getElementById('gallery');
            if (!shots || shots.length === 0) return;

            document.getElementById('noScreenshotsNotice')?.remove();
            gallery.innerHTML = '';

            shots.forEach(item => {
                const card = document.createElement('div');
                card.className = 'gallery-item';
                card.innerHTML = `
                    <div class="gallery-item-header">
                        <span>${item.url}</span>
                        <span style="color: ${item.healthy ? 'var(--accent-green)' : 'var(--accent-red)'}">
                            ${item.healthy ? '&#9679; Healthy (HTTP ' + item.status_code + ')' : '&#9888; Critical Alert'}
                        </span>
                    </div>
                    <div class="gallery-grid">
                        <div class="shot-box">
                            <div class="shot-label">Before Update</div>
                            ${item.before ? `<img src="${item.before}" onclick="window.open(this.src)" alt="Before">` : '<p style="padding:40px;color:gray;">No image</p>'}
                        </div>
                        <div class="shot-box">
                            <div class="shot-label">After Update</div>
                            ${item.after ? `<img src="${item.after}" onclick="window.open(this.src)" alt="After">` : '<p style="padding:40px;color:gray;">No image</p>'}
                        </div>
                    </div>
                `;
                gallery.appendChild(card);
            });
        }

        function openReportsFolder() {
            fetch('/api/open-folder?type=reports');
        }

        function openScreenshotsFolder() {
            fetch('/api/open-folder?type=screenshots');
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PROFESSIONAL_DASHBOARD)

@app.route("/api/start", methods=["POST"])
def api_start():
    global orchestrator_instance
    if execution_state["is_running"]:
        return jsonify({"status": "error", "message": "Pipeline already actively running."}), 400

    payload = request.get_json() or {}
    lines = payload.get("lines", [])
    headless = payload.get("headless", False)

    if not lines:
        return jsonify({"status": "error", "message": "No target URLs provided."}), 400

    # Auto-start mock server if local test URL is present
    for line in lines:
        if "127.0.0.1:8765" in line:
            start_local_mock_server_if_needed()

    execution_state["is_running"] = True
    execution_state["logs"] = []
    execution_state["latest_report"] = None
    execution_state["current"] = 0
    execution_state["total"] = len(lines)
    execution_state["stats"] = {
        "total": len(lines),
        "healthy": 0,
        "failed": 0,
        "plugins_updated": 0,
        "themes_updated": 0
    }
    execution_state["recent_screenshots"] = []
    execution_state["status_msg"] = f"Initializing update pipeline for {len(lines)} site(s)..."

    orchestrator_instance = UpdateOrchestrator(
        raw_lines=lines,
        headless=headless,
        log_callback=append_log,
        progress_callback=update_progress,
        site_update_callback=on_site_updated
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
            execution_state["status_msg"] = "Pipeline completed successfully."
        except Exception as e:
            append_log(f"Fatal error in pipeline: {e}")
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
        append_log("Cancellation requested. Stopping after current task finishes...")
    return jsonify({"status": "stopping"})

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(execution_state)

@app.route("/api/open-folder", methods=["GET"])
def api_open_folder():
    folder_type = request.args.get("type", "reports")
    target = config.REPORTS_DIR if folder_type == "reports" else config.SCREENSHOTS_DIR
    try:
        os.startfile(str(target.resolve()))
    except Exception as e:
        pass
    return jsonify({"status": "ok"})

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
        append_log("Auto-started mock WordPress server at http://127.0.0.1:8765")

def launch_server():
    port = 5050
    def _open():
        time.sleep(1.2)
        webbrowser.open(f"http://127.0.0.1:{port}")
    threading.Thread(target=_open, daemon=True).start()

    print(f"Starting Professional Web Dashboard at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    launch_server()
