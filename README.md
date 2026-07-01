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

| 🎛️ Interactive UI Dashboards | 📁 Advanced File Handling (TTS) |
| :--- | :--- |
| ![Interactive UI Dashboards](docs/dashboard_v4.png) | ![TTS File Upload](docs/tts_v2.png) |
| **📋 Interactive Forms (Modals)** | **📊 System Automation Logs** |
| ![Interactive Modals](docs/modal_v2.png) | ![System Automation Logs](docs/sync_v3.png) |
| **🏃 Manual Chat Commands** | **🌤️ Dynamic Weather Forecasts** |
| ![Manual Chat Commands](docs/fitbit_v2.png) | ![Dynamic Weather Panel](docs/weather_v2.png) |

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
- **👁️ Visual Status Indicators:** Real-time emoji reactions (⏳, ✅, ❌) let users know exactly when a command is processing, succeeded, or failed without needing extra text replies.

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

### 🐳 Docker Overrides (Custom API Ports & Local IPs)
If port `8080` is already in use on your host machine, or you need to mount local development variables without modifying tracked Git files, you can use a `docker-compose.override.yml` file. 

Create a file named `docker-compose.override.yml` in the root directory:

```yaml
services:
  dashcord:
    ports: !override
      - "8082:8080" # Binds external port 8082 on your host machine
    volumes:
      - ./secrets.env:/app/secrets.env
    extra_hosts:
      - "n8n.lan:192.168.1.102" # Map internal local LAN domains
```

> **💡 Missing Slash Commands?**
> Discord aggressively caches Slash Commands on desktop and mobile clients. If you start the bot and don't immediately see your `/commands` in Discord, completely restart your Discord app (CTRL+R on desktop) to clear the cache.

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
    "panel_persist_delay": 1.5,
    "allowed_users": ["1234567890"],
    "allowed_channels":[]
  }
}
```
*Typing `!ping test` will send a POST request containing the arguments to that webhook. Because `allowed_users` has an ID, only that Discord user can trigger it.*

> **💡 Handling Race Conditions (`panel_persist_delay`)**
> If your automation platform (like n8n) replies to a button click but *also* sends secondary follow-up messages a moment later, the bot might jump the panel to the bottom too fast, causing the panel to end up *above* your automation's follow-up messages. 
> To fix this, you can add `"panel_persist_delay": 1.5` (seconds) to the **command** configuration. This tells the bot to wait before jumping the panel to the bottom, mitigating the race condition.

> **💡 Note on Case Sensitivity**
> Commands are **case-insensitive for the end user** (they can type `!PING` or `!Ping`). However, you must define the command keys in `routes.json` in **all lowercase** (e.g., `"ping"`, not `"Ping"`).
>
> **❓ Smart Help**
> If a user types a command that doesn't exist, DashCord will automatically reply with a list of commands that the user **actually has permission to use** in that specific channel.

*   **Supported Methods:** Both `"POST"` and `"GET"` are supported.
*   **GET Requests:** If you choose `GET`, the entire JSON payload is stringified and passed as a URL query parameter (e.g., `?payload={"source":"discord", ...}`).

### ⌨️ Automatic Slash Commands

Whenever you add a new command to `routes.json`, DashCord will automatically register it as a native Discord Slash Command (e.g., `/ping`). 

Users can trigger it by typing the traditional prefix (`!ping restart`) OR by using the Discord slash menu (`/ping arguments: restart`).
- **Permissions:** The bot respects your `allowed_users` and `allowed_channels` rules even when triggered via Slash Commands.
- **Descriptions:** You can add a `"description"` key to your command config to customize what shows up in the Discord Slash Command menu!

```json
"commands": {
  "deploy": {
    "endpoint": "https://your-automation-tool.com/webhook/deploy",
    "description": "Trigger a server deployment pipeline",
    "allowed_users": ["1234567890"]
  }
}
```

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

### 3. Designing Interactive UI Dashboards (Embeds, Buttons & Dropdowns)

Panels create persistent, interactive dashboards in your Discord channels. You can bind specific commands to buttons and **Dropdown Menus (Selects)**, and wrap them in beautiful **Custom Embeds**.

```json
"panels": {
  "Home_Automation": {
    "channels": ["112233445566778899"],
    "embed": {
      "title": "🏠 Smart Home Hub",
      "color": "#3498db"
    },
    "selects": [
      {
        "placeholder": "🌤️ Weather & Environment...",
        "options": [
          { "label": "Get Local Weather", "command": "weather", "args": ["now"], "emoji": "🌤️" },
          { "label": "Check Indoor Temp", "command": "weather", "args": ["indoor"], "emoji": "🌡️" }
        ]
      }
    ],
    "buttons": [
      { "label": "Run AI Task", "command": "advanced-ai", "args": ["force"], "style": "success", "emoji": "🧠" }
    ]
  }
}
```

*   **Embeds:** Adding an `"embed"` block automatically upgrades your panel from plain text to a rich, colored dashboard with titles, descriptions, and thumbnails.
*   **Selects (Dropdowns):** A massive space-saver. Group related commands into clean select menus (max 5 select menus per panel, up to 25 options each).
    *   `placeholder`: The helper text displayed in the menu before an option is selected.
    *   `label`: The primary text displayed for the option.
    *   `description` (Optional): A subtitle displayed beneath the label inside the open dropdown menu.
*   **Buttons:** Standard quick-action buttons. 
    *   **Styles Available:** `primary` (Blurple), `secondary` (Grey), `success` (Green), `danger` (Red).
*   **Text Content & Titles:** You can add raw text above your embed using the `"content"` key. If you want to remove the default `🧩 **DashCord Panel** (name)` header, set `"show_title": false`.
*   **Dynamic API Security:** Add `"api_protected": true` to completely block the API from viewing or modifying a panel, or `"api_writable": true` to allow it.
*   **Emojis:** You can add `"emoji"` keys to both buttons and select options to make your dashboard visually intuitive.

**Customizing Persistence per Panel:**
If you want one panel to "jump" to the bottom of the chat every 60 seconds but another to stay put, add a `persist` block directly to the panel:
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

---

### 4. Interactive Forms (Modals)

DashCord allows you to turn **any button into a pop-up form**. Instead of just sending a predefined command when a button is clicked, Discord will prompt the user to type in data (like logging an entry or submitting a query), and *then* send that data to your webhook.

To enable this, add a `"modal"` dictionary to any button:

```json
{
  "label": "Deploy Update",
  "command": "ping",
  "args": ["deploy"],
  "style": "success",
  "emoji": "🚀",
  "modal": {
    "title": "Deploy New Container",
    "inputs": [
      { "id": "image_tag", "label": "Docker Tag / Version", "placeholder": "e.g. latest, v2.1.0", "required": true },
      { "id": "deploy_notes", "label": "Release Notes", "placeholder": "What changed in this deployment?", "required": false, "long": true }
    ]
  }
}
```

*   **Modal Schema Options:**
    *   `title`: The header displayed at the top of the pop-up modal.
    *   `inputs`: An array of text fields (Max: 5 fields per modal).
    *   `id`: The unique tracking key. The text entered by the user will be mapped to this ID under `"modal_inputs"` in the webhook payload.
    *   `label`: The field title displayed directly above the text box.
    *   `placeholder`: Light grey placeholder text shown inside the empty text box.
    *   `required`: Set to `true` to force the user to fill out the field before submitting (Default: `true`).
    *   `long`: Set to `true` to render a paragraph text box. Omit or set to `false` for a single-line input.

**The Webhook Payload:**
When the user submits the form, DashCord will merge their typed answers into your webhook payload under the `"modal_inputs"` key. Your automation platform (n8n, Make) will receive this:

```json
{
  "source": "discord",
  "event_type": "panel_action",
  "command": "ping",
  "args": ["deploy"],
  "timestamp": "2026-06-18T17:15:48-04:00",
  "discord": {
    "user_display": "D🪐PE",
    "channel_name": "devops-general"
  },
  "modal_inputs": {
    "image_tag": "v2.1.0",
    "deploy_notes": "Added support for interactive dropdown menus."
  }
}
```
You can now pull `{{ $json.body.modal_inputs.image_tag }}` directly into your database or deployment nodes!

### 5. Dynamic Body Templating (Optional)

By default, DashCord sends a standardized payload to your webhook. However, if your API requires a very specific JSON structure (or if you want to drop the bot straight into an existing integration without changing the API), you can define a `body_template`.

The `body_template` can be **any valid JSON structure** (deeply nested objects, arrays, etc.). DashCord will recursively scan your template and replace `{{placeholders}}` with real-time data using dot-notation.

**Example Template in `routes.json`:**
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

**What your Webhook Actually Receives:**
When a user uploads a file called `vocal_sample.wav` and types `!ai-task transcribe`, DashCord compiles the template on the fly. Your webhook will receive this perfectly formatted, custom payload:

```json
{
  "settings": {
    "priority": "high",
    "dry_run": false
  },
  "user_info": {
    "name": "D🪐PE",
    "id": "506198719609528768"
  },
  "task_data": {
    "prompt": "!ai-task transcribe",
    "file_name": "vocal_sample.wav",
    "file_base64": "U29tZSBmYWtlIGJhc2U2NCBiaW5hcnkgZGF0YS4uLg=="
  }
}
```

**Common Placeholders You Can Use:**
* `{{raw}}`: The full text the user typed (e.g., `!weather tomorrow`).
* `{{args}}`: The list of arguments provided by the user (e.g., `['now', 'tomorrow']`).
* `{{args.0}}`, `{{args.1}}`, etc.: Access individual arguments by their index (e.g., `{{args.0}}` retrieves the first argument typed after the command).
* `{{nonce}}`: A unique UUID generated for every single request. Use this for idempotency or as a database primary key.
* `{{command}}`: The name of the command triggered.
* `{{discord.user_id}}` / `{{discord.user_display}}`: Information about the triggering user.
* `{{discord.channel_id}}` / `{{discord.channel_name}}`: Information about the channel.
* `{{attachment_b64}}`: The fully encoded base64 string of the uploaded file.
* `{{source_meta_b64}}`: A Base64-encoded JSON object containing both the `discord` and `attachment` metadata blocks.
* `{{attachment_text}}`: The raw UTF-8 text of the file (great for `.txt` or `.json` uploads).
* `{{attachment.filename}}`: The original name of the uploaded file.
* `{{modal_inputs.your_field_id}}`: The raw text typed by a user into a specific modal input box (e.g., `{{modal_inputs.weight_lbs}}`).

### 6. Custom HTTP Headers (Optional)

By default, DashCord secures your webhooks using the `X-DashCord-Token` header globally defined in your `.env`. However, if you want to bypass your automation tool and point DashCord *directly* at a third-party API (like OpenAI, Gantry, or GitHub), you can define custom HTTP headers per-command.

```json
"commands": {
  "chat": {
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer sk-proj-YourApiKeyHere",
      "OpenAI-Organization": "org-123456"
    },
    "body_template": {
      "model": "gpt-4",
      "messages": [{"role": "user", "content": "{{raw}}"}]
    }
  }
}
```
*Note: Any custom headers defined in `routes.json` will override the global default token if they share the same key. If omitted, the bot falls back to using the global `.env` secret.*

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
  
  // (The following is only included if a modal form was submitted)
  "modal_inputs": {
    "your_input_id_1": "value typed by user",
    "your_input_id_2": "value typed by user"
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

## 📡 Dynamic API (Programmatic Routing)

DashCord provides a built-in REST API allowing you to create, update, read, and delete commands and panels at runtime. Changes made via the API are saved to a separate `dynamic_routes.json` file and persist across bot restarts.

This is incredibly powerful if you want your automation tools (n8n, Make, etc.) to dynamically spawn, update, or destroy UI panels in Discord on the fly.

### 1. Configuration & Authentication
Enable the API in your `.env` file:
```ini
API_ENABLED=true
API_PORT=8080
DYNAMIC_ROUTES_PATH=config/dynamic_routes.json

# If false, the API is blocked from modifying anything hardcoded in routes.json
API_ALLOW_STATIC_OVERWRITE=false 
```

All requests require your shared secret passed in the headers:
```http
X-DashCord-Token: your_secret_here
```

### 2. Endpoint & Schema
**`POST /api/dynamic`**

```json
{
  "type": "panel", 
  "action": "upsert",
  "id": "my_element_id",
  "config": { ... }
}
```

*   **`type`**: `"panel"` or `"command"`.
*   **`action`**: 
    *   `get`: Returns the JSON config for the specified `id`. (If `id` is omitted, it returns your entire active inventory).
    *   `upsert`: Creates or updates the item in memory and saves it to disk. Uses **deep merging**, so you only need to provide the fields you want to change.
    *   `refresh`: Same as `upsert`, but for panels, it immediately triggers a Discord message edit to reflect the new UI in the chat.
    *   `delete`: Removes the item, deletes it from disk, and removes the associated panel message from Discord.
*   **`id`**: The unique key for the command or panel.
*   **`config`**: The configuration object (uses the exact same schema as `routes.json`).

### 3. Security Flags & Shadowing (Strict Read-Only Guarantee)

> **🔒 Hard Guarantee: `routes.json` is Strictly Read-Only**
> DashCord never opens `routes.json` in write mode. It is physically impossible for the bot to modify, overwrite, or delete your static `routes.json` file on disk under any configuration or setting. You do not need to worry about the bot altering your core configuration files.

#### How "Shadowing" Works (In-Memory Overwrites)
When `API_ALLOW_STATIC_OVERWRITE` is set to `true`, the term "overwrite" refers strictly to **runtime memory**, not your filesystem. Here is exactly what happens when you modify a static route via the API:

1. **Memory Load:** At startup, DashCord reads your static `routes.json` file into memory.
2. **Dynamic Overlay:** It then reads `dynamic_routes.json` and overlays (shadows) those configurations on top of the active memory state.
3. **API Writes:** When you edit or delete a static route via the API, the changes are saved **only** to `dynamic_routes.json`. Your original `routes.json` file on disk remains completely untouched and pristine.
4. **API Deletions:** If you "delete" a static route via the API, the deletion is noted in runtime memory and the active Discord panel is removed, but your physical `routes.json` file is never altered.

#### Per-Item API Permissions
You can override default API behaviors on a per-item basis directly inside your read-only `routes.json` file:
*   `"api_writable": true` — Allows the API to modify or refresh this specific static item at runtime (with all changes written safely to `dynamic_routes.json`).
*   `"api_protected": true` — Completely hides the item from the API. It will not appear in programmatic `get` requests and returns a `403 Forbidden` if targeted by an edit.

> **💡 Best Practice:** Use `routes.json` for fixed, read-only system infrastructure. If you plan to heavily manage or dynamically update a panel via external automation tools (like n8n), do not define it in `routes.json` at all. Have your automation tool generate it entirely via the API so it lives 100% within the dynamic routing system.

---

### API Examples

**1. Retrieve All Configurations**  
Dump the active configuration of all panels (both static and dynamic).
```bash
curl -X POST http://127.0.0.1:8080/api/dynamic \
  -H "Content-Type: application/json" \
  -H "X-DashCord-Token: YOUR_SECRET" \
  -d '{"type": "panel", "action": "get"}'
```

*Response (200 OK):*
```json
{
  "status": "success",
  "panels": {
    "pc_power": {
      "channels": [1517700723616514130],
      "persist": {
        "enabled": true,
        "interval_seconds": 120,
        "cleanup_old_active": true
      },
      "embed": {
        "title": "🖥️ PC Power Control",
        "description": "Send a Wake-on-LAN magic packet to wake devices.",
        "color": "#2ecc71"
      },
      "buttons": [
        {
          "label": "Wake PC",
          "command": "wake-on-lan",
          "args": ["a1:f8:c8:b5:75:b0", "192.168.1.61"],
          "style": "success",
          "emoji": "⚡"
        }
      ]
    }
  }
}
```

**2. Create a Panel**  
Create a brand new panel with buttons and dropdowns.
```bash
curl -X POST http://127.0.0.1:8080/api/dynamic \
  -H "Content-Type: application/json" \
  -H "X-DashCord-Token: YOUR_SECRET" \
  -d '{
    "type": "panel",
    "action": "upsert",
    "id": "advanced_test_panel",
    "config": {
      "channels": [11227196329312276],
      "show_title": true,
      "content": "⚠️ System offline. Performing maintenance.",
      "embed": {
        "title": "🛠️ Advanced UI Test",
        "description": "This panel features Dropdowns and Modals!",
        "color": "#e74c3c"
      },
      "buttons": [
        {
          "label": "Open Form",
          "command": "ping",
          "style": "primary",
          "emoji": "📝",
          "modal": {
            "title": "Feedback Form",
            "inputs": [
              {
                "id": "feedback_text",
                "label": "What do you think of this?",
                "placeholder": "It is great...",
                "long": true,
                "required": true
              }
            ]
          }
        }
      ],
      "selects": [
        {
          "placeholder": "Choose a ping type...",
          "options": [
            { "label": "Ping Server", "command": "ping", "args": ["server"], "emoji": "🖥️", "description": "Check server status" },
            { "label": "Ping Network", "command": "ping", "args": ["network"], "emoji": "🌐", "description": "Check network status" }
          ]
        }
      ]
    }
  }'
```

*Response (200 OK):*
```json
{
  "status": "success",
  "message": "Panel 'advanced_test_panel' upserted",
  "results": [
    {
      "channel_id": 11227196329312276,
      "message_id": "1521635316388073654"
    }
  ]
}
```

**3. Partially Update (Refresh) Panel Content & State**  
DashCord's API uses deep-merging. You can change specific properties like the raw text `content` or embed aspects (`description`, `color`) without re-sending your original channels, buttons, or selects. 

Using the `"action": "refresh"` payload tells the bot to immediately edit the existing Discord message in-place to show the new state.

```bash
curl -X POST http://127.0.0.1:8080/api/dynamic \
  -H "Content-Type: application/json" \
  -H "X-DashCord-Token: YOUR_SECRET" \
  -d '{
    "type": "panel",
    "action": "refresh",
    "id": "advanced_test_panel",
    "config": {
      "content": "✅ Maintenance complete! All systems operational.",
      "embed": {
        "description": "The dynamic update was successfully applied.",
        "color": "#2ecc71"
      }
    }
  }'
```

*Response (200 OK):*
```json
{
  "status": "success",
  "message": "Panel 'advanced_test_panel' refreshed",
  "results": [
    {
      "channel_id": 11227196329312276,
      "message_id": "1521635316388073654"
    }
  ]
}
```
*(In Discord, the red warning panel instantly transitions to a green success state, keeping the original interaction buttons and dropdown selects intact.)*

**4. Retrieve a Single Panel Configuration**  
```bash
curl -X POST http://127.0.0.1:8080/api/dynamic \
  -H "Content-Type: application/json" \
  -H "X-DashCord-Token: YOUR_SECRET" \
  -d '{"type": "panel", "action": "get", "id": "advanced_test_panel"}'
```

*Response (200 OK):*
```json
{
  "status": "success",
  "id": "advanced_test_panel",
  "config": {
    "channels": [11227196329312276],
    "show_title": true,
    "content": "✅ Maintenance complete! All systems operational.",
    "embed": {
      "title": "🛠️ Advanced UI Test",
      "description": "The dynamic update was successfully applied.",
      "color": "#2ecc71"
    },
    "buttons": [
      {
        "label": "Open Form",
        "command": "ping",
        "style": "primary",
        "emoji": "📝",
        "modal": {
          "title": "Feedback Form",
          "inputs": [
            {
              "id": "feedback_text",
              "label": "What do you think of this?",
              "placeholder": "It is great...",
              "long": true,
              "required": true
            }
          ]
        }
      }
    ]
  }
}
```

**5. Delete a Panel**  
```bash
curl -X POST http://127.0.0.1:8080/api/dynamic \
  -H "Content-Type: application/json" \
  -H "X-DashCord-Token: YOUR_SECRET" \
  -d '{"type": "panel", "action": "delete", "id": "advanced_test_panel"}'
```

*Response (200 OK):*
```json
{
  "status": "success",
  "message": "Panel 'advanced_test_panel' deleted"
}
```

---

### 🔧 Pro Configuration (.env)

DashCord is highly customizable. You can fine-tune exactly how the bot, your webhooks, and your interactive panels behave by modifying your `.env` file. 

#### 🤖 General Bot Settings
- `DISCORD_TOKEN`: **(Required)** Your Discord Bot Token.
- `COMMAND_PREFIX`: The prefix used for typed commands in chat (Default: `!`).
- `TIMEZONE`: The timezone used for panel timestamps and payload metadata (Default: `America/New_York`).
- `DISPLAY_UNKNOWN_COMMAND_ERROR`: If a user mistypes a command (e.g., `!wether`), the bot will reply with a helpful list of commands they actually have permission to use (Default: `true`).
- `DISPLAY_UNKNOWN_COMMAND_ERROR_SILENT_CHANNELS`: A comma-separated list of channel IDs where the bot will never post an "Unknown command" error. Use this if you have other bots in the same channel so DashCord doesn't interrupt their commands (Default: empty).
- `DASHCORD_DEBUG`: Enables verbose internal debug logging in the console (Default: `false`).
- `ROUTES_PATH`: The file path to your routing configuration (Default: `routes.json` in the bot's root directory).
- `DYNAMIC_ROUTES_PATH`: The file path to your dynamic routing configuration (Default: `dynamic_routes.json` in the bot's config directory).
- `COMMAND_REACTION_ENABLED`: Automatically add emoji reactions to user messages to show command status (pending, success, fail) (Default: `true`).
- `COMMAND_REACTION_PENDING`: The emoji to show while a command or file upload is being processed by your webhook (Default: `⏳`).
- `COMMAND_REACTION_SUCCESS`: The emoji to show when a command succeeds (Default: `✅`).
- `COMMAND_REACTION_FAIL`: The emoji to show when a command or webhook fails (Default: `❌`).
  
#### 🌐 Webhook Settings
- `DASHCORD_SHARED_SECRET`: A secret string sent as the `X-DashCord-Token` HTTP header to secure your webhooks from unauthorized requests.
- `HTTP_TIMEOUT_SECONDS`: How long the bot waits for your webhook to respond before throwing a timeout error (Default: `20`).
- `VERIFY_TLS`: Whether to verify SSL/TLS certificates when hitting your webhook URLs. Set to `false` if you are using self-signed certs on a local network (Default: `true`).
- `DEBUG_WEBHOOK`: Prints beautifully formatted, raw webhook request and response payloads directly to the console for API troubleshooting (Default: `false`).

#### 📡 API Server Settings
- `API_ENABLED`: Turns on the local programmatic REST API (Default: `false`).
- `API_PORT`: The port the API binds to (Default: `8080`).
- `API_ALLOW_STATIC_OVERWRITE`: If `true`, the API is permitted to edit or delete routes that were hardcoded in `routes.json`. If `false`, it can only manage dynamic routes (Default: `false`).

#### 🎛️ Panel Interaction & Spawning
- `PANEL_SHOW_TITLE_DEFAULT`: Whether panels should automatically include the `🧩 **DashCord Panel** ({name})` title header above the embed. (Default: `true`).
- `PANEL_SPAWN_NEW_ON_CLICK`: Post a fresh copy of the panel at the bottom of the chat automatically after a user clicks a button (Default: `true`).
- `PANEL_STATUS_LINE`: When a button is clicked, update the old panel's text to show an audit log of who clicked it (e.g., `Last: !ping restart • CoolUser • 4:05 PM`) (Default: `true`).
- `PANEL_ARCHIVE_DISABLE_BUTTONS`: When a button is clicked, permanently grey-out/disable the buttons on that specific message so users must use the newest panel at the bottom (Default: `true`).
- `PANEL_REPOST_ON_STARTUP`: When the bot boots up, it will scan channels to find your panels and "re-attach" itself to them so buttons keep working (Default: `true`).
- `PANEL_FORCE_NEW_ON_STARTUP`: Instead of editing the existing panel in-place on boot, the bot will delete the old one and post a brand new panel at the bottom of the chat (Default: `true`).

#### 🎨 Panel Visual Status Indicators
*When users click buttons, DashCord can dynamically inject status emojis into the UI.*
- `PANEL_STATUS_EMOJI_PENDING`: The emoji shown while your webhook is processing the action (Default: `⏳`).
- `PANEL_STATUS_EMOJI_SUCCESS`: The emoji shown when your webhook completes the action successfully (Default: `✅`).
- `PANEL_STATUS_EMOJI_FAIL`: The emoji shown when the webhook times out or fails (Default: `❌`).
- `PANEL_STATUS_EMOJI_IN_EMBED`: Automatically append the status emoji to the rich Embed Title (e.g., `🏠 Smart Home Hub ✅`) (Default: `true`).
- `PANEL_STATUS_EMOJI_TITLE`: Automatically prepend the status emoji to the text status line above the embed (e.g., `✅ Last: !ping • User • 4:05 PM`) (Default: `true`).

#### 🧹 Panel Persistence & Cleanup
*Persistence is the bot's ability to keep panels at the bottom of the chat so they don't get lost when users are talking.*
- `PANEL_PERSIST_ON_RESPONSE`: If `true`, the bot will immediately jump the panel to the bottom of the chat after a user clicks a button and a response is returned. (Default: `true`).
- `PANEL_PERSIST_ON_RESPONSE_DELAY`: How many seconds to wait before moving the panel to the bottom after a response. Highly useful if your automation sends secondary follow-up messages and you want the panel to jump *after* those finish sending (Default: `0`).
- `PANEL_PERSIST_DEFAULT`: The global default for whether panels should automatically "jump" to the bottom of the chat (Default: `false`). *(Note: You can override this per-panel in `routes.json`)*.
- `PANEL_PERSIST_INTERVAL_SECONDS`: How often the background loop checks if chat activity has buried your panels (Default: `45`).
- `PANEL_PERSIST_CLEANUP_OLD_ACTIVE`: When the bot moves a panel to the bottom of the chat, it deletes the old one to prevent duplicates (Default: `true`).
- `PANEL_DELETE_OLD_PANELS`: Allows the bot to mass-delete old, disconnected panels if things get messy (Default: `true`).
- `PANEL_SCAN_LIMIT`: How many messages up the chat history the bot will scan when looking for old panels to clean up (Default: `50`).