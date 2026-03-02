<p align="center">
  <img src="docs/logo.png" width="180" alt="DashCord Logo">
</p>

<h1 align="center">DashCord</h1>

<p align="center">
  <strong>The headless Discord-to-automation bridge.</strong><br>
  Turn Discord into a persistent UI for your home lab, n8n, and Make pipelines.
</p>

<p align="center">
  <img src="https://img.shields.io/github/v/release/nextgearslab/DashCord?color=blue&style=flat-square" alt="Latest Release">
  <img src="https://img.shields.io/github/license/nextgearslab/DashCord?color=orange&style=flat-square" alt="License">
  <img src="https://img.shields.io/github/stars/nextgearslab/DashCord?style=flat-square" alt="Stars">
</p>

---

DashCord is a highly flexible, configuration-driven Discord bot that translates chat commands, file uploads, and interactive UI panels (buttons) into HTTP webhook requests. 

Originally built for **n8n**, this bot works flawlessly with **Make (Integromat), Zapier, Node-RED**, or any custom API. 

Instead of hardcoding new Discord commands every time you want to automate something, you simply define them in a `routes.json` file. The bot acts as a universal headless bridge between Discord and your automation platform.

| 🎛️ Interactive UI Panels | 📁 Advanced File Handling (TTS) |
| :--- | :--- |
| ![Weather Panel](docs/display1.png) | ![TTS File Upload](docs/display4.png) |
| **📊 System Automation Logs** | **🏃 Manual Chat Commands** |
| ![Sync Manager Log](docs/display3.png) | ![Fitbit Command](docs/display2.png) |

## ❓ Why use DashCord?

While platforms like n8n and Node-RED have native Discord nodes, they are often difficult to use for advanced UI management. DashCord acts as a specialized middleware that solves three specific pain points:
1. **Persistent UI:** Keeping button panels at the bottom of a busy chat (Sticky UI) is handled by the bot, not your workflow.
2. **Binary Pipelines:** Automatically converts multi-file uploads into Base64 and "fans them out" so your workflow only has to process one file at a time.
3. **Clean Workflows:** Keeps your automation canvas focused on logic rather than managing Discord API states and message IDs.
   
## ✨ Features

- **⚡ Dynamic Commands:** Add new slash-free commands (e.g., `!weather`, `!deploy`) just by editing a JSON file.
- **🎛️ Sticky Dashboard Panels:** Generate persistent UI button panels in specific channels. The bot can automatically "persist" these panels, moving them to the bottom of the chat so they never get buried. Users can click buttons to trigger workflows without typing.
- **📁 Intelligent File Fan-out:** Forward files directly to your webhooks. Can auto-parse JSON attachments, convert to Base64, and dynamically fan-out requests (upload 5 files, it triggers 5 separate webhook calls).
- **🎭 Dynamic Body Templating:** Inject Discord metadata (like `{{discord.user_display}}` or `{{discord.channel_id}}`) directly into the JSON payload sent to your webhook, molding the data to fit your API perfectly.
- **🔒 Security Built-In:** Restrict specific commands to specific Discord channels or user IDs. Secures outbound requests with a custom `X-DashCord-Token` header.
- **💬 Native Discord Replies:** Your webhook can respond with JSON containing plain text or rich Discord Embeds, and the bot will cleanly post it back to the channel.

---

## 🚀 Quick Start (Docker)

1. Clone the repository:
```bash
git clone https://github.com/nextgearslab/DashCord.git
cd DashCord
```

2. Setup Configuration:
```bash
cp .env.example .env
cp routes.json.example routes.json
```

3. Open `.env` and add your **Discord Bot Token**.

4. Configure your commands and endpoints in `routes.json`.

5. Run it (using the Docker Compose wrapper):
```bash
chmod +x start.sh
./start.sh
```
*(To view live logs, simply run `./logs.sh`)*

> **⚠️ CRITICAL SETUP STEP:** 
> Because this bot reads chat commands (`!weather`), you **must** enable the **Message Content Intent**.
> Go to the [Discord Developer Portal](https://discord.com/developers/applications) -> Your Bot -> **Bot** tab -> Scroll down to **Privileged Gateway Intents** -> Turn ON **Message Content Intent**.

---

## ⚙️ Configuration File (`routes.json`)

All routing logic is driven by `routes.json`. It has two main sections: `commands` and `panels`.

### 1. Defining a Command

Commands map a typed Discord message to a webhook URL.

```json
"commands": {
  "ping": {
    "endpoint": "https://your-automation-tool.com/webhook/ping",
    "method": "POST",
    "allowed_users": ["1234567890"],
    "allowed_channels":[]
  }
}
```
*Typing `!ping test` will send a POST request containing the arguments to that webhook. Because `allowed_users` has an ID, only that Discord user can trigger it.*

> **💡 Note on Case Sensitivity**
> Commands are **case-insensitive for the end user** (they can type `!PING` or `!Ping`). However, you must define the command keys in `routes.json` in **all lowercase** (e.g., `"ping"`, not `"Ping"`).
>
> **❓ Smart Help**
> If a user types a command that doesn't exist, DashCord will automatically reply with a list of commands that the user **actually has permission to use** in that specific channel.

*   **Supported Methods:** Both `"POST"` and `"GET"` are supported.
*   **GET Requests:** If you choose `GET`, the entire JSON payload is stringified and passed as a URL query parameter (e.g., `?payload={"source":"discord", ...}`).

### 2. Defining File Uploads

You can allow commands to accept attachments, or even fire automatically when a specific filetype is uploaded without a command at all.

```json
"upload": {
  "endpoint": "https://your-webhook...",
  "method": "POST",
  "accept_attachments": true,
  "allow_without_command": true,
  "attachment_rules": {
    "extensions":[".json", ".csv"],
    "max_bytes": 2500000,
    "require_json": false
  }
}
```
> **💡 The "Fan-out" Rule**
> DashCord handles multiple file uploads intelligently. If a user uploads **5 files at once**, the bot will "fan-out" and trigger **5 separate webhook calls** (one for each file). This makes it much easier to build your n8n/Make workflows, as you only ever have to handle **one file at a time** in your automation logic!

> **🎭 Attachment Feedback**
> You can control how the bot replies to uploads using the `attachment_reply` block.
> *   `mode`: Set to `"errors"` (default) to only reply if something goes wrong, `"always"` to always confirm, or `"none"` for silence.
> *   `success_template` / `error_template`: Use `{ok}`, `{bad}`, and `{total}` as variables to customize the message.

### 3. Designing Interactive UI Panels

Panels create persistent messages with buttons. You can bind specific commands and background arguments to each button.

```json
"panels": {
  "Server_Controls": {
    "channels":["1029384756"],
    "buttons":[
      {
        "label": "Restart Server",
        "command": "ping",
        "args": ["restart"],
        "style": "danger"
      },
      {
        "label": "Check Status",
        "command": "ping",
        "args": ["status"],
        "style": "primary"
      }
    ]
  }
}
```
**Button Styles Available:**
| Style Name | Discord Color | Best Used For |
| :--- | :--- | :--- |
| `primary` | Blurple (Blue) | Main actions |
| `secondary`| Grey | Neutral / Informational |
| `success` | Green | Confirmations / Starts |
| `danger` | Red | Restarts / Stops / Deletes |

*Note: Clicking the "Restart Server" button above executes the `ping` command with the argument `restart` behind the scenes, exactly as if the user typed `!ping restart`.*

**Customizing Persistence per Panel:**
If you want one panel to "jump" to the bottom every 60 seconds but another to stay put, add a `persist` block directly to the panel:
```json
"Server_Controls": {
  "channels": ["123456789"],
  "persist": {
    "enabled": true,
    "interval_seconds": 60,
    "cleanup_old_active": true
  },
  "buttons": [...]
}
```

### 4. Dynamic Body Templating (Optional)

By default, DashCord sends a standardized payload to your webhook. However, if your API requires a very specific JSON structure (or if you want to drop the bot straight into an existing integration without changing the API), you can define a `body_template`.

The `body_template` can be **any valid JSON structure** (deeply nested objects, arrays, etc.). DashCord will recursively scan your template and replace `{{placeholders}}` with real-time data using dot-notation.

```json
"commands": {
  "ai-task": {
    "endpoint": "http://192.168.1.100/run/ai",
    "method": "POST",
    "body_template": {
      "settings": {
        "priority": "high",
        "dry_run": false
      },
      "user_info": {
        "name": "{{discord.user_display}}",
        "id": "{{discord.user_id}}"
      },
      "task_data": {
        "prompt": "{{raw}}",
        "file_name": "{{attachment.filename}}",
        "file_base64": "{{attachment_b64}}"
      }
    }
  }
}
```

**Common Placeholders You Can Use:**
* `{{raw}}`: The full text the user typed (e.g., `!weather tomorrow`).
* `{{args}}`: The list of arguments provided by the user (e.g., `['now', 'tomorrow']`).
* `{{nonce}}`: A unique UUID generated for every single request. Use this for idempotency or as a database primary key.
* `{{command}}`: The name of the command triggered.
* `{{discord.user_id}}` / `{{discord.user_display}}`: Information about the triggering user.
* `{{discord.channel_id}}` / `{{discord.channel_name}}`: Information about the channel.
* `{{attachment_b64}}`: The fully encoded base64 string of the uploaded file.
* `{{source_meta_b64}}`: A Base64-encoded JSON object containing both the `discord` and `attachment` metadata blocks.
* `{{attachment_text}}`: The raw UTF-8 text of the file (great for `.txt` or `.json` uploads).
* `{{attachment.filename}}`: The original name of the uploaded file.

---

## 📦 Default Webhook Payload

If you **do not** use a `body_template`, your Webhook will receive DashCord's default JSON POST payload. This is also the exact underlying data structure you are querying when using `{{placeholders}}` in a custom template:

```json
{
  "source": "discord",
  "event_type": "command", 
  "command": "ping",
  "args": ["restart", "now"],
  "raw": "!ping restart now",
  "timestamp": "2026-02-25T12:00:00-05:00",
  "nonce": "a1b2c3d4-...",
  "discord": {
    "guild_id": "123456...",
    "guild_name": "My Server",
    "channel_id": "123456...",
    "channel_name": "general",
    "user_id": "123456...",
    "user_name": "cooluser123",
    "user_display": "CoolUser",
    "message_id": "123456..."
  },
  "meta": {
    "timezone": "America/New_York"
  },
  
  // (The following are only included if a file was uploaded)
  "attachment": {
    "filename": "data.json",
    "content_type": "application/json",
    "size": 1024,
    "url": "https://cdn.discordapp.com/..."
  },
  "attachment_text": "{\"hello\": \"world\"}",
  "attachment_bytes_len": 1024,
  "attachment_b64": "eyJoZWxsbyI6ICJ3b3JsZCJ9",
  "source_meta_b64": "..."
}
```
> **💡 Pro Tip: Using the Nonce**
> Every request includes a `nonce` (a unique UUID). If you are performing sensitive actions, like processing a payment or restarting a production server, your webhook should store this ID. If you receive a second request with the same `nonce` due to a network retry, you can safely ignore it to prevent duplicate actions (this is known as *idempotency*).

> **🔑 Authentication Header**
> The bot sends the `DASHCORD_SHARED_SECRET` (from your `.env` file) as a custom header:
> `X-DashCord-Token: your_secret_here`
> *Ensure your webhook validates this header so nobody else can trigger your endpoints!*
> 
> **💡 n8n Tip:** Most automation platforms (like Node.js & n8n) normalize HTTP headers to lowercase. You should look for `x-dashcord-token` in your expressions (e.g., `{{ $json.headers["x-dashcord-token"] }}`).

---

## 💬 Responding to Discord

Your webhook should respond with a **200 OK** status. To make the bot reply natively in Discord, return JSON from your webhook.

**Simple Text Reply:**
```json
{
  "reply": {
    "content": "✅ Server restart initiated!"
  }
}
```

**Rich Embed Reply:**
DashCord fully supports Discord embeds. Just pass an array of embed objects:
```json
{
  "reply": {
    "content": "Server Status Check:",
    "embeds":[
      {
        "title": "CPU Usage",
        "description": "Currently running at 45% capacity.",
        "color": 65280
      }
    ]
  }
}
```

*(If you do not want the bot to reply at all, return `{"reply": {"suppress": true}}` or just an empty 200 OK).*

---

### 🔧 Pro Configuration (.env)

DashCord is highly customizable. You can fine-tune exactly how the bot, your webhooks, and your interactive panels behave by modifying your `.env` file. 

#### 🤖 General Bot Settings
- `DISCORD_TOKEN`: **(Required)** Your Discord Bot Token.
- `COMMAND_PREFIX`: The prefix used for typed commands in chat (Default: `!`).
- `TIMEZONE`: The timezone used for panel timestamps and payload metadata (Default: `America/New_York`).
- `DISPLAY_UNKNOWN_COMMAND_ERROR`: If a user mistypes a command (e.g., `!wether`), the bot will reply with a helpful list of commands they actually have permission to use (Default: `true`).
- `DASHCORD_DEBUG`: Enables verbose internal debug logging in the console (Default: `false`).
- `ROUTES_PATH`: The file path to your routing configuration (Default: `routes.json` in the bot's root directory).

#### 🌐 Webhook & API Settings
- `DASHCORD_SHARED_SECRET`: A secret string sent as the `X-DashCord-Token` HTTP header to secure your webhooks from unauthorized requests.
- `HTTP_TIMEOUT_SECONDS`: How long the bot waits for your webhook to respond before throwing a timeout error (Default: `20`).
- `VERIFY_TLS`: Whether to verify SSL/TLS certificates when hitting your webhook URLs. Set to `false` if you are using self-signed certs on a local network (Default: `true`).
- `DEBUG_WEBHOOK`: Prints beautifully formatted, raw webhook request and response payloads directly to the console for API troubleshooting (Default: `false`).

#### 🎛️ Panel Interaction & Spawning
- `PANEL_SPAWN_NEW_ON_CLICK`: Post a fresh copy of the panel at the bottom of the chat automatically after a user clicks a button (Default: `true`).
- `PANEL_STATUS_LINE`: When a button is clicked, update the old panel's text to show an audit log of who clicked it (e.g., `Last: !ping restart • CoolUser • 4:05 PM`) (Default: `true`).
- `PANEL_ARCHIVE_DISABLE_BUTTONS`: When a button is clicked, permanently grey-out/disable the buttons on that specific message so users must use the newest panel at the bottom (Default: `true`).
- `PANEL_REPOST_ON_STARTUP`: When the bot boots up, it will scan channels to find your panels and "re-attach" itself to them so buttons keep working (Default: `true`).
- `PANEL_FORCE_NEW_ON_STARTUP`: Instead of editing the existing panel in-place on boot, the bot will delete the old one and post a brand new panel at the bottom of the chat (Default: `true`).

#### 🧹 Panel Persistence & Cleanup
*Persistence is the bot's ability to keep panels at the bottom of the chat so they don't get lost when users are talking.*
- `PANEL_PERSIST_DEFAULT`: The global default for whether panels should automatically "jump" to the bottom of the chat (Default: `false`). *(Note: You can override this per-panel in `routes.json`)*.
- `PANEL_PERSIST_INTERVAL_SECONDS`: How often the background loop checks if chat activity has buried your panels (Default: `45`).
- `PANEL_PERSIST_CLEANUP_OLD_ACTIVE`: When the bot moves a panel to the bottom of the chat, it deletes the old one to prevent duplicates (Default: `true`).
- `PANEL_DELETE_OLD_PANELS`: Allows the bot to mass-delete old, disconnected panels if things get messy (Default: `true`).
- `PANEL_SCAN_LIMIT`: How many messages up the chat history the bot will scan when looking for old panels to clean up (Default: `50`).