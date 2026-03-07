import os
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio
import traceback

import base64
import re
from typing import Any
from datetime import timezone

import requests
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord.ext import tasks

import logging
BOT_STARTED_AT_UTC = datetime.now(timezone.utc)  # module load time (safe default)

def get_env_bool(key: str, default: str = "false") -> bool:
    """Helper to parse boolean environment variables."""
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes", "y", "on")

DASHCORD_DEBUG = get_env_bool("DASHCORD_DEBUG", "0")

log = logging.getLogger("dashcord")
log.setLevel(logging.DEBUG if DASHCORD_DEBUG else logging.INFO)

_handler = logging.StreamHandler()
_handler.setLevel(logging.DEBUG if DASHCORD_DEBUG else logging.INFO)
_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
_handler.setFormatter(_formatter)

# avoid duplicate handlers on reload
if not log.handlers:
    log.addHandler(_handler)

def _dbg(msg: str, *args):
    if DASHCORD_DEBUG:
        log.debug(msg, *args)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ----------------------------
# LOAD ENV
# ----------------------------
load_dotenv()
load_dotenv("secrets.env", override=True)

ROUTES_PATH = os.getenv("ROUTES_PATH", os.path.join(BASE_DIR, "routes.json"))

VERIFY_TLS = get_env_bool("VERIFY_TLS", "true")
DEBUG_WEBHOOK = get_env_bool("DEBUG_WEBHOOK", "0")
DISPLAY_UNKNOWN_COMMAND_ERROR = get_env_bool("DISPLAY_UNKNOWN_COMMAND_ERROR", "true")

DISPLAY_UNKNOWN_COMMAND_ERROR_SILENT_CHANNELS = set(
    cid.strip() for cid in os.getenv("DISPLAY_UNKNOWN_COMMAND_ERROR_SILENT_CHANNELS", "").split(",") if cid.strip()
)
# ----------------------------
# PANEL OPTIONS (.env)
# ----------------------------
PANEL_REPOST_ON_STARTUP       = get_env_bool("PANEL_REPOST_ON_STARTUP", "true")
PANEL_REPOST_ON_CLICK         = get_env_bool("PANEL_REPOST_ON_CLICK", "false")
PANEL_DELETE_OLD_PANELS       = get_env_bool("PANEL_DELETE_OLD_PANELS", "true")
PANEL_SCAN_LIMIT              = int(os.getenv("PANEL_SCAN_LIMIT", "50"))
PANEL_STATUS_LINE             = get_env_bool("PANEL_STATUS_LINE", "true")
PANEL_SPAWN_NEW_ON_CLICK      = get_env_bool("PANEL_SPAWN_NEW_ON_CLICK", "true")
PANEL_ARCHIVE_DISABLE_BUTTONS = get_env_bool("PANEL_ARCHIVE_DISABLE_BUTTONS", "true")
PANEL_FORCE_NEW_ON_STARTUP    = get_env_bool("PANEL_FORCE_NEW_ON_STARTUP", "true")
PANEL_PERSIST_DEFAULT         = get_env_bool("PANEL_PERSIST_DEFAULT", "false")
PANEL_PERSIST_INTERVAL_SECONDS = int(os.getenv("PANEL_PERSIST_INTERVAL_SECONDS", "45"))
PANEL_PERSIST_CLEANUP_OLD_ACTIVE = get_env_bool("PANEL_PERSIST_CLEANUP_OLD_ACTIVE", "true")

# channel_id -> { panel_name -> message_id }
PANEL_STATE: dict[str, dict[str, str]] = {}

# channel_id -> { panel_name -> active_message_id }
PANEL_ACTIVE: dict[str, dict[str, str]] = {}


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")
DASHCORD_SHARED_SECRET = os.getenv("DASHCORD_SHARED_SECRET", "")

HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))

PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")


# ----------------------------
# LOAD ROUTES.JSON
# ----------------------------
if not os.path.exists(ROUTES_PATH):
    raise RuntimeError(f"routes.json not found at: {ROUTES_PATH}")

with open(ROUTES_PATH, "r", encoding="utf-8") as f:
    ROUTES = json.load(f)
    

COMMANDS = ROUTES.get("commands", {}) or {}
PANELS = ROUTES.get("panels", {}) or {}

log.info(f"BOOT routes={ROUTES_PATH} prefix={COMMAND_PREFIX!r} cmds={sorted(COMMANDS.keys())}")

# ----------------------------
# HELPERS
# ----------------------------

def _message_time_utc(message: discord.Message) -> datetime:
    # created_at is UTC-aware in discord.py
    if getattr(message, "created_at", None):
        return message.created_at
    # fallback: derive from snowflake
    try:
        return discord.utils.snowflake_time(message.id)
    except Exception:
        return datetime.now(timezone.utc)

def _is_pre_start_message(message: discord.Message) -> bool:
    try:
        return _message_time_utc(message) < BOT_STARTED_AT_UTC
    except Exception:
        return False

def _is_one_or_many_json_objects(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False

    # normal json first
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return True
        if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
            return True
        return False
    except json.JSONDecodeError:
        pass

    # concatenated objects
    dec = json.JSONDecoder()
    i = 0
    n = len(text)
    found = 0

    while True:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        obj, end = dec.raw_decode(text, i)  # can throw
        if not isinstance(obj, dict):
            return False
        found += 1
        i = end

    return found > 0

def _clone_payload(payload: dict) -> dict:
    return json.loads(json.dumps(payload))

async def _fanout_attachments_to_command(message: discord.Message, command: str, base_payload: dict) -> None:
    cfg = _get_cmd_cfg(command)
    rules = cfg.get("attachment_rules") or {}
    exts = rules.get("extensions") or[]
    atts = _find_matching_attachments(message, exts)

    if not atts:
        want = ", ".join(exts) if exts else "any file"
        got = ", ".join([a.filename for a in (message.attachments or [])]) or "(none)"

        log.warning(f"⚠️ User uploaded wrong file type for command '{command}'. Expected: {want}, Got: {got}")
        
        await message.reply(f"❌ No matching attachment found. Expected: {want}. Got: {got}")
        return


    ok = 0
    bad = 0
    bad_lines: list[str] =[]

    for att in atts:
        p = _clone_payload(base_payload)
        handled, err = await _ingest_specific_attachment(att, command, p)
        if handled and err:
            bad += 1
            bad_lines.append(err)
            log.warning(f"⚠️ Attachment rejected for command '{command}': {err}")
            continue

        try:
            _dbg("Webhook call start cmd=%s att=%s", command, att.filename)
            try:
                data = await post_to_webhook_async(command, p)
            except Exception as e:
                _dbg("Webhook call EXCEPTION cmd=%s att=%s err=%s:%s", command, att.filename, type(e).__name__, e)
                raise
            finally:
                _dbg("Webhook call end cmd=%s att=%s", command, att.filename)


            if (data or {}).get("ok"):
                ok += 1
            else:
                bad += 1
                msg = ((data or {}).get("reply") or {}).get("content") or "unknown error"
                bad_lines.append(f"❌ `{att.filename}`: {msg[:200]}")
        except Exception as e:
            bad += 1
            bad_lines.append(f"❌ `{att.filename}`: {type(e).__name__}: {e}")
            _dbg("Webhook fanout failed att=%s err=%s:%s", att.filename, type(e).__name__, e)
            log.error(f"⚠️ Webhook fanout failed for attachment '{att.filename}': {e}", exc_info=True)


    # ----------------------------
    # routes-driven attachment reply policy
    # ----------------------------
    reply_cfg = cfg.get("attachment_reply") or {}
    if not isinstance(reply_cfg, dict):
        reply_cfg = {}

    mode = str(reply_cfg.get("mode", "errors")).strip().lower()
    # modes: none | errors | always
    if mode not in ("none", "errors", "always"):
        mode = "errors"

    total = len(atts)
    has_errors = (bad > 0)

    # Decide whether to reply at all
    should_reply = (
        (mode == "always") or
        (mode == "errors" and has_errors)
    )
    if not should_reply:
        return

    # Render templates (also routes-driven, no "queue" language baked in)
    success_tpl = str(reply_cfg.get("success_template", "📦 Uploaded {ok}/{total} file(s).")).strip()
    error_tpl   = str(reply_cfg.get("error_template", "❌ Upload errors ({bad}/{total}):\n{errors}")).strip()

    # Keep error list short
    errors_text = "\n".join(bad_lines[:6]).strip()

    if has_errors:
        msg = error_tpl.format(ok=ok, bad=bad, total=total, errors=errors_text)
    else:
        msg = success_tpl.format(ok=ok, bad=bad, total=total, errors="")

    # If template produced empty/whitespace, don't spam
    msg = (msg or "").strip()
    if msg:
        await message.reply(msg[:2000])


def _commands_allowing_upload_only() -> list[str]:
    out =[]
    for name, cfg in (COMMANDS or {}).items():
        if isinstance(cfg, dict) and cfg.get("allow_without_command") and cfg.get("accept_attachments"):
            out.append(str(name).lower())
    return out

def _is_upload_only_message(message: discord.Message) -> bool:
    # treat empty or whitespace-only content as upload-only
    return not (message.content or "").strip()


def _get_cmd_cfg(command: str) -> dict:
    cfg = COMMANDS.get(command) or {}
    return cfg if isinstance(cfg, dict) else {}

def _find_matching_attachments(message: discord.Message, exts: list[str]) -> list[discord.Attachment]:
    exts = [e.lower() for e in (exts or [])]
    out: list[discord.Attachment] = []
    for a in (message.attachments or[]):
        name = (a.filename or "").lower()
        if not exts:
            out.append(a)
        elif any(name.endswith(e) for e in exts):
            out.append(a)

    _dbg("ATT match exts=%s got=%s", exts, [a.filename for a in out])
    return out


async def _ingest_specific_attachment(att: discord.Attachment, command: str, payload: dict) -> tuple[bool, str]:
    cfg = _get_cmd_cfg(command)
    if not cfg.get("accept_attachments"):
        return (False, "")

    rules = cfg.get("attachment_rules") or {}
    if not isinstance(rules, dict):
        rules = {}

    max_bytes = int(rules.get("max_bytes", 2_500_000))
    require_json = bool(rules.get("require_json", False))

    if getattr(att, "size", 0) and att.size > max_bytes:
        return (True, f"❌ `{att.filename}` too large ({att.size} bytes). Max is {max_bytes} bytes.")

    try:
        b = await att.read()
    except Exception as e:
        return (True, f"❌ Failed to download `{att.filename}`: {type(e).__name__}: {e}")

    if len(b) > max_bytes:
        return (True, f"❌ `{att.filename}` too large ({len(b)} bytes). Max is {max_bytes} bytes.")

    try:
        text = b.decode("utf-8", errors="strict")
    except Exception as e:
        return (True, f"❌ `{att.filename}` is not valid UTF-8: {type(e).__name__}: {e}")

    if require_json:
        try:
            if not _is_one_or_many_json_objects(text):
                return (True, f"❌ `{att.filename}` JSON must be object, list[object], or multiple objects back-to-back.")
        except Exception as e:
            return (True, f"❌ `{att.filename}` invalid JSON: {type(e).__name__}: {e}")

        
    _dbg("ATT ingested filename=%s bytes=%d require_json=%s", att.filename, len(b), require_json)


    payload["attachment"] = {
        "filename": att.filename,
        "content_type": getattr(att, "content_type", None),
        "size": len(b),
        "url": getattr(att, "url", None),
    }
    payload["attachment_text"] = text
    payload["attachment_bytes_len"] = len(b)
    payload["attachment_b64"] = base64.b64encode(b).decode("ascii")

    meta_obj = {
        "discord": payload.get("discord", {}),
        "attachment": payload.get("attachment", {}),
    }
    payload["source_meta_b64"] = base64.b64encode(
        json.dumps(meta_obj, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    return (True, "")


def _render_body_template(tpl: Any, payload: dict) -> Any:
    """
    Replace {{...}} placeholders inside strings, recursively.
    Supports {{raw}}, {{command}}, {{args}}, {{discord.channel_id}}, etc.
    """
    if isinstance(tpl, str):
        def repl(m: re.Match) -> str:
            key = m.group(1)
            # dot-path lookup in payload
            cur: Any = payload
            for part in key.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    cur = ""
                    break
            return str(cur)
        return PLACEHOLDER_RE.sub(repl, tpl)

    if isinstance(tpl, dict):
        return {k: _render_body_template(v, payload) for k, v in tpl.items()}

    if isinstance(tpl, list):
        return[_render_body_template(x, payload) for x in tpl]

    return tpl

def _panel_persist_cfg(panel_cfg: dict) -> tuple[bool, int, bool]:
    p = panel_cfg.get("persist") if isinstance(panel_cfg, dict) else None
    if not isinstance(p, dict):
        return (PANEL_PERSIST_DEFAULT, PANEL_PERSIST_INTERVAL_SECONDS, PANEL_PERSIST_CLEANUP_OLD_ACTIVE)

    enabled = p.get("enabled", PANEL_PERSIST_DEFAULT)
    interval = int(p.get("interval_seconds", PANEL_PERSIST_INTERVAL_SECONDS))
    cleanup = p.get("cleanup_old_active", PANEL_PERSIST_CLEANUP_OLD_ACTIVE)

    enabled = bool(enabled)
    cleanup = bool(cleanup)
    if interval < 10:
        interval = 10  # safety: don’t spam-check too fast
    return (enabled, interval, cleanup)


async def _get_last_message(channel: discord.abc.Messageable) -> discord.Message | None:
    try:
        async for m in channel.history(limit=1):  # type: ignore[attr-defined]
            return m
    except Exception as e:
        log.warning(f"⚠️ Cannot fetch message history in channel {getattr(channel, 'id', 'unknown')} (Missing permissions?): {e}")
        return None
    return None


async def _get_last_message_id(channel: discord.abc.Messageable) -> int | None:
    m = await _get_last_message(channel)
    return m.id if m else None


async def _persist_panel_once(panel_name: str, channel: discord.abc.Messageable, panel_cfg: dict) -> None:
    # If panel is not last message, post a new active panel (force_new=True)
    last_id = await _get_last_message_id(channel)
    if last_id is None or not getattr(channel, "id", None):
        return

    active_id_str = _get_active_panel_msg_id(channel.id, panel_name)
    active_id = int(active_id_str) if active_id_str and active_id_str.isdigit() else None

    # If our active panel is already last, do nothing
    if active_id and last_id == active_id:
        return

    log.info(f"🔄 Persistence: Moving panel '{panel_name}' to bottom of channel {channel.id}")

    # Post new panel at bottom
    await _post_panel_to_channel(channel, panel_name, panel_cfg, force_new=True)

    # Cleanup previous active panel so we don’t accumulate junk
    enabled, interval, cleanup_old = _panel_persist_cfg(panel_cfg)
    if cleanup_old and active_id:
        try:
            old = await channel.fetch_message(active_id)  # type: ignore[attr-defined]
            if old and old.author and bot.user and old.author.id == bot.user.id:
                await old.delete()
        except Exception as e:
            log.warning(f"⚠️ Failed to delete old active panel message {active_id} (Missing permissions?): {e}")

def _get_active_panel_msg_id(channel_id: int, panel_name: str) -> str | None:
    return (PANEL_ACTIVE.get(_panel_key(channel_id), {}) or {}).get(panel_name)

def _set_active_panel_msg_id(channel_id: int, panel_name: str, message_id: int) -> None:
    PANEL_ACTIVE.setdefault(_panel_key(channel_id), {})[panel_name] = str(message_id)


def _panel_key(channel_id: int) -> str:
    return str(channel_id)

def _get_panel_msg_id(channel_id: int, panel_name: str) -> str | None:
    return (PANEL_STATE.get(_panel_key(channel_id), {}) or {}).get(panel_name)

def _set_panel_msg_id(channel_id: int, panel_name: str, message_id: int) -> None:
    PANEL_STATE.setdefault(_panel_key(channel_id), {})[panel_name] = str(message_id)

async def _delete_existing_panel_message(channel: discord.abc.Messageable, panel_name: str) -> None:
    if not getattr(channel, "id", None) or not bot.user:
        return

    stored = _get_panel_msg_id(channel.id, panel_name)
    if stored:
        try:
            msg = await channel.fetch_message(int(stored))  # type: ignore[attr-defined]
            if msg and msg.author and msg.author.id == bot.user.id:
                await msg.delete()
                log.info(f"🧹 Cleaned up stored old panel '{panel_name}' in channel {channel.id}")
                return
        except Exception:
            pass

    try:
        async for msg in channel.history(limit=PANEL_SCAN_LIMIT):  # type: ignore[attr-defined]
            if msg.author and bot.user and msg.author.id == bot.user.id:
                if isinstance(msg.content, str) and msg.content.startswith("🧩"):
                    if f"({panel_name})" in msg.content:
                        try:
                            await msg.delete()
        
                            log.info(f"🧹 Cleaned up old panel '{panel_name}' (ID: {msg.id}) from history")
                        except Exception as e:                
                            log.warning(f"⚠️ Failed to delete old panel '{panel_name}' (ID: {msg.id}) during cleanup: {e}")
    except Exception as e:
        log.warning(f"⚠️ Failed to scan history for cleanup in channel {channel.id}: {e}")

async def _find_existing_panel_message(channel: discord.abc.Messageable, panel_name: str):
    if not getattr(channel, "id", None) or not bot.user:
        return None

    ACTIVE_CONTENT = f"🧩 **DashCord Panel** ({panel_name})"

    try:
        async for msg in channel.history(limit=PANEL_SCAN_LIMIT):
            if msg.author and msg.author.id == bot.user.id:
                if isinstance(msg.content, str) and msg.content.strip() == ACTIVE_CONTENT:
                    log.info(f"🔍 Found existing panel '{panel_name}' in channel {channel.id}. Attaching to it.")
                    _set_panel_msg_id(channel.id, panel_name, msg.id)
                    return msg
    except Exception as e:
        log.warning(f"⚠️ Failed to scan for existing panel '{panel_name}' in channel {channel.id}: {e}")

    return None

async def _post_panel_to_channel(
    channel: discord.abc.Messageable,
    panel_name: str,
    panel_cfg: dict,
    *,
    force_new: bool = False
) -> None:
    content = f"🧩 **DashCord Panel** ({panel_name})"
    view = DashPanel(panel_name, panel_cfg)

    if not force_new:
        existing = await _find_existing_panel_message(channel, panel_name)
        if existing:
            try:
                _dbg("Updating existing message ID %s for panel '%s'", existing.id, panel_name)
                await existing.edit(content=content, view=view)
                _set_active_panel_msg_id(channel.id, panel_name, existing.id)
                return
            except Exception as e:
                log.warning(f"⚠️ Found existing panel '{panel_name}' but failed to edit it. Falling back to posting new. Error: {e}")


    log.info(f"🆕 Posting new panel '{panel_name}' to channel {getattr(channel, 'id', 'unknown')}")

    sent = await channel.send(content, view=view)
    if getattr(channel, "id", None):
        _set_panel_msg_id(channel.id, panel_name, sent.id)
        _set_active_panel_msg_id(channel.id, panel_name, sent.id)

def now_local_iso() -> str:
    try:
        return datetime.now(ZoneInfo(TIMEZONE)).isoformat()
    except Exception:
        return datetime.now().isoformat()

def resolve_endpoint(command: str) -> str:
    cfg = COMMANDS.get(command)
    if not cfg:
        raise RuntimeError(f"No command configured: {command}")

    endpoint = cfg.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
        raise RuntimeError(f"Invalid endpoint URL for command '{command}': {endpoint!r}")

    return endpoint

def _as_int_set(values) -> set[int]:
    out: set[int] = set()
    for v in (values or[]):
        try:
            out.add(int(v))
        except Exception:
            pass
    return out

def is_user_allowed(command: str, user_id: int, silent: bool = False) -> bool:
    allowed = (COMMANDS.get(command, {}) or {}).get("allowed_users",[])
    allowed_set = _as_int_set(allowed)
    ok = (len(allowed_set) == 0) or (int(user_id) in allowed_set)

    _dbg(
        "ALLOW_USER? cmd=%s user_id=%s(%s) allowed=%s -> %s",
        command,
        user_id, type(user_id).__name__,
        list(allowed_set),
        ok
    )

    if not ok and not silent:
        log.warning(f"🚫 User {user_id} denied access to command '{command}'")

    return ok

def is_channel_allowed(command: str, channel_id: int, silent: bool = False) -> bool:
    allowed = (COMMANDS.get(command, {}) or {}).get("allowed_channels",[])
    allowed_set = _as_int_set(allowed)
    ok = (len(allowed_set) == 0) or (int(channel_id) in allowed_set)

    _dbg(
        "ALLOW_CHAN? cmd=%s channel_id=%s(%s) allowed=%s -> %s",
        command,
        channel_id, type(channel_id).__name__,
        list(allowed_set),
        ok
    )

    if not ok and not silent:
        log.warning(f"🚫 Command '{command}' denied in channel {channel_id}")

    return ok


def build_payload(*, event_type, command, args, raw, guild, channel, user, message_id=None, interaction_id=None):
    return {
        "source": "discord",
        "event_type": event_type,  # "command" | "button"
        "command": command,
        "args": args,
        "raw": raw,
        "timestamp": now_local_iso(),
        "nonce": str(uuid.uuid4()),
        "discord": {
            "guild_id": str(guild.id) if guild else None,
            "guild_name": guild.name if guild else None,
            "channel_id": str(channel.id) if getattr(channel, "id", None) else None,
            "channel_name": getattr(channel, "name", None),
            "user_id": str(user.id),
            "user_name": getattr(user, "name", None),
            "user_display": getattr(user, "display_name", None),
            "message_id": str(message_id) if message_id else None,
            "interaction_id": interaction_id,
        },
        "meta": {"timezone": TIMEZONE},
    }

def _resolve_method(command: str) -> str:
    cfg = COMMANDS.get(command) or {}
    m = (cfg.get("method") or "POST").strip().upper()
    if m not in ("POST", "GET"):
        raise RuntimeError(f"Invalid method for command '{command}': {m!r} (use POST or GET)")
    return m

async def post_to_webhook_async(command: str, payload: dict) -> dict:
    # run blocking requests.* off the event loop
    return await asyncio.to_thread(post_to_webhook, command, payload)

def post_to_webhook(command: str, payload: dict) -> dict:
    cfg = COMMANDS.get(command) or {}
    endpoint = resolve_endpoint(command)
    method = _resolve_method(command)

    body_template = cfg.get("body_template")  # optional
    out_json = payload
    if body_template is not None:
        out_json = _render_body_template(body_template, payload)

    headers = {"Content-Type": "application/json"}
    if DASHCORD_SHARED_SECRET:
        headers["X-DashCord-Token"] = DASHCORD_SHARED_SECRET

    def parse_response(r: requests.Response) -> dict:
        _dbg("WEBHOOK POST cmd=%s status=%s", command, r.status_code)

        text = r.text or ""

        # ---- DEBUG RAW RESPONSE ----
        if DEBUG_WEBHOOK:
            safe_headers = dict(r.headers)
            preview = text[:800].replace("\n", "\\n")
            log.info(
                "\n================ WEBHOOK RESPONSE ================\n"
                f"command: {command}\n"
                f"endpoint: {endpoint}\n"
                f"status: {r.status_code}\n"
                f"content-type: {safe_headers.get('Content-Type')}\n"
                f"text_preview: {preview}\n"
                "=================================================="
            )

        # ---- TRY JSON ----
        try:
            data = r.json()
        except Exception:
            data = None

        # If endpoint responds with an "items array", unwrap item 0
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            data = data[0]

        # If endpoint wrapped the real payload under { "response": {...} }, unwrap it
        if isinstance(data, dict) and isinstance(data.get("response"), dict):
            data = data["response"]

        # If still not a dict, fall back to raw text
        if not isinstance(data, dict):
            data = {"ok": (200 <= r.status_code < 300), "reply": {"content": text}}


        # Normalize error responses
        if not (200 <= r.status_code < 300):
            log.warning(f"❌ Webhook Error [{command}]: HTTP {r.status_code} - {text[:200]}")
            data["ok"] = False
            data.setdefault("reply", {})
            if not isinstance(data["reply"], dict):
                data["reply"] = {"content": str(data["reply"])}
            data["reply"].setdefault("content", f"Webhook HTTP {r.status_code}: {text[:800]}")

        # Normalize reply shape
        data.setdefault("reply", {})
        if not isinstance(data["reply"], dict):
            data["reply"] = {"content": str(data["reply"])}

        # ---- DEBUG PARSED ----
        if DEBUG_WEBHOOK:
            reply_obj = data.get("reply")
            is_dict = isinstance(reply_obj, dict)
            reply_keys = list(reply_obj.keys()) if is_dict else None
            c = reply_obj.get("content") if is_dict else None
            c_len = len(c) if isinstance(c, str) else None
            c_preview = c[:200].replace("\n", "\\n") if isinstance(c, str) else None

            log.info(
                "\n================ WEBHOOK PARSED ================\n"
                f"PARSED TYPE: {type(data).__name__}\n"
                f"PARSED KEYS: {list(data.keys())}\n"
                f"REPLY TYPE: {type(reply_obj).__name__}\n"
                f"REPLY KEYS: {reply_keys}\n"
                f"CONTENT LEN: {c_len}\n"
                f"CONTENT PREVIEW: {c_preview}\n"
                "=================================================="
            )

        return data

    t0 = datetime.now().timestamp()
    _dbg("WEBHOOK request cmd=%s method=%s endpoint=%s timeout=%s verify_tls=%s",
        command, method, endpoint, HTTP_TIMEOUT_SECONDS, VERIFY_TLS)

    # --- primary request ---
    if method == "POST":
        r = requests.post(
            endpoint,
            headers=headers,
            json=out_json,
            timeout=HTTP_TIMEOUT_SECONDS,
            verify=VERIFY_TLS,
        )

        _dbg("WEBHOOK response cmd=%s status=%s elapsed=%.2fs",
        command, r.status_code, datetime.now().timestamp() - t0)

        if r.status_code == 404 and "not registered for POST requests" in (r.text or ""):
            r2 = requests.get(
                endpoint,
                headers=headers,
                params={"payload": json.dumps(out_json, separators=(",", ":"))},
                timeout=HTTP_TIMEOUT_SECONDS,
                verify=VERIFY_TLS,
            )
            return parse_response(r2)

        data = parse_response(r)
        _dbg("WEBHOOK parsed cmd=%s ok=%s reply_len=%s", command, data.get("ok"), len(((data.get("reply") or {}).get("content") or "")))
        return data


    # method == GET
    r = requests.get(
        endpoint,
        headers=headers,
        params={"payload": json.dumps(out_json, separators=(",", ":"))},
        timeout=HTTP_TIMEOUT_SECONDS,
        verify=VERIFY_TLS,
    )
    data = parse_response(r)
    _dbg("WEBHOOK parsed cmd=%s ok=%s reply_len=%s", command, data.get("ok"), len(((data.get("reply") or {}).get("content") or "")))
    return data


async def send_reply(channel: discord.abc.Messageable, data: dict) -> None:
    reply = (data or {}).get("reply") or {}
    if not isinstance(reply, dict):
        reply = {"content": str(reply)}

    # honor suppress flag (support both spellings)
    suppress = bool(reply.get("suppress") or reply.get("supress"))
    content = (reply.get("content") or "").strip()
    embeds_raw = reply.get("embeds") or []

    embeds: list[discord.Embed] =[]
    if isinstance(embeds_raw, list):
        for e in embeds_raw[:10]:
            if isinstance(e, dict):
                try:
                    embeds.append(discord.Embed.from_dict(e))
                except Exception:
                    pass

    # If suppress is true, send NOTHING.
    if suppress or (not content and not embeds):
        return

    await channel.send(content=content[:2000], embeds=embeds)

# ----------------------------
# DISCORD SETUP
# ----------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=COMMAND_PREFIX,
    intents=intents,
    help_command=None,
)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    log.error(f"⚠️ Discord Command Error in '{ctx.command}': {error}", exc_info=error)

    raise error

# ----------------------------
# PANEL UI
# ----------------------------
STYLE_MAP = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}

class DashButton(discord.ui.Button):
    def __init__(self, panel_name: str, cfg: dict):
        label = cfg.get("label", "Button")
        command = cfg.get("command")
        args = cfg.get("args", []) or[]
        style_name = (cfg.get("style") or "secondary").lower()

        if not isinstance(command, str) or not command:
            raise RuntimeError(f"Panel button missing command: {cfg}")

        super().__init__(
            label=label,
            style=STYLE_MAP.get(style_name, discord.ButtonStyle.secondary),
            custom_id=f"dashcord:{panel_name}:{command}:{'-'.join(args)}"
        )

        self.panel_name = panel_name
        self.command = command
        self.args = args

    async def callback(self, interaction: discord.Interaction):
        if not interaction.channel:
            await interaction.response.send_message("⚠️ No channel context.", ephemeral=True)
            return

        if not is_channel_allowed(self.command, interaction.channel.id):
            await interaction.response.send_message("⛔ Not allowed in this channel.", ephemeral=True)
            return

        if not is_user_allowed(self.command, interaction.user.id):
            await interaction.response.send_message("⛔ Not allowed for your user.", ephemeral=True)
            return

        # Defer silently
        await interaction.response.defer(ephemeral=True)

        log.info(f"🖱️ User '{interaction.user.display_name}' clicked button '{self.command}' on panel '{self.panel_name}'")

        cfg = _get_cmd_cfg(self.command)
        if cfg.get("accept_attachments"):
            log.warning(f"⚠️ User '{interaction.user.display_name}' clicked button '{self.command}' but it requires a file upload.")
            await interaction.followup.send(
                "❌ This command requires a file upload. Use the typed command with an attached file.",
                ephemeral=True,
            )
            return

        payload = build_payload(
            event_type="button",
            command=self.command,
            args=self.args,
            raw=f"[button] {self.command} {' '.join(self.args)}".strip(),
            guild=interaction.guild,
            channel=interaction.channel,
            user=interaction.user,
            interaction_id=str(interaction.id),
        )

        async def _archive_this_panel_message() -> None:
            try:
                msg = interaction.message
                if not msg:
                    return

                content = msg.content
                # Only update the text if STATUS_LINE is true
                if PANEL_STATUS_LINE:
                    try:
                        ts = datetime.now(ZoneInfo(TIMEZONE)).strftime("%-I:%M %p")
                    except Exception:
                        ts = datetime.now().strftime("%I:%M %p").lstrip("0")
                    user = getattr(interaction.user, "display_name", None) or getattr(interaction.user, "name", "Someone")
                    last_cmd = f"{self.command} {' '.join(self.args)}".strip()
                    content = f"🧩 **DashCord Panel** ({self.panel_name})\nLast: `{last_cmd}` • {user} • {ts}"

                # Always edit the view to apply the 'disabled' state
                archived_view = DashPanel(
                    self.panel_name,
                    PANELS.get(self.panel_name, {}) or {},
                    disabled=PANEL_ARCHIVE_DISABLE_BUTTONS
                )
                await msg.edit(content=content, view=archived_view)
            except Exception as e:
                log.warning(f"⚠️ Failed to edit/archive panel message (Missing permissions?): {e}")

        async def _spawn_new_panel() -> None:
            if not PANEL_SPAWN_NEW_ON_CLICK or not interaction.channel:
                return
            try:
                await _post_panel_to_channel(
                    interaction.channel,
                    self.panel_name,
                    PANELS.get(self.panel_name, {}) or {},
                    force_new=True,
                )
            except Exception as e:
                log.error(f"⚠️ Failed to spawn new panel '{self.panel_name}' after button click: {e}", exc_info=True)
        
        # 1. Archive immediately
        await _archive_this_panel_message()
        
        # 2. Spawn the new one immediately so it's ready even if the webhook is slow or fails
        await _spawn_new_panel()
            
        try:
            _dbg("Webhook button call start cmd=%s", self.command)
            data = await post_to_webhook_async(self.command, payload)
            _dbg("Webhook button call end cmd=%s", self.command)

            reply = (data or {}).get("reply") or {}
            if not isinstance(reply, dict):
                reply = {"content": str(reply)}

            suppress = bool(reply.get("suppress") or reply.get("supress"))
            content = (reply.get("content") or "").strip()


            if suppress or not content:
                return

            await interaction.followup.send(content=content[:2000], ephemeral=False)

        except Exception as e:
            log.error(f"⚠️ Exception triggering button command '{self.command}': {e}", exc_info=True)
            await interaction.followup.send(f"⚠️ Trigger failed: {type(e).__name__}: {e}", ephemeral=True)

class DashPanel(discord.ui.View):
    def __init__(self, panel_name: str, panel_cfg: dict, *, disabled: bool = False):
        super().__init__(timeout=None)
        for btn_cfg in (panel_cfg.get("buttons") or[]):
            b = DashButton(panel_name, btn_cfg)
            b.disabled = disabled
            self.add_item(b)


async def post_panels():
    for panel_name, panel_cfg in PANELS.items():
        channels = panel_cfg.get("channels") or[]
        for channel_id in channels:
            try:
                channel_id = int(channel_id)
            except Exception:
                log.warning(f"⚠️ Panel '{panel_name}': bad channel id: {channel_id!r}")
                continue

            channel = bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await bot.fetch_channel(channel_id)
                except Exception as e:
                    log.warning(f"⚠️ Panel '{panel_name}': cannot fetch channel {channel_id}: {e}")
                    continue

            try:
                if PANEL_FORCE_NEW_ON_STARTUP and PANEL_DELETE_OLD_PANELS:
                    await _delete_existing_panel_message(channel, panel_name)

                await _post_panel_to_channel(
                    channel,
                    panel_name,
                    panel_cfg,
                    force_new=PANEL_FORCE_NEW_ON_STARTUP,
                )
            except Exception as e:
                log.error(f"⚠️ Failed to post panel '{panel_name}' to {channel_id}: {e}")

# ----------------------------
# EVENTS
# ----------------------------
@bot.event
async def on_ready():
    global BOT_STARTED_AT_UTC
    BOT_STARTED_AT_UTC = datetime.now(timezone.utc)
    log.info(f"✅ DashCord online as {bot.user} (ID: {bot.user.id}) start_utc={BOT_STARTED_AT_UTC.isoformat()}")

    if PANEL_REPOST_ON_STARTUP:
        await post_panels()

    if not panel_persist_loop.is_running():
        panel_persist_loop.start()

@bot.event
async def on_disconnect():
    log.warning("🔌 DashCord disconnected from Discord Gateway.")

@bot.event
async def on_resumed():
    log.info("🔄 DashCord reconnected and resumed session.")

@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    if _is_pre_start_message(message):
        _dbg(
            "IGNORE pre-start msg id=%s msg_utc=%s bot_start_utc=%s",
            message.id,
            _message_time_utc(message).isoformat(),
            BOT_STARTED_AT_UTC.isoformat(),
        )
        return

    if not message.author.bot:
        _dbg(
            "MSG recv id=%s chan=%s(%s) author=%s content_len=%d has_atts=%s att_names=%s",
            message.id,
            getattr(message.channel, "id", None), type(getattr(message.channel, "id", None)).__name__,
            getattr(message.author, "name", None),
            len(message.content or ""),
            bool(message.attachments),[a.filename for a in (message.attachments or [])],
        )

    # ----------------------------
    # UPLOAD-ONLY ROUTES (no prefix)
    # ----------------------------
    upload_only = bool(message.attachments) and _is_upload_only_message(message)
    _dbg(
        "UPLOAD_ONLY check: upload_only=%s content=%r",
        upload_only,
        (message.content or "")
    )

    if upload_only:
        cmds = _commands_allowing_upload_only()
        _dbg("UPLOAD_ONLY eligible commands=%s", cmds)

        fired_any = False

        for command in cmds:
            if not is_channel_allowed(command, message.channel.id, silent=True):
                _dbg("UPLOAD_ONLY skip cmd=%s reason=channel_not_allowed", command)
                continue

            if not is_user_allowed(command, message.author.id, silent=True):
                _dbg("UPLOAD_ONLY skip cmd=%s reason=user_not_allowed", command)
                continue

            fired_any = True
            _dbg("UPLOAD_ONLY FIRE cmd=%s", command)

            payload = build_payload(
                event_type="command",
                command=command,
                args=[],
                raw=f"[upload-only] {command}",
                guild=message.guild,
                channel=message.channel,
                user=message.author,
                message_id=message.id,
            )
            
            log.info(f"📤 User '{message.author.display_name}' triggered upload-only command '{command}' with {len(message.attachments)} file(s)")

            await _fanout_attachments_to_command(message, command, payload)
            return

        if not fired_any:
            _dbg("UPLOAD_ONLY no commands fired (all skipped).")
            return
        
    # ----------------------------
    # TYPED COMMAND ROUTES (!weather now, !fitbit sleep, !ai + attachment)
    # ----------------------------
    content = (message.content or "").strip()
    if not content.startswith(COMMAND_PREFIX):
        return

    parts = content[len(COMMAND_PREFIX):].strip().split()
    if not parts:
        return

    command = parts[0].lower()
    args = parts[1:]

    # ✅ SMART UNKNOWN COMMAND ERROR
    if command not in COMMANDS:
        available_cmds = [
            cmd for cmd in COMMANDS 
            if is_channel_allowed(cmd, message.channel.id, silent=True) 
            and is_user_allowed(cmd, message.author.id, silent=True)
        ]
        
        if not available_cmds:
            log.warning(f"❓ Unknown command '{command}' from {message.author.display_name} - SILENCED (No routes active in this channel)")
            return

        if str(message.channel.id) in DISPLAY_UNKNOWN_COMMAND_ERROR_SILENT_CHANNELS:
            log.warning(f"❓ Unknown command '{command}' from {message.author.display_name} - SILENCED (Channel is in silent list)")
            return

        if DISPLAY_UNKNOWN_COMMAND_ERROR:
            log.warning(f"❓ Unknown command '{command}' from {message.author.display_name} - REPLIED with help list")
            cmd_list = ", ".join(f"`{COMMAND_PREFIX}{c}`" for c in sorted(available_cmds))
            await message.reply(f"❌ Unknown command `{COMMAND_PREFIX}{command}`.\n**Available commands here:** {cmd_list}")
                
        return
    if not is_channel_allowed(command, message.channel.id):
        await message.reply("⛔ Not allowed in this channel.")
        return

    if not is_user_allowed(command, message.author.id):
        await message.reply("⛔ Not allowed for your user.")
        return

    payload = build_payload(
        event_type="command",
        command=command,
        args=args,
        raw=content,
        guild=message.guild,
        channel=message.channel,
        user=message.author,
        message_id=message.id,
    )

    cfg = _get_cmd_cfg(command)
    if cfg.get("accept_attachments") and message.attachments:
        log.info(f"📤 User '{message.author.display_name}' triggered command '{command}' with {len(message.attachments)} file(s)")
        await _fanout_attachments_to_command(message, command, payload)
        return
    
    log.info(f"⚡ User '{message.author.display_name}' triggered command '{command}' in channel {message.channel.id}")

    try:
        data = await post_to_webhook_async(command, payload)
        await send_reply(message.channel, data)
    except Exception as e:
        log.error(f"⚠️ Exception triggering command '{command}': {e}", exc_info=True)
        await message.reply(f"⚠️ Trigger failed: {type(e).__name__}: {e}")


# ---- persistence scheduler state ----
PANEL_PERSIST_LAST: dict[str, float] = {}  # key: f"{channel_id}:{panel_name}"

@tasks.loop(seconds=5)
async def panel_persist_loop():
    await bot.wait_until_ready()
    if not bot.user:
        return

    now_ts = datetime.now().timestamp()

    for panel_name, panel_cfg in PANELS.items():
        enabled, interval, _cleanup = _panel_persist_cfg(panel_cfg)
        if not enabled:
            continue

        for channel_id in (panel_cfg.get("channels") or[]):
            try:
                cid = int(channel_id)
            except Exception:
                continue

            key = f"{cid}:{panel_name}"
            last = PANEL_PERSIST_LAST.get(key, 0.0)
            if (now_ts - last) < interval:
                continue

            channel = bot.get_channel(cid)
            if channel is None:
                try:
                    channel = await bot.fetch_channel(cid)
                except Exception:
                    continue

            try:
                await _persist_panel_once(panel_name, channel, panel_cfg)
            except Exception as e:
                log.error(f"⚠️ Error persisting panel '{panel_name}' in channel {cid}: {e}", exc_info=True)

            PANEL_PERSIST_LAST[key] = now_ts

# ----------------------------
# MAIN
# ----------------------------
def main():
    if not DISCORD_TOKEN:
        log.error("❌ DISCORD_TOKEN is missing. Please check your .env file.")
        return
        
    try:
        bot.run(DISCORD_TOKEN, log_handler=None)
    except discord.LoginFailure:
        log.error("❌ Failed to log in. Your DISCORD_TOKEN is invalid or expired.")
    except Exception as e:
        log.critical(f"❌ Fatal error starting bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()