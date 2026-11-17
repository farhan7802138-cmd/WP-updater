"""
Local Mock WordPress Server for Testing
Runs a lightweight local web server mimicking WordPress frontend,
admin login via token, and update-core.php page.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import threading
import time

PORT = 8765

class MockWordPressHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep console clean
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "":
            # Homepage (Health Check)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>My Test WordPress Site</title>
            <style>
                body { font-family: sans-serif; background: #f0f2f5; padding: 40px; text-align: center; }
                .hero { background: white; max-width: 600px; margin: auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                h1 { color: #1e293b; }
                p { color: #64748b; line-height: 1.6; }
            </style>
            </head>
            <body>
                <div class="hero">
                    <h1>Welcome to Test WordPress Site</h1>
                    <p>Site is running healthy with HTTP 200 OK.</p>
                    <p>Status: All systems operational.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))

        elif path.startswith("/wp-admin") and ("token" in query or "wtlwp_token" in query or path == "/wp-admin/index.php" or path == "/wp-admin/"):
            # Mock WP Admin Dashboard
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Dashboard &lsaquo; Test Site &#8212; WordPress</title>
            <style>
                body { margin: 0; font-family: sans-serif; background: #f0f0f1; }
                #wpadminbar { height: 32px; background: #1d2327; color: #fff; padding: 0 15px; display: flex; align-items: center; }
                #adminmenu { width: 160px; background: #1d2327; color: #fff; position: fixed; top: 32px; bottom: 0; padding-top: 10px; }
                #adminmenu a { color: #fff; display: block; padding: 8px 15px; text-decoration: none; font-size: 13px; }
                #adminmenu a:hover { background: #2271b1; }
                .content { margin-left: 180px; padding: 20px; }
                .notice { background: white; border-left: 4px solid #72aee6; padding: 10px 15px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
                button.notice-dismiss { background: none; border: none; font-size: 16px; cursor: pointer; color: #787c82; }
            </style>
            </head>
            <body>
                <div id="wpadminbar">
                    <span style="font-weight: bold;">Test WordPress Site</span>
                </div>
                <div id="adminmenu">
                    <a href="/wp-admin/">Dashboard</a>
                    <a href="/wp-admin/update-core.php">Updates</a>
                    <a href="/wp-admin/plugins.php">Plugins</a>
                    <a href="/wp-admin/themes.php">Themes</a>
                </div>
                <div class="content">
                    <h1>Dashboard</h1>
                    <div class="notice">
                        <span>Welcome to WordPress! Everything is ready for updates.</span>
                        <button class="notice-dismiss">&times;</button>
                    </div>
                    <p>Temporary Login Successful.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))

        elif path == "/wp-admin/update-core.php":
            # Mock WordPress Update Center
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>WordPress Updates &lsaquo; Test Site &#8212; WordPress</title>
            <style>
                body { margin: 0; font-family: sans-serif; background: #f0f0f1; }
                #wpadminbar { height: 32px; background: #1d2327; color: #fff; padding: 0 15px; display: flex; align-items: center; }
                #adminmenu { width: 160px; background: #1d2327; color: #fff; position: fixed; top: 32px; bottom: 0; }
                .content { margin-left: 180px; padding: 20px; }
                table { width: 100%; border-collapse: collapse; background: white; margin: 15px 0; }
                th, td { padding: 12px; border-bottom: 1px solid #c3c4c7; text-align: left; }
                .button-primary { background: #2271b1; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 13px; }
                .button-primary:hover { background: #135e96; }
            </style>
            <script>
                function updatePlugins() {
                    document.getElementById('plugin-status').innerText = 'Updating selected plugins...';
                    setTimeout(function() {
                        document.getElementById('update-plugins-table').style.display = 'none';
                        document.getElementById('plugin-status').innerHTML = '<h3 style="color:green;">All updates have been completed.</h3><a href="/wp-admin/update-core.php">Return to WordPress Updates</a>';
                    }, 2500);
                }
                function updateThemes() {
                    document.getElementById('theme-status').innerText = 'Updating selected themes...';
                    setTimeout(function() {
                        document.getElementById('update-themes-table').style.display = 'none';
                        document.getElementById('theme-status').innerHTML = '<h3 style="color:green;">All updates have been completed.</h3><a href="/wp-admin/update-core.php">Return to WordPress Updates</a>';
                    }, 2500);
                }
            </script>
            </head>
            <body>
                <div id="wpadminbar">
                    <span style="font-weight: bold;">Test WordPress Site</span>
                </div>
                <div id="adminmenu"></div>
                <div class="content">
                    <h1>WordPress Updates</h1>
                    
                    <h2>Plugins</h2>
                    <div id="plugin-status"></div>
                    <table id="update-plugins-table">
                        <thead>
                            <tr>
                                <th><input type="checkbox" id="plugins-select-all" onclick="toggleAll(this, 'plugin')"> Select All</th>
                                <th>Plugin</th>
                                <th>Installed Version</th>
                                <th>New Version</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><input type="checkbox" name="checked[]" class="plugin-cb"></td>
                                <td><strong>Elementor Website Builder</strong></td>
                                <td>3.19.0</td>
                                <td>3.21.0</td>
                            </tr>
                            <tr>
                                <td><input type="checkbox" name="checked[]" class="plugin-cb"></td>
                                <td><strong>WooCommerce</strong></td>
                                <td>8.5.0</td>
                                <td>8.8.0</td>
                            </tr>
                        </tbody>
                    </table>
                    <button id="upgrade-plugins" class="button-primary" onclick="updatePlugins()">Update Plugins</button>

                    <h2 style="margin-top: 40px;">Themes</h2>
                    <div id="theme-status"></div>
                    <table id="update-themes-table">
                        <thead>
                            <tr>
                                <th><input type="checkbox" id="themes-select-all" onclick="toggleAll(this, 'theme')"> Select All</th>
                                <th>Theme</th>
                                <th>Installed Version</th>
                                <th>New Version</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><input type="checkbox" name="checked[]" class="theme-cb"></td>
                                <td><strong>Astra</strong></td>
                                <td>4.6.0</td>
                                <td>4.7.0</td>
                            </tr>
                        </tbody>
                    </table>
                    <button id="upgrade-themes" class="button-primary" onclick="updateThemes()">Update Themes</button>
                </div>
                <script>
                    function toggleAll(master, type) {
                        var cbs = document.querySelectorAll('.' + type + '-cb');
                        for(var i=0; i<cbs.length; i++) {
                            cbs[i].checked = master.checked;
                        }
                    }
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server = HTTPServer(("127.0.0.1", PORT), MockWordPressHandler)
    print(f"Mock WordPress server started at: http://127.0.0.1:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()

