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
- **📁 Flexible File Ingestion (Fan-out & Batch Mode):** Forward files directly to your webhooks. Auto-parse JSON attachments, convert to Base64, and choose between fan-out (1 webhook per file) or batch mode (bundle all uploaded files into an `attachments` array in a single webhook).
- **🎭 Dynamic Body Templating:** Inject Discord metadata (like `{{discord.user_display}}`, `{{discord.user_roles}}`, or `{{discord.channel_id}}`) directly into the JSON payload sent to your webhook, molding the data to fit your API perfectly.
- **🪝 Dynamic Response Templating:** Connect buttons directly to 3rd-party APIs (OpenAI, GitHub, Local servers). DashCord can intercept raw JSON responses and dynamically map them into beautiful Discord Embeds without needing a middleman server to translate the data!
- **🔑 Personal User API Tokens:** Dynamically inject individual Bearer tokens based on the triggering Discord User ID (`USER_TOKEN_<USER_ID>`) to authorize multi-tenant automation workflows.
- **✂️ Long-Message Chunking & Codeblock Continuity:** Automatically splits long webhook responses (>1900 chars) cleanly across multiple Discord messages while preserving markdown code block syntax (````lang ... ````) and leading indentation.
- **🔒 Security Built-In:** Restrict specific commands to specific Discord channels or user IDs. Secures outbound requests with a custom `X-DashCord-Token` header.
- **💬 Native Discord Replies & Dynamic Panels:** Your webhook can respond with JSON containing plain text, rich Discord Embeds, or even dynamic UI panels (`reply.panel`), and the bot will cleanly post or update them in-place.
- **👁️ Visual Status Indicators:** Real-time emoji reactions (⏳, ✅, ❌) let users know exactly when a command is processing, succeeded, or failed without needing extra text replies.
- **⏱️ Live Ticking Animations & Loading Panes:** Turn on animated loading messages and watch a live `(2.5s)` counter tick up in real-time before morphing directly into the final webhook reply.
- **📡 Programmatic REST API & Message Dispatcher:** Create, update, refresh, or delete UI dashboards on the fly via REST, or push automated channel messages with optional delay timers (`POST /api/send_message`).
- **🥷 Stealth & Ephemeral Routing:** Configure specific commands to reply privately (so only the clicking user sees the result) and disable public bot reactions (`⏳`) for total chat cleanliness.
- **🚧 API Maintenance Mode:** Disable UI panels on the fly via the API. Keep the panel visible in chat, but grey out all buttons and dropdowns while your backend is restarting.
- **⚙️ Max Configuration:** Everything is overrideable. Set global defaults in your `.env`, but override emojis, delays, animations, and privacy settings down to the individual panel or command level.
  
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

Commands map a typed Discord message (or Slash Command) to a webhook URL. You have ultimate control over how the command behaves visually and functionally.

```json
"commands": {
  "deploy-server": {
    "endpoint": "https://your-automation-tool.com/webhook/deploy",
    "method": "POST",
    "timeout": 60,
    "ephemeral_replies": true,
    "reactions_enabled": false,
    "action_persist_delay": 5.0,
    "allowed_users": ["1234567890"],
    "allowed_channels": []
  }
}
```
*Typing `!deploy-server` will securely trigger your webhook. Because `ephemeral_replies` is true, the response will only be visible to the user who triggered it.*

**Master Command Configuration Options:**
*   `endpoint`: **(Required)** The webhook URL to trigger.
*   `method`: HTTP method to use (`"POST"` or `"GET"`). (Default: `"POST"`).
*   `description`: The custom text description shown in Discord's native `/` Slash Command menu.
*   `allowed_users`: Array of Discord User IDs permitted to use this command. Leave empty `[]` to allow anyone.
*   `allowed_channels`: Array of Discord Channel IDs where this command can be used. Leave empty `[]` to allow anywhere.
*   `timeout`: How many seconds DashCord will wait for your webhook to reply before throwing an error. Great for long-running workflows (Overrides the `.env` global timeout).
*   `ephemeral_replies`: Set to `true` to make the bot's reply private (only the user who triggered it can see the response).
*   `reactions_enabled`: Set to `false` to prevent the bot from adding the `⏳` and `✅` reactions to typed chat commands. Perfect for stealthy background triggers.
*   `action_persist_delay`: Handles race conditions. If your automation tool sends multiple follow-up messages *after* replying to the button, this delay (in seconds) tells the bot to wait before jumping the panel to the bottom of the chat.
*   `headers`: A dictionary of custom HTTP headers to send to your webhook (Overrides the global `X-DashCord-Token`).
*   `body_template`: A custom JSON structure to map exactly what your webhook expects instead of the default DashCord schema.
*   `response_template`: A custom JSON structure used to map a 3rd-party API's raw JSON response into a valid Discord reply (supports dot-notation parsing, embeds, and arrays).
*   `reply_to_message`: If `true`, the bot responds by replying directly to the user's trigger message. If `false`, posts as a general message in the channel.
*   `loading_message`: If `true`, spawns a temporary loading message in chat while waiting for the webhook to complete.
*   `loading_text`: Custom loading text template (e.g. `"⏳ Working on {command}..."`).
*   `show_elapsed_time`: Appends an audit status line with elapsed time (e.g. `✅ Last: !deploy • User • 4:05 PM (2.1s)`) to the final reply.
*   `api_protected`: If `true`, completely blocks the Dynamic API from viewing or editing this command.
*   `api_writable`: If `true`, explicitly allows the Dynamic API to edit this command at runtime (if it's a static route).

> **💡 Note on Case Sensitivity**
> Commands are **case-insensitive for the end user** (they can type `!DEPLOY` or `!deploy`). However, you must define the command keys in `routes.json` in **all lowercase** (e.g., `"deploy"`, not `"Deploy"`).

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

> **💡 Perfect Argument Parity**
> When using a native Slash Command, you will see a single input field called `arguments`. 
> If you type `restart force` into the Slash input, DashCord automatically splits it behind the scenes, passing `["restart", "force"]` inside the `args` array to your webhook. This guarantees your backend workflows can process typed commands (`!deploy restart force`) and Slash Commands (`/deploy arguments: restart force`) using the exact same parsing logic.

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

> **💡 Pro-Tip: Wildcard Extensions**
> If you want a command to accept any file upload regardless of the file type, simply set `"extensions": []` or omit the `"extensions"` key entirely from the `attachment_rules` block.

> **💡 The "Fan-out" vs "Batch" Rule**
> By default (`"fanout": true`), if a user uploads **5 files at once**, DashCord fans out and triggers **5 separate webhook calls** (one for each file). This simplifies downstream workflows by handling one file per execution.
>
> If you set `"fanout": false`, DashCord switches to **Batch Ingestion Mode**, sending all uploaded files inside a single webhook POST request with an `attachments` array:
> ```json
> {
>   "source": "discord",
>   "event_type": "command",
>   "command": "batch-upload",
>   "attachments": [
>     {
>       "attachment": { "filename": "doc1.txt", "size": 1204, "content_type": "text/plain", "url": "..." },
>       "attachment_text": "...",
>       "attachment_bytes_len": 1204,
>       "attachment_b64": "...",
>       "source_meta_b64": "..."
>     },
>     {
>       "attachment": { "filename": "doc2.txt", "size": 842, "content_type": "text/plain", "url": "..." },
>       "attachment_text": "...",
>       "attachment_bytes_len": 842,
>       "attachment_b64": "...",
>       "source_meta_b64": "..."
>     }
>   ]
> }
> ```

> **🎭 Attachment Feedback**
> You can control how the bot replies to uploads using the `attachment_reply` block.
> *   `mode`: Set to `"errors"` (default) to only reply if something goes wrong, `"always"` to always confirm, or `"none"` for silence.
> *   `success_template` / `error_template`: Use `{ok}`, `{bad}`, and `{total}` as variables to customize the message.
> *   `require_json`: Set to `true` to force validation. DashCord natively parses standard JSON (objects/lists) as well as **Concatenated JSON / JSON Lines** (multiple raw JSON objects uploaded back-to-back, e.g., `{"id":1}{"id":2}`), validating them safely before hitting your webhook.

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

#### 🎛️ Master Panel Configuration (Max Config)
Every global setting in your `.env` can be overridden on a per-panel basis. This allows you to have a completely silent, static panel living right next to a fully animated, hyper-persistent dashboard.

Here is the **Ultimate Panel Schema** showing every possible configuration key:

```json
"panels": {
  "Ultimate_Dashboard": {
    "channels": ["112233445566778899"],
    "disabled": false,
    "show_title": true,
    "spawn_new_on_click": false,
    "archive_disable_buttons": false,
    "api_protected": false,
    "api_writable": true,
    "persist": {
      "enabled": true,
      "interval_seconds": 60,
      "cleanup_old_active": true,
      "on_response": true,
      "response_delay_sec": 1.5
    },
    "status": {
      "show_status_line": true,
      "show_elapsed_time": true,
      "emoji_in_status_line": true,
      "emoji_in_embed_title": true,
      "animate_pending_emoji": true,
      "animate_elapsed_time": true,
      "show_loading_message": false,
      "append_status_to_reply": false,
      "emojis": {
        "pending": "🔄",
        "pending_alt": "🔃",
        "success": "🟢",
        "fail": "🔴"
      }
    },
    "embed": { ... },
    "buttons": [ ... ],
    "selects": [ ... ]
  }
}
```

**Root Panel Options:**
*   `disabled`: *(Maintenance Mode)* Instantly greys out and locks all buttons/dropdowns. Users can read the embed, but cannot click anything. (Great for API toggling during backend restarts).
*   `show_title`: Toggles the `🧩 **DashCord Panel** ({name})` header text above the embed.
*   `spawn_new_on_click`: If `false`, the bot will update the *existing* message in place when clicked instead of posting a new copy at the bottom of the chat.
*   `archive_disable_buttons`: If `false`, old messages keep their buttons clickable instead of permanently greying them out.
*   `api_protected`: If `true`, completely blocks the Dynamic API from viewing or modifying this panel.
*   `api_writable`: If `true`, explicitly allows the Dynamic API to edit this static panel at runtime.

**The `persist` Block (Sticky UI):**
*   `enabled`: Turns on the background loop to auto-jump the panel to the bottom of the chat if users are talking.
*   `interval_seconds`: How often the background loop checks if the panel is buried.
*   `cleanup_old_active`: Deletes the old panel when jumping to the bottom so the chat doesn't get cluttered.
*   `on_response`: Automatically jumps the panel to the bottom the exact moment a webhook replies (Highly recommended).
*   `response_delay_sec`: Overrides the command-level delay. Waits X seconds after a webhook replies before jumping to the bottom (Fixes n8n/Make race conditions where subsequent messages fire after the webhook response).

**The `status` Block (Animations & Aesthetics):**
*   `show_status_line`: Injects an audit log (`✅ Last: !deploy • User • 4:05 PM`) into the raw text of the message after a click.
*   `show_elapsed_time`: Appends the final processing time to the status line: `... 4:05 PM (4.2s)`.
*   `emoji_in_status_line` / `emoji_in_embed_title`: Toggles whether status emojis appear in the text line and embed title.
*   `animate_pending_emoji`: Alternates back and forth between your `pending` and `pending_alt` emojis while the webhook is processing.
*   `animate_elapsed_time`: Spawns a live, ticking timer `(1.5s -> 3.0s)` in the UI while waiting for your webhook.
*   `show_loading_message`: If `true`, spawns a temporary animated loading pane in chat when a button is clicked.
*   `append_status_to_reply`: Appends the status audit line (`✅ Last: ... (1.5s)`) directly to the webhook's response reply message instead of modifying the panel.
*   `emojis`: Define custom emojis for pending, success, and fail states.
  
---

### 4. Interactive Forms (Modals)

DashCord allows you to turn **any button or dropdown (select) option into a pop-up form**. Instead of just triggering a command instantly, Discord will prompt the user to fill out input fields, merge their answers under `"modal_inputs"`, and *then* send the complete payload to your webhook.

#### 🚀 Binding a Modal to a Button
To trigger a form from a standard button, add a `"modal"` dictionary directly to the button object:

```json
{
  "label": "Deploy Update",
  "command": "ping",
  "style": "success",
  "emoji": "🚀",
  "modal": {
    "title": "Deploy New Container",
    "inputs": [
      { "id": "image_tag", "label": "Docker Tag / Version", "placeholder": "e.g. latest, v2.1.0" }
    ]
  }
}
```

#### 🌤️ Binding a Modal to a Dropdown (Select Option)
To trigger a form from a dropdown menu, add the `"modal"` dictionary directly inside the specific option inside your `selects` array:

```json
"selects": [
  {
    "placeholder": "Choose a maintenance task...",
    "options": [
      {
        "label": "Troubleshoot Server",
        "command": "ping",
        "args": ["troubleshoot"],
        "emoji": "🛠️",
        "modal": {
          "title": "File Incident Ticket",
          "inputs": [
            { "id": "ticket_id", "label": "Jira / Incident Ticket ID", "placeholder": "e.g. DEVOPS-104", "required": true },
            { "id": "issue_desc", "label": "Describe the Issue", "placeholder": "What is broken?", "long": true }
          ]
        }
      }
    ]
  }
]
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
* `{{timestamp}}`: The local ISO-8601 timestamp generated at execution time (e.g., `2026-07-02T15:16:00-04:00`).
* `{{source}}`: Always `"discord"` (useful if routing multiple platforms to a single database).
* `{{event_type}}`: The raw event trigger type (e.g., `"command"`, `"upload-only"`, or `"panel_action"`).
* `{{meta.timezone}}`: The active timezone of the bot (e.g., `America/New_York`).
* `{{discord.user_name}}`: The actual Discord account username/handle (e.g., `cooluser123` vs. display name `CoolUser`).
* `{{discord.user_roles}}`: A list of Discord Role IDs assigned to the user (excluding `@everyone`), e.g. `["123456789012345678"]`.
* `{{discord.user_role_names}}`: A list of Discord Role names assigned to the user, e.g. `["Admin", "DevOps"]`.
* `{{discord.guild_id}}` / `{{discord.guild_name}}`: The server ID and server Name where the action was taken.
* `{{discord.message_id}}` / `{{discord.interaction_id}}`: Unique Discord snowflake IDs for message mapping, audit trails, or debug logging.
  
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

#### 🔑 Personal User API Tokens (`USER_TOKEN_<USER_ID>`)
If your backend or n8n workflow manages permissions on a per-user basis, you can define individual API Bearer tokens in your `.env` or `secrets.env` mapped by Discord User Snowflake ID:

```ini
USER_TOKEN_1443414759046250536=dc_usr_token_abcdef123456
USER_TOKEN_941490597930348614=dc_usr_token_789012ghijkl
```

When a user with a configured token triggers any command or panel button, DashCord automatically injects their token as:
```http
Authorization: Bearer dc_usr_token_abcdef123456
```
*(If `DASHCORD_SHARED_SECRET` is set, DashCord still transmits `X-DashCord-Token` concurrently so your server can verify bot integrity while authorizing the individual user).*

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
    "user_roles": ["123456789012345678", "987654321098765432"],
    "user_role_names": ["Admin", "DevOps"],
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

**Ephemeral (Private) Replies:**
If you want to keep the chat completely clean, your webhook can force the reply to be ephemeral (only the clicking user can see it):
```json
{
  "reply": {
    "content": "✅ Server restarted secretly.",
    "ephemeral": true
  }
}
```
*(Note: If a command is configured with `"ephemeral_replies": true` in `routes.json`, all replies will be private automatically. This JSON flag allows your webhook logic to conditionally override that setting on the fly).*

#### 🎛️ Dynamic Interactive Panels in Replies (`reply.panel`)
Your webhook response can dynamically return a panel UI schema under `"panel"` or `"reply": { "panel": { ... } }`. DashCord will attach interactive buttons and dropdowns directly to the reply, and save dynamic panels to disk:

```json
{
  "reply": {
    "content": "Select a maintenance task to execute:",
    "panel": {
      "id": "dyn_maintenance",
      "buttons": [
        { "label": "Purge Cache", "command": "ping", "args": ["purge"], "style": "danger", "emoji": "🧹" },
        { "label": "Health Check", "command": "uptime", "style": "success", "emoji": "🩺" }
      ],
      "selects": [
        {
          "placeholder": "Choose server action...",
          "options": [
            { "label": "Restart Node", "command": "ping", "args": ["restart"], "emoji": "🔄" },
            { "label": "View Logs", "command": "uptime", "emoji": "📋" }
          ]
        }
      ]
    }
  }
}
```
*   **Command Linking:** Any `command` specified in dynamic buttons or dropdowns will execute against your active commands defined in `routes.json`.
*   **In-Place UI Updates:** If a webhook returns `"panel"` with *no text content* (or empty string), DashCord will automatically update the original calling panel view in-place instead of posting a new message.

#### ✂️ Smart Message Chunking (>2000 Chars)
If your webhook response exceeds Discord's 2,000-character limit, DashCord uses `_send_chunked` to automatically split the output at paragraph boundaries and newlines. 
- **Code Block Continuity:** If a chunk cuts off inside an open markdown code block (````json ... ````), DashCord cleanly closes the block at the end of the chunk and reopens ````json on the next chunk so formatting is never broken.
- **Indentation Protection:** Prepends zero-width spaces to preserved whitespace so Discord does not strip leading indentation.

#### 🪵 Auto-Formatting Console Outputs (`stdout`)
If you are running automation pipelines that execute shell commands or script tasks, formatting them into rich JSON embeds can be tedious. If your webhook response returns a root `"stdout"` key instead of a `"reply"`, DashCord automatically formats it into a cleanly styled terminal code block:

```json
{
  "stdout": "Loaded 12 dependencies...\nStarting build compilation...\nBuild complete (1.2s)."
}
```

**Discord Visual Result:**
```
Loaded 12 dependencies...
Starting build compilation...
Build complete (1.2s).
```

#### 📦 Middleware Response Unwrapping
DashCord contains defensive parsing routines to prevent errors when automation platforms return wrapped structures. It will automatically detect and unwrap:
*   **Arrays:** If your endpoint responds with a list containing a single dictionary `[{ "ok": true }]`, DashCord safely extracts index `0`.
*   **Nesting:** If your platform wraps replies under a parent `"response"` block (e.g., `{ "response": { "reply": { ... } } }`), the bot extracts the inner data structure automatically.
  
*(If you do not want the bot to reply at all, return `{"reply": {"suppress": true}}` or just an empty 200 OK).*

---

## 🪝 Response Templates (Mapping 3rd-Party APIs)

By default, DashCord expects your automation tool to return a specific JSON structure (`{"reply": {"content": "..."}}`). 

But if you connect a button directly to an external API (like GitHub, OpenAI, or a local server) that you don't control, it will return raw JSON. Instead of writing a custom middleware server, you can use a **`response_template`** directly in your command config to translate that raw data into Discord-ready messages.

---

### 💻 Step-by-Step Walkthrough: Mapping HTTPBin

Here is exactly how to map a raw API response using a live test with `httpbin.org`.

#### Step 1: Define the Base Command
First, we create a basic command in `routes.json` that sends a custom payload to HTTPBin. 

```json
"commands": {
  "ping": {
    "endpoint": "https://httpbin.org/post",
    "method": "POST",
    "body_template": {
      "params": {
        "message": "PONG!",
        "user": "{{discord.user_name}}"
      }
    }
  }
}
```

#### Step 2: Trigger the Command & Check Logs
If you link this command to a button and click it, HTTPBin will echo your payload back. Because the API doesn't return DashCord's expected `{"reply": ...}` format, nothing will happen in Discord. 

However, DashCord intercepts the raw API response and prints it to your console. This is the exact raw log you will see:

```text
================ WEBHOOK RESPONSE ================
command: ping
endpoint: https://httpbin.org/post
status: 200
content-type: application/json
text_preview: {
  "args": {}, 
  "data": "{\"params\": {\"message\": \"PONG!\", \"user\": \"milkyway\"}}", 
  "files": {}, 
  "form": {}, 
  "headers": {
    "Accept": "*/*", 
    "Accept-Encoding": "gzip, deflate", 
    "Content-Length": "55", 
    "Content-Type": "application/json", 
    "Host": "httpbin.org", 
    "User-Agent": "Python/3.12 aiohttp/3.14.1", 
    "X-Amzn-Trace-Id": "Root=1...", 
    "X-Dashcord-Token": "..."
  }, 
  "json": {
    "params": {
      "message": "PONG!", 
      "user": "milkyway"
    }
  }, 
  "origin": "160.219.119.128", 
  "url": "https://httpbin.org/post"
}
==================================================
```

#### Step 3: Trace your Data Path
To display this data in Discord, look at the JSON keys inside the log above and trace their paths:
1. **Origin IP:** Located at the root under `"origin"`. Path: `{{origin}}`
2. **User-Agent:** Located inside the `headers` object. Path: `{{headers.User-Agent}}`
3. **Echoed Message:** Located deep inside `json` -> `params` -> `message`. Path: `{{json.params.message}}`

#### Step 4: Add the Response Template
Now, we simply update our command in `routes.json` with a `response_template` using those exact paths to tell DashCord how to format the message:

```json
"commands": {
  "ping": {
    "endpoint": "https://httpbin.org/post",
    "method": "POST",
    "body_template": {
      "params": {
        "message": "PONG!",
        "user": "{{discord.user_name}}"
      }
    },
    "response_template": {
      "reply": {
        "content": "🎯 **API Ping Success!**\n\n**🌍 Origin IP:** `{{origin}}`\n**🤖 User-Agent:** `{{headers.User-Agent}}`\n**💬 Echoed Message:** `{{json.params.message}}`"
      }
    }
  }
}
```

#### Step 5: The Result in Discord
When a user clicks your button now, DashCord automatically translates the raw JSON from the console log and posts this clean output to the channel:

> 🎯 **API Ping Success!**
> 
> **🌍 Origin IP:** `160.219.119.128`
> **🤖 User-Agent:** `Python/3.12 aiohttp/3.14.1`
> **💬 Echoed Message:** `PONG!`

### 💡 Advanced Mapping (Embeds, Arrays & Privacy)

Because `response_template` is evaluated recursively against the entire JSON payload, you can use it to dynamically generate rich Discord Embeds, toggle ephemeral (private) states, or pull from arrays!

#### 🎨 1. Dynamic Discord Embeds
You can map 3rd-party API data directly into Discord Embed fields.
If a server-monitoring API returns `{"hostname": "Prod-DB", "cpu": 98, "status": "Critical"}`, you can map it to a red embed:

```json
"response_template": {
  "reply": {
    "embeds": [
      {
        "title": "🖥️ {{hostname}} Status",
        "description": "System status is currently: **{{status}}**",
        "color": 16711680,
        "fields": [
          {
            "name": "CPU Usage",
            "value": "`{{cpu}}%`",
            "inline": true
          }
        ]
      }
    ]
  }
}
```

#### 📚 2. Accessing Arrays (Lists)
If your API returns a list of items (e.g., `{"results": [{"name": "Task 1"}, {"name": "Task 2"}]}`), you can access specific indexes using numbers in your dot-notation:

```json
"response_template": {
  "reply": {
    "content": "✅ The latest task completed was: **{{results.0.name}}**"
  }
}
```

#### 🥷 3. Dynamic Privacy (Ephemeral Flags)
You can even use the API's response to decide if the Discord message should be public or private. If your API returns `{"is_sensitive_data": true}`, you can map that directly to the `ephemeral` flag!

```json
"response_template": {
  "reply": {
    "content": "Here is the data: {{data}}",
    "ephemeral": "{{is_sensitive_data}}"
  }
}
```

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

All requests require your shared secret passed in the headers as either `X-DashCord-Token` or the standard HTTP `Authorization` header:
```http
Authorization: your_secret_here
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

### 📤 Direct REST Message Dispatcher (`POST /api/send_message`)

Send messages or Discord embeds directly to any Discord channel programmatically without triggering a command. Supports optional delayed background execution.

**Endpoint:** `POST /api/send_message`

**Payload Schema:**
```json
{
  "channel_id": "112233445566778899",
  "content": "🚀 Automated build #402 deployed successfully!",
  "embeds": [
    {
      "title": "Build Summary",
      "description": "Environment: `production`\nStatus: `Passed`",
      "color": 65280
    }
  ],
  "delay": 2.5
}
```

*   `channel_id`: **(Required)** Target Discord channel snowflake ID.
*   `content`: Raw text content (supports markdown and automatic chunking if >2000 chars).
*   `embeds`: Array of Discord Embed JSON objects (up to 10).
*   `delay`: Optional delay in seconds before sending. Runs as a background task, returning `200 OK` immediately.

```bash
curl -X POST http://127.0.0.1:8080/api/send_message \
  -H "Content-Type: application/json" \
  -H "X-DashCord-Token: YOUR_SECRET" \
  -d '{
    "channel_id": "112233445566778899",
    "content": "📢 Backup completed on storage array 1.",
    "delay": 0
  }'
```

*Response (200 OK):*
```json
{
  "status": "success",
  "message": "Message queued with 0.0s delay"
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

#### 💬 Chat Commands & Loading Indicators
- `COMMAND_REACTION_ENABLED`: Automatically add emoji reactions to user messages to show command status (pending, success, fail) (Default: `true`).
- `COMMAND_REACTION_PENDING`: The emoji to show while a command or file upload is being processed by your webhook (Default: `⏳`).
- `COMMAND_REACTION_SUCCESS`: The emoji to show when a command succeeds (Default: `✅`).
- `COMMAND_REACTION_FAIL`: The emoji to show when a command or webhook fails (Default: `❌`).
- `COMMAND_LOADING_MESSAGE_ENABLED`: Spawns a temporary loading message in chat while waiting for command webhooks to reply (Default: `false`).
- `COMMAND_LOADING_MESSAGE_TEXT`: Template text for the loading message (Default: `⏳ Processing \`{command}\`...`).
- `COMMAND_SHOW_ELAPSED_TIME`: Injects an audit status line with elapsed time into the final text reply (Default: `false`).
- `COMMAND_REPLY_TO_MESSAGE`: Whether command responses are posted as Discord inline replies referencing the user message (Default: `true`).
  
#### 🌐 Webhook Settings
- `DASHCORD_SHARED_SECRET`: A secret string sent as the `X-DashCord-Token` HTTP header to secure your webhooks from unauthorized requests.
- `USER_TOKEN_<DISCORD_USER_ID>`: Optional per-user Bearer token dynamically injected as `Authorization: Bearer <token>` when that specific user triggers a command or panel.
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

#### 🎨 Panel Visual Status Indicators & Animations
*When users click buttons, DashCord can dynamically inject status emojis and live timers into the UI.*
- `PANEL_STATUS_EMOJI_PENDING`: The emoji shown while your webhook is processing the action (Default: `⏳`).
- `PANEL_STATUS_EMOJI_SUCCESS`: The emoji shown when your webhook completes the action successfully (Default: `✅`).
- `PANEL_STATUS_EMOJI_FAIL`: The emoji shown when the webhook times out or fails (Default: `❌`).
- `PANEL_STATUS_EMOJI_IN_EMBED`: Automatically append the status emoji to the rich Embed Title (e.g., `🏠 Smart Home Hub ✅`) (Default: `true`).
- `PANEL_STATUS_EMOJI_TITLE`: Automatically prepend the status emoji to the text status line above the embed (e.g., `✅ Last: !ping • User • 4:05 PM`) (Default: `true`).
- `PANEL_STATUS_ANIMATE_PENDING`: Enables an animation loop that alternates the pending emoji while waiting for a response (Default: `false`).
- `PANEL_STATUS_EMOJI_PENDING_ALT`: The secondary emoji used if `PANEL_STATUS_ANIMATE_PENDING` is enabled (Default: `⌛`).
- `PANEL_STATUS_ANIMATE_INTERVAL`: The speed (in seconds) of the animation. Discord strictly limits message edits, so `1.5` is the minimum safe limit (Default: `1.5`).
- `PANEL_STATUS_SHOW_ELAPSED`: Appends the final processing time to the status line once completed (e.g., `(4.2s)`) (Default: `true`).
- `PANEL_STATUS_ANIMATE_ELAPSED`: Spawns a live ticking timer `(1.5s)` that visibly counts up in real-time while processing (Default: `true`).

#### 🧹 Panel Persistence & Cleanup
*Persistence is the bot's ability to keep panels at the bottom of the chat so they don't get lost when users are talking.*
- `PANEL_PERSIST_ON_RESPONSE`: If `true`, the bot will immediately jump the panel to the bottom of the chat after a user clicks a button and a response is returned. (Default: `true`).
- `PANEL_PERSIST_ON_RESPONSE_DELAY`: How many seconds to wait before moving the panel to the bottom after a response. Highly useful if your automation sends secondary follow-up messages and you want the panel to jump *after* those finish sending (Default: `0`).
- `PANEL_PERSIST_DEFAULT`: The global default for whether panels should automatically "jump" to the bottom of the chat (Default: `false`). *(Note: You can override this per-panel in `routes.json`)*.
- `PANEL_PERSIST_INTERVAL_SECONDS`: How often the background loop checks if chat activity has buried your panels (Default: `45`).
- `PANEL_PERSIST_CLEANUP_OLD_ACTIVE`: When the bot moves a panel to the bottom of the chat, it deletes the old one to prevent duplicates (Default: `true`).
- `PANEL_DELETE_OLD_PANELS`: Allows the bot to mass-delete old, disconnected panels if things get messy (Default: `true`).
- `PANEL_SCAN_LIMIT`: How many messages up the chat history the bot will scan when looking for old panels to clean up (Default: `50`).