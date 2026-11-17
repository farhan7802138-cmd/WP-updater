import os
from datetime import datetime
from pathlib import Path
import config

class Reporter:
    @staticmethod
    def generate_html_report(results: list) -> str:
        """
        Generates a rich, interactive HTML report with side-by-side Before/After screenshot comparison.
        """
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = config.REPORTS_DIR / f"wp_update_report_{file_timestamp}.html"

        total_sites = len(results)
        healthy_sites = sum(1 for r in results if r.get("post_check", {}).get("is_healthy", False))
        failed_sites = total_sites - healthy_sites
        total_plugins = sum(r.get("update_summary", {}).get("plugins_updated", 0) for r in results)
        total_themes = sum(r.get("update_summary", {}).get("themes_updated", 0) for r in results)

        cards_html = ""
        for idx, res in enumerate(results, 1):
            url = res.get("url", "N/A")
            pre = res.get("pre_check", {})
            post = res.get("post_check", {})
            upd = res.get("update_summary", {})
            is_healthy = post.get("is_healthy", False)

            status_badge = (
                '<span class="badge badge-success">Healthy (Working)</span>'
                if is_healthy else
                '<span class="badge badge-danger">Critical / Broken</span>'
            )

            before_img = Path(pre.get("screenshot_path", "")).as_uri() if pre.get("screenshot_path") else ""
            after_img = Path(post.get("screenshot_path", "")).as_uri() if post.get("screenshot_path") else ""

            errors_list = post.get("detected_errors", [])
            errors_html = ""
            if errors_list:
                errors_html = f"""
                <div class="errors-box">
                    <strong>Issues Detected:</strong>
                    <ul>{''.join(f'<li>{e}</li>' for e in errors_list)}</ul>
                </div>
                """

            cards_html += f"""
            <div class="site-card {'card-failed' if not is_healthy else ''}">
                <div class="site-header">
                    <span class="site-number">#{idx}</span>
                    <span class="site-url">{url}</span>
                    {status_badge}
                </div>
                <div class="site-details">
                    <p><strong>Plugins Updated:</strong> {upd.get('plugins_updated', 0)} | <strong>Themes Updated:</strong> {upd.get('themes_updated', 0)}</p>
                    <p><strong>Status Codes:</strong> Pre-update: {pre.get('status_code', 'N/A')} &rarr; Post-update: {post.get('status_code', 'N/A')}</p>
                    {errors_html}
                </div>
                <div class="comparison-grid">
                    <div class="screenshot-box">
                        <div class="img-label">Homepage Before Update</div>
                        {f'<img src="{before_img}" alt="Before Update" onclick="window.open(this.src)" />' if before_img else '<p class="no-img">No screenshot</p>'}
                    </div>
                    <div class="screenshot-box">
                        <div class="img-label">Homepage After Update</div>
                        {f'<img src="{after_img}" alt="After Update" onclick="window.open(this.src)" />' if after_img else '<p class="no-img">No screenshot</p>'}
                    </div>
                </div>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WordPress Updates Verification Report</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --border: #334155;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --accent: #38bdf8;
            --success: #22c55e;
            --danger: #ef4444;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 30px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            font-size: 28px;
            margin-bottom: 8px;
            color: var(--accent);
        }}
        .meta {{
            color: var(--text-dim);
            margin-bottom: 24px;
            font-size: 14px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 16px 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-card .num {{
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 4px;
            color: var(--accent);
        }}
        .stat-card.success .num {{ color: var(--success); }}
        .stat-card.danger .num {{ color: var(--danger); }}
        .stat-card .label {{
            font-size: 13px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .site-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }}
        .card-failed {{
            border-color: var(--danger);
        }}
        .site-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
            margin-bottom: 14px;
        }}
        .site-number {{
            font-weight: bold;
            color: var(--accent);
            margin-right: 10px;
        }}
        .site-url {{
            font-size: 18px;
            font-weight: 600;
            flex-grow: 1;
            word-break: break-all;
        }}
        .badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-success {{ background: rgba(34, 197, 94, 0.2); color: var(--success); border: 1px solid var(--success); }}
        .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }}
        .site-details {{
            font-size: 14px;
            color: var(--text-dim);
            margin-bottom: 16px;
        }}
        .site-details p {{ margin: 4px 0; }}
        .errors-box {{
            margin-top: 10px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid var(--danger);
            padding: 10px 14px;
            border-radius: 6px;
            color: #fca5a5;
        }}
        .errors-box ul {{ margin: 4px 0 0 20px; padding: 0; }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 14px;
        }}
        .screenshot-box {{
            background: #090d16;
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            text-align: center;
        }}
        .img-label {{
            padding: 8px;
            font-size: 12px;
            font-weight: bold;
            background: #1e293b;
            color: var(--text-dim);
            border-bottom: 1px solid var(--border);
        }}
        .screenshot-box img {{
            width: 100%;
            height: 280px;
            object-fit: cover;
            object-position: top;
            cursor: pointer;
            transition: opacity 0.2s;
        }}
        .screenshot-box img:hover {{
            opacity: 0.9;
        }}
        .no-img {{
            padding: 60px 0;
            color: var(--text-dim);
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>WordPress Updates & Health Report</h1>
        <div class="meta">Generated on: {timestamp_str} | Powered by Playwright Automation</div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="num">{total_sites}</div>
                <div class="label">Total Sites</div>
            </div>
            <div class="stat-card success">
                <div class="num">{healthy_sites}</div>
                <div class="label">Healthy Sites</div>
            </div>
            <div class="stat-card {'danger' if failed_sites > 0 else ''}">
                <div class="num">{failed_sites}</div>
                <div class="label">Broken / Alerts</div>
            </div>
            <div class="stat-card">
                <div class="num">{total_plugins}</div>
                <div class="label">Plugins Updated</div>
            </div>
            <div class="stat-card">
                <div class="num">{total_themes}</div>
                <div class="label">Themes Updated</div>
            </div>
        </div>

        {cards_html}
    </div>
</body>
</html>
"""
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(report_filename)

