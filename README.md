# Oblivion V1 - Discord Webhook Ping Farm GUI

## Overview
Oblivion V1 is a user-friendly GUI tool for sending pings to Discord webhooks, supporting Parallel and Sequential modes, advanced settings, and full theme customization. It is designed for non-commercial, educational, and testing purposes only.

## Features
- **Parallel and Sequential Modes:**
  - **Parallel:** Send pings to multiple shards at once (select any combination of groups).
  - **Sequential:** Send pings to one shard at a time, automatically switching to the next when the total pings are reached.
- **Shard Selection and Management:**
  - Add or delete shard groups (webhook groups) directly from the Settings tab.
  - Import webhooks from JSON files, grouped by name (e.g., "MANGO (1-50)").
  - Delete groups with a dropdown selector.
- **Advanced Options:**
  - Rate limiting (customizable backoff time after hitting Discord rate limits).
  - Max retries for failed requests.
  - Message limit per webhook.
  - Total pings per shard (Sequential mode).
- **Theme System:**
  - 10+ built-in themes (OLED Dark, Femboy's Heaven, Hacker X, Pings Aura, Mango Mango Mango, Snowgrave Route, Virtual Grass, Shadow Realm, Visual Studio, Light Mode, Not Spotify, and more).
  - Custom theme editor: set your own colors for background, foreground, accent, entry fields, etc.
  - Themes are JSON-based and easy to expand.
- **Log Area:**
  - Real-time logs of all actions, errors, and status updates.
  - Toggle log visibility with a button.
- **Configurable Settings:**
  - All options are available via the GUI and saved to `config.yaml`.
  - Reset to default or save at any time.
- **Responsive, Modern UI:**
  - Built with Tkinter and ttk for a clean, modern look.
  - Window and taskbar icon support (Windows).
- **Safe Exit:**
  - "Kill" button for immediate shutdown.

## Full List of Program Functions
- **Start/Stop/Kill:** Begin, halt, or immediately terminate the pinging process.
- **Mode Selection:** Choose between Parallel and Sequential modes (recommended for first-time users).
- **Shard Selection:**
  - Parallel: Checkboxes for each group.
  - Sequential: Dropdown to select starting group.
- **Add/Delete Shard Groups:**
  - Add: Enter group name and select a JSON file of webhook URLs.
  - Delete: Select a group from the dropdown and remove it.
- **Ping Farm Settings:**
  - Message, Username, Avatar URL, Delay, Total Pings (essential fields).
- **Advanced Options:**
  - Rate Limit Backoff, Max Retries, Message Limit per Webhook.
- **Theme Selection:**
  - Choose from built-in or custom themes.
  - Custom: Enter hex colors for all UI elements.
- **Log Area:**
  - View, hide, or show logs.
- **Save/Reset Config:**
  - Save current settings or reset to defaults.
- **Import/Export Webhooks:**
  - Import via Add Shard Group (JSON file of URLs).
  - Export by copying from `webhooks.json`.
- **Window Icon:**
  - Uses `icon.ico` for a custom look.

## Kill Button (No Safe Stop)
There is no "Stop" button. The only way to halt the process is the **Kill** button, which immediately terminates the program and all threads. This is a temporary solution: due to the way the code is structured (with threads and network requests), a safe and graceful stop was not feasible at this time. The Kill button is provided as the only reliable way to close the app during operation.

## Configuration
- **config.yaml:** Stores your settings, preferences, and custom theme colors. Example options:
  - `message`, `username`, `avatar_url`, `delay`, `rate_limit_backoff`, `max_retries`, `message_limit`, `total_pings`, `theme`, `custom_theme`, `webhooks_file`
- **webhooks.json:** Stores your webhook groups and URLs. Supports hundreds of webhooks, organized by group (e.g., "MANGO (1-50)", "CHERRY (51-100)", etc.).
- **themes.json:** Stores all built-in theme color definitions. You can add your own themes here.

## Usage
### Control Tab
- **Mode:** Choose between Parallel (multiple shards at once) and Sequential (one at a time, auto-switch). For first-time users, these are the recommended names.
- **Shard Selection:** Check or select which shards to use (Parallel) or pick a starting shard (Sequential).
- **Start/Kill:** Begin or immediately terminate the pinging process. There is no safe stop; the Kill button forcefully closes the program.

### Settings Tab
- **Ping Farm Settings:**
  - Message, Username, Avatar URL, Delay, Total Pings (essential fields)
- **Advanced Options:**
  - Show/hide with a toggle button
  - Max Retries, Rate Limit Backoff, Message Limit per Webhook
- **Save/Reset:** Save your config or reset to defaults
- **Manage Shards:** Add or delete groups directly from the GUI

### Preferences
- **Theme:** Choose a built-in or custom theme
- **Custom Theme:** Enter hex colors for background, foreground, accent, entry fields, etc. These are saved in `config.yaml` under `custom_theme`.

### Log Area
- View real-time logs of all actions
- Toggle visibility with the Hide/Show Logs button

## Themes
- Themes are defined in `themes.json` for easy editing and expansion
- Built-in themes include: OLED Dark, Femboy's Heaven, Hacker X, Pings Aura, Mango Mango Mango, Snowgrave Route, Virtual Grass, Shadow Realm, Visual Studio, Light Mode, Not Spotify, and more
- The 'Default' theme uses the classic white look
- Custom themes can be created via the GUI or by editing the config

## Webhooks
- Webhooks are grouped in `webhooks.json` (e.g., "MANGO (1-50)", "CHERRY (51-100)", etc.)
- Each group contains a list of Discord webhook URLs
- The app can handle hundreds of webhooks efficiently
- Add or delete groups from the Settings tab

## Configuration Options (config.yaml)
- `message`: The message to send (default: '@everyone')
- `username`: The username for the webhook (default: 'Oblivion V1')
- `avatar_url`: The avatar image URL for the webhook
- `delay`: Delay between messages in seconds (default: 2.5)
- `rate_limit_backoff`: Wait time after hitting a rate limit (default: 60)
- `max_retries`: Maximum retry attempts for failed requests (default: 3)
- `message_limit`: Maximum messages per webhook (default: 9000)
- `total_pings`: Total pings per shard in Sequential mode (default: 100)
- `theme`: Name of the selected theme
- `custom_theme`: Custom color settings (if using Custom theme)
- `webhooks_file`: Path to the webhooks JSON file

## FAQ
**Q: Is this tool safe for production or commercial use?**
A: No. It is for educational/testing use only and may violate Discord's TOS if misused.

**Q: How do I add a new theme?**
A: Edit `themes.json` and restart the app, or use the Custom theme option in Preferences.

**Q: How do I import/export webhooks?**
A: Use the Add Shard Group feature in Settings to import. Export by copying from `webhooks.json`.

**Q: Why is there only a Kill button and no Stop button?**
A: Due to the way the program is structured (with threads and network requests), a safe stop was not feasible. The Kill button immediately terminates the program and all threads. This is a temporary solution until a safer method can be implemented.

**Q: What are Parallel and Sequential modes?**
A: Parallel sends pings to multiple shards at once. Sequential sends to one shard at a time and automatically switches to the next when done.

## License & Disclaimer
Oblivion V1 is provided for non-commercial use only. Use at your own risk. The author is not responsible for misuse or any consequences arising from use of this software. See Discord's Terms of Service: https://discord.com/terms 
