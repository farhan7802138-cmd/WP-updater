# WordPress Plugins & Themes Auto-Updater (Python + Playwright)

Automated WordPress Updater jo **Temporary Login URLs** ke zariye login karta hai, plugins aur themes update karta hai, aur homepage ko update se pehle aur baad mein verify karta hai (screenshots + error scan).

## Features
- **Insaan ki tarah kaam karta hai (Human-like)**: Natural mouse movements, delays, smooth scrolling, aur irritating admin banners/notices ko auto-dismiss karna.
- **Temporary Login URL Support**: "Temporary Login Without Password" plugin ke links ko line-by-line paste karein.
- **Pre-Update & Post-Update Health Checks**:
  - Homepage ka HTTP status code check karta hai.
  - PHP fatal errors, database connection errors, critical error screens, aur white screen of death detect karta hai.
  - Before aur After screenshots capture karta hai.
- **Automatic Cache Purge**: LiteSpeed, WP Rocket waghaira detect hotay hi cache purge karta hai.
- **Modern Desktop GUI**: CustomTkinter dark theme interface, Start/Stop buttons, live logs, progress bar, aur HTML report viewer.
- **HTML Visual Report**: Dono screenshots side-by-side aur health status badges.

## Quick Start
1. `launch.bat` par double-click karein.
2. Text area mein har line par apna temporary login link paste karein:
   ```text
   https://site1.com/wp-admin/?wtlwp_token=xyz123...
   https://site2.com/wp-admin/?wtlwp_token=abc456...
   ```
3. **Start Updating** par click karein.
4. Process khatam hone ke baad **View Latest HTML Report** par click karke Before aur After screenshots check karein!

