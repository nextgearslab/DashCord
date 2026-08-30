import os
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio

import base64
import re
from typing import Any
from datetime import timezone

import aiohttp
import time
from dotenv import load_dotenv

from aiohttp import web

import discord
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands


import logging
BOT_STARTED_AT_UTC = datetime.now(timezone.utc)  # module load time (safe default)

def get_env_bool(key: str, default: str = "false") -> bool:
    """Helper to parse boolean environment variables."""
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes", "y", "on")

def parse_bool(val: Any, default: bool = False) -> bool:
    """Helper to parse mixed bool/string values from JSON or configs."""
    if val is None: return default
    if isinstance(val, bool): return val
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")


DASHCORD_DEBUG = get_env_bool("DASHCORD_DEBUG", "false") 

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

# ------------------------------------------------------------------------------
# LOAD ENV & ESTABLISH FALLBACKS
# ------------------------------------------------------------------------------
load_dotenv()
load_dotenv("secrets.env", override=True)

# 🤖 Core Discord Bot Settings
DISCORD_TOKEN  = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
TIMEZONE       = os.getenv("TIMEZONE", "America/New_York")

# 📁 Storage & Configuration Paths
ROUTES_PATH         = os.getenv("ROUTES_PATH", os.path.join(BASE_DIR, "routes.json"))
DYNAMIC_ROUTES_PATH = os.getenv("DYNAMIC_ROUTES_PATH", os.path.join(BASE_DIR, "config/dynamic_routes.json"))

# ⚙️ Chat Commands & Helper Settings
DISPLAY_UNKNOWN_COMMAND_ERROR = get_env_bool("DISPLAY_UNKNOWN_COMMAND_ERROR", "true")
DISPLAY_UNKNOWN_COMMAND_ERROR_SILENT_CHANNELS = set(
    cid.strip() for cid in os.getenv("DISPLAY_UNKNOWN_COMMAND_ERROR_SILENT_CHANNELS", "").split(",") if cid.strip()
)

# 🎭 Chat Command Reactions (⏳, ✅, ❌ on typed user messages)
COMMAND_REACTION_ENABLED        = get_env_bool("COMMAND_REACTION_ENABLED", "true")
COMMAND_REACTION_PENDING        = os.getenv("COMMAND_REACTION_PENDING", "⏳")
COMMAND_REACTION_SUCCESS        = os.getenv("COMMAND_REACTION_SUCCESS", "✅")
COMMAND_REACTION_FAIL           = os.getenv("COMMAND_REACTION_FAIL", "❌")
COMMAND_LOADING_MESSAGE_ENABLED = get_env_bool("COMMAND_LOADING_MESSAGE_ENABLED", "false")
COMMAND_LOADING_MESSAGE_TEXT    = os.getenv("COMMAND_LOADING_MESSAGE_TEXT", "⏳ Processing `{command}`...")
COMMAND_SHOW_ELAPSED_TIME       = get_env_bool("COMMAND_SHOW_ELAPSED_TIME", "false")
COMMAND_REPLY_TO_MESSAGE        = get_env_bool("COMMAND_REPLY_TO_MESSAGE", "true")

# 🎛️ Panel Interaction & Behavior Baselines
PANEL_SHOW_TITLE_DEFAULT       = get_env_bool("PANEL_SHOW_TITLE_DEFAULT", "true")
PANEL_REPOST_ON_STARTUP        = get_env_bool("PANEL_REPOST_ON_STARTUP", "true")
PANEL_SPAWN_NEW_ON_CLICK       = get_env_bool("PANEL_SPAWN_NEW_ON_CLICK", "true")
PANEL_ARCHIVE_DISABLE_BUTTONS  = get_env_bool("PANEL_ARCHIVE_DISABLE_BUTTONS", "true")
PANEL_FORCE_NEW_ON_STARTUP     = get_env_bool("PANEL_FORCE_NEW_ON_STARTUP", "true")

# 🎨 Panel Status Lines & Emojis
PANEL_STATUS_LINE           = get_env_bool("PANEL_STATUS_LINE", "true")
PANEL_STATUS_EMOJI_PENDING  = os.getenv("PANEL_STATUS_EMOJI_PENDING", "⏳")
PANEL_STATUS_EMOJI_SUCCESS  = os.getenv("PANEL_STATUS_EMOJI_SUCCESS", "✅")
PANEL_STATUS_EMOJI_FAIL     = os.getenv("PANEL_STATUS_EMOJI_FAIL", "❌")
PANEL_STATUS_EMOJI_IN_EMBED = get_env_bool("PANEL_STATUS_EMOJI_IN_EMBED", "true")
PANEL_STATUS_EMOJI_TITLE    = get_env_bool("PANEL_STATUS_EMOJI_TITLE", "true")

# ⏱️ Panel Status Animations & Elapsed Timers
PANEL_STATUS_ANIMATE_PENDING   = get_env_bool("PANEL_STATUS_ANIMATE_PENDING", "false")
PANEL_STATUS_EMOJI_PENDING_ALT = os.getenv("PANEL_STATUS_EMOJI_PENDING_ALT", "⌛")
PANEL_STATUS_ANIMATE_INTERVAL  = float(os.getenv("PANEL_STATUS_ANIMATE_INTERVAL", "1.5"))
PANEL_STATUS_SHOW_ELAPSED      = get_env_bool("PANEL_STATUS_SHOW_ELAPSED", "true")
PANEL_STATUS_ANIMATE_ELAPSED   = get_env_bool("PANEL_STATUS_ANIMATE_ELAPSED", "true")

# 🧹 Panel Cleanup & History Scan Limits
PANEL_DELETE_OLD_PANELS = get_env_bool("PANEL_DELETE_OLD_PANELS", "true")
PANEL_SCAN_LIMIT        = int(os.getenv("PANEL_SCAN_LIMIT", "50"))

# 🏃 Sticky UI / Panel Persistence Loop
PANEL_PERSIST_DEFAULT            = get_env_bool("PANEL_PERSIST_DEFAULT", "false")
PANEL_PERSIST_INTERVAL_SECONDS   = int(os.getenv("PANEL_PERSIST_INTERVAL_SECONDS", "45"))
PANEL_PERSIST_ON_RESPONSE        = get_env_bool("PANEL_PERSIST_ON_RESPONSE", "true")
PANEL_PERSIST_ON_RESPONSE_DELAY  = float(os.getenv("PANEL_PERSIST_ON_RESPONSE_DELAY", "0"))
PANEL_PERSIST_CLEANUP_OLD_ACTIVE = get_env_bool("PANEL_PERSIST_CLEANUP_OLD_ACTIVE", "true")

# 📡 Programmatic REST API Server Settings
API_ENABLED                 = get_env_bool("API_ENABLED", "false")
API_PORT                    = int(os.getenv("API_PORT", "8080"))
API_ALLOW_STATIC_OVERWRITE  = get_env_bool("API_ALLOW_STATIC_OVERWRITE", "false")

# 🌐 Webhook Connectivity & Advanced Security
DASHCORD_SHARED_SECRET = os.getenv("DASHCORD_SHARED_SECRET", "")
HTTP_TIMEOUT_SECONDS   = float(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
VERIFY_TLS             = get_env_bool("VERIFY_TLS", "true")

# 🐞 Troubleshooting & Logging Controls
DEBUG_WEBHOOK  = get_env_bool("DEBUG_WEBHOOK", "false")

# channel_id -> { panel_name -> message_id }
PANEL_STATE: dict[str, dict[str, str]] = {}

# channel_id -> { panel_name -> active_message_id }
PANEL_ACTIVE: dict[str, dict[str, str]] = {}

AIOHTTP_SESSION: aiohttp.ClientSession | None = None


# ----------------------------
# LOAD ROUTES.JSON & DYNAMIC ROUTES
# ----------------------------
if not os.path.exists(ROUTES_PATH):
    raise RuntimeError(f"routes.json not found at: {ROUTES_PATH}")

with open(ROUTES_PATH, "r", encoding="utf-8") as f:
    ROUTES = json.load(f)
    
STATIC_COMMANDS = ROUTES.get("commands", {}) or {}
STATIC_PANELS = ROUTES.get("panels", {}) or {}

DYNAMIC_COMMANDS = {}
DYNAMIC_PANELS = {}

if os.path.exists(DYNAMIC_ROUTES_PATH):
    try:
        with open(DYNAMIC_ROUTES_PATH, "r", encoding="utf-8") as f:
            dyn = json.load(f)
            DYNAMIC_COMMANDS = dyn.get("commands", {}) or {}
            DYNAMIC_PANELS = dyn.get("panels", {}) or {}
            log.info(f"Loaded {len(DYNAMIC_COMMANDS)} dynamic commands and {len(DYNAMIC_PANELS)} dynamic panels.")
    except Exception as e:
        log.error(f"Failed to load dynamic routes from {DYNAMIC_ROUTES_PATH}: {e}")
else:
    _dbg("No dynamic routes configuration file found at: %s. Starting with static configuration only.", DYNAMIC_ROUTES_PATH)

# Merged active states
COMMANDS = {**STATIC_COMMANDS, **DYNAMIC_COMMANDS}
PANELS   = {**STATIC_PANELS, **DYNAMIC_PANELS}

def _save_dynamic_routes():
    try:
        data = {
            "commands": DYNAMIC_COMMANDS,
            "panels": DYNAMIC_PANELS
        }
        with open(DYNAMIC_ROUTES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.error(f"⚠️ Failed to save dynamic routes: {e}")

log.info(f"BOOT routes={ROUTES_PATH} prefix={COMMAND_PREFIX!r} cmds={sorted(COMMANDS.keys())}")

# ----------------------------
# HELPERS
# ----------------------------

async def _send_chunked(sender_func, content: str, fallback_sender_func=None, **kwargs):
    """Helper to split >2000 char messages cleanly at newlines/spaces, preserving codeblocks and leading spaces."""
    if not content:
        if kwargs:
            await sender_func(content=None, **kwargs)
        return

    MAX_LEN = 1900
    chunks = []
    current_chunk = ""
    in_code_block = False
    code_block_lang = ""

    def get_ending_state(s, start_state, start_lang):
        state = start_state
        lang = start_lang
        for line in s.split('\n'):
            t_line = line.lstrip()
            if t_line.startswith("```"):
                if state:
                    state = False
                    lang = ""
                else:
                    state = True
                    lang = t_line[3:].strip()
        return state, lang

    sections = content.split('\n\n')

    for i, section in enumerate(sections):
        will_be_in_cb, new_lang = get_ending_state(section, in_code_block, code_block_lang)
        closing_allowance = 4 if will_be_in_cb else 0
        separator_len = 2 if current_chunk else 0

        if len(current_chunk) + separator_len + len(section) + closing_allowance <= MAX_LEN:
            if current_chunk:
                current_chunk += '\n\n' + section
            else:
                if in_code_block and not section.lstrip().startswith("```"):
                    current_chunk = f"```{code_block_lang}\n{section}"
                else:
                    current_chunk = section
            in_code_block = will_be_in_cb
            code_block_lang = new_lang
        else:
            # If the section doesn't fit in the CURRENT message, but IT DOES fit in a BRAND NEW message
            prefix_for_new = f"```{code_block_lang}\n" if (in_code_block and not section.lstrip().startswith("```")) else ""
            
            if len(prefix_for_new) + len(section) + closing_allowance <= MAX_LEN:
                if current_chunk:
                    if in_code_block:
                        current_chunk = current_chunk.rstrip() + "\n```"
                    chunks.append(current_chunk.lstrip('\n').rstrip() + '\n\u200b')
                current_chunk = prefix_for_new + section
                in_code_block = will_be_in_cb
                code_block_lang = new_lang
            else:
                # If the block ITSELF is > MAX_LEN chars, fall back to line-by-line chopping.
                lines = section.split('\n')
                for j, line in enumerate(lines):
                    t_line = line.lstrip()
                    is_toggle = t_line.startswith("```")

                    line_will_be_in_cb = in_code_block
                    line_new_lang = code_block_lang

                    if is_toggle:
                        if in_code_block:
                            line_will_be_in_cb = False
                            line_new_lang = ""
                        else:
                            line_will_be_in_cb = True
                            line_new_lang = t_line[3:].strip()

                    line_closing_allowance = 4 if line_will_be_in_cb else 0
                    line_sep = ('\n\n' if j == 0 else '\n') if current_chunk else ''
                    line_sep_len = len(line_sep)

                    if len(current_chunk) + line_sep_len + len(line) + line_closing_allowance <= MAX_LEN:
                        if current_chunk:
                            current_chunk += line_sep + line
                        else:
                            if in_code_block and not is_toggle:
                                current_chunk = f"```{code_block_lang}\n{line}"
                            elif in_code_block and is_toggle and t_line.rstrip() == "```":
                                current_chunk = ""
                            else:
                                current_chunk = line
                        in_code_block = line_will_be_in_cb
                        code_block_lang = line_new_lang
                    else:
                        if current_chunk:
                            if in_code_block:
                                current_chunk = current_chunk.rstrip() + "\n```"
                            chunks.append(current_chunk.lstrip('\n').rstrip() + '\n\u200b')
                            current_chunk = ""

                        if len(line) + line_closing_allowance <= MAX_LEN:
                            if in_code_block and not is_toggle:
                                current_chunk = f"```{code_block_lang}\n{line}"
                            elif in_code_block and is_toggle and t_line.rstrip() == "```":
                                current_chunk = ""
                            else:
                                current_chunk = line
                            in_code_block = line_will_be_in_cb
                            code_block_lang = line_new_lang
                        else:
                            remaining_line = line
                            prefix = f"```{code_block_lang}\n" if (in_code_block and not is_toggle) else ""

                            while len(remaining_line) > 0:
                                allowance = 4 if line_will_be_in_cb else 0
                                space_left = MAX_LEN - len(prefix) - allowance - 1
                                if space_left <= 0: space_left = 1

                                part = remaining_line[:space_left]
                                remaining_line = remaining_line[space_left:]

                                if len(remaining_line) > 0:
                                    chunk_to_push = prefix + part
                                    if line_will_be_in_cb: chunk_to_push += "\n```"
                                    chunks.append(chunk_to_push.lstrip('\n').rstrip() + '\n\u200b')
                                    prefix = f"```{line_new_lang}\n" if line_will_be_in_cb else ""
                                else:
                                    current_chunk = prefix + part

                            in_code_block = line_will_be_in_cb
                            code_block_lang = line_new_lang

    if current_chunk:
        if in_code_block and not current_chunk.rstrip().endswith("```"):
            current_chunk = current_chunk.rstrip() + "\n```"
        chunks.append(current_chunk.lstrip('\n').rstrip())

    # If the chunk begins with whitespace, prepend a zero-width space so Discord doesn't strip it.
    final_chunks = []
    for chunk in chunks:
        if chunk.startswith((" ", "\t")):
            chunk = '\u200B' + chunk
        final_chunks.append(chunk)

    for i, chunk in enumerate(final_chunks):
        is_last = (i == len(final_chunks) - 1)
        
        # Only pass embeds, views, and non-ephemeral kwargs to the final chunk
        passthrough = {}
        for k, v in kwargs.items():
            if is_last or k == "ephemeral":
                passthrough[k] = v

        current_sender = sender_func
        
        # For chunk 2+, if a fallback is provided and the message is NOT ephemeral, route as standard message
        # (Ephemeral messages MUST be sent via interaction followups)
        if i > 0 and fallback_sender_func and not kwargs.get("ephemeral"):
            current_sender = fallback_sender_func
            passthrough.pop("ephemeral", None) # Standard channel.send doesn't accept ephemeral argument

        try:
            await current_sender(content=chunk, **passthrough)
        except discord.Forbidden:
            # If standard channel.send fails due to permission locks, silently fallback to interaction webhook
            if current_sender != sender_func:
                if "ephemeral" in kwargs:
                    passthrough["ephemeral"] = kwargs["ephemeral"]
                await sender_func(content=chunk, **passthrough)
            else:
                _dbg("Forbidden error sending chunk %d", i)


async def _add_reaction_safe(message: discord.Message, emoji: str) -> None:
    if not COMMAND_REACTION_ENABLED:
        return
    try:
        await message.add_reaction(emoji)
    except Exception as e:
        _dbg("Could not add reaction %s to message %s: %s", emoji, message.id, e)

async def _remove_reaction_safe(message: discord.Message, emoji: str) -> None:
    if not COMMAND_REACTION_ENABLED or not bot.user:
        return
    try:
        await message.remove_reaction(emoji, bot.user)
    except Exception as e:
        _dbg("Could not remove reaction %s from message %s: %s", emoji, message.id, e)

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
        try:
            obj, end = dec.raw_decode(text, i)
        except Exception:
            return False
        if not isinstance(obj, dict):
            return False
        found += 1
        i = end

    return found > 0

def _clone_payload(payload: dict) -> dict:
    return json.loads(json.dumps(payload))

def _deep_update(d, u):
    """Deep merges dict 'u' into dict 'd' safely."""
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v)
        else:
            d[k] = v
    return d

async def _fanout_attachments_to_command(message: discord.Message, command: str, base_payload: dict) -> None:
    cfg = _get_cmd_cfg(command)
    rules = cfg.get("attachment_rules") or {}
    exts = rules.get("extensions") or []
    
    fanout = rules.get("fanout", True)
    
    atts = _find_matching_attachments(message, exts)

    if not atts:
        want = ", ".join(exts) if exts else "any file"
        got = ", ".join([a.filename for a in (message.attachments or [])]) or "(none)"

        log.warning(f"⚠️ User uploaded wrong file type for command '{command}'. Expected: {want}, Got: {got}")
        await message.reply(f"❌ No matching attachment found. Expected: {want}. Got: {got}")
        return

    await _add_reaction_safe(message, COMMAND_REACTION_PENDING)

    total = len(atts)
    ok = 0
    bad = 0
    bad_lines: list[str] = []

    if fanout:
        # ==========================================
        # FAN-OUT (1 webhook per file)
        # ==========================================
        log.info(f"📤 Ingesting file batch: starting fan-out for {total} file(s) on command '{command}'...")

        for index, att in enumerate(atts, start=1):
            p = _clone_payload(base_payload)
            handled, err = await _ingest_specific_attachment(att, command, p)
            if handled and err:
                bad += 1
                bad_lines.append(err)
                log.warning(f"⚠️ [{index}/{total}] Attachment '{att.filename}' rejected: {err}")
                continue

            try:
                _dbg("Webhook call start cmd=%s att=%s", command, att.filename)
                data = await post_to_webhook_async(command, p)
                _dbg("Webhook call end cmd=%s att=%s", command, att.filename)

                if (data or {}).get("ok"):
                    ok += 1
                    _dbg("[%d/%d] Attachment '%s' processed successfully by webhook.", index, total, att.filename)
                else:
                    bad += 1
                    msg = ((data or {}).get("reply") or {}).get("content") or "unknown error"
                    bad_lines.append(f"❌ `{att.filename}`: {msg[:200]}")
                    log.warning(f"⚠️ [{index}/{total}] Webhook rejected file '{att.filename}': {msg[:100]}")
            except Exception as e:
                bad += 1
                bad_lines.append(f"❌ `{att.filename}`: {type(e).__name__}: {e}")
                log.error(f"⚠️ [{index}/{total}] Failed to post file '{att.filename}': {e}", exc_info=True)

        log.info(f"📤 File batch complete for command '{command}': {ok} succeeded, {bad} failed.")

    else:
        # ==========================================
        # BATCH (All files in 1 webhook)
        # ==========================================
        log.info(f"📤 Ingesting file batch: sending {total} file(s) as a single payload for command '{command}'...")
        
        p = _clone_payload(base_payload)
        p["attachments"] = [] # Create an array for our files
        
        ok_ingest = 0
        for index, att in enumerate(atts, start=1):
            # Use a temporary dict so _ingest_specific_attachment doesn't overwrite root keys
            temp_p = {"discord": p.get("discord", {})}
            handled, err = await _ingest_specific_attachment(att, command, temp_p)
            
            if handled and err:
                bad += 1
                bad_lines.append(err)
                log.warning(f"⚠️ [{index}/{total}] Attachment '{att.filename}' rejected: {err}")
                continue
                
            # Append the extracted metadata to our batch array
            p["attachments"].append({
                "attachment": temp_p.get("attachment"),
                "attachment_text": temp_p.get("attachment_text"),
                "attachment_bytes_len": temp_p.get("attachment_bytes_len"),
                "attachment_b64": temp_p.get("attachment_b64"),
                "source_meta_b64": temp_p.get("source_meta_b64")
            })
            ok_ingest += 1

        if ok_ingest > 0:
            try:
                data = await post_to_webhook_async(command, p)
                if (data or {}).get("ok"):
                    ok = total # Mark all ingested files as successful
                else:
                    bad += ok_ingest # Mark all as failed if the webhook rejects the batch
                    msg = ((data or {}).get("reply") or {}).get("content") or "unknown error"
                    bad_lines.append(f"❌ Webhook batch rejection: {msg[:200]}")
            except Exception as e:
                bad += ok_ingest
                bad_lines.append(f"❌ Webhook batch exception: {type(e).__name__}: {e}")
                log.error(f"⚠️ Failed to post batch payload: {e}", exc_info=True)

        log.info(f"📤 Batch payload complete for command '{command}': {ok} files processed, {bad} failed.")

    # ----------------------------
    # routes-driven attachment reply policy
    # ----------------------------
    reply_cfg = cfg.get("attachment_reply") or {}
    if not isinstance(reply_cfg, dict):
        reply_cfg = {}

    mode = str(reply_cfg.get("mode", "errors")).strip().lower()
    if mode not in ("none", "errors", "always"):
        mode = "errors"

    has_errors = (bad > 0)

    await _remove_reaction_safe(message, COMMAND_REACTION_PENDING)
    if has_errors:
        await _add_reaction_safe(message, COMMAND_REACTION_FAIL)
    elif ok > 0:
        await _add_reaction_safe(message, COMMAND_REACTION_SUCCESS)

    should_reply = (
        (mode == "always") or
        (mode == "errors" and has_errors)
    )
    if not should_reply:
        return

    success_tpl = str(reply_cfg.get("success_template", "📦 Uploaded {ok}/{total} file(s).")).strip()
    error_tpl   = str(reply_cfg.get("error_template", "❌ Upload errors ({bad}/{total}):\n{errors}")).strip()

    errors_text = "\n".join(bad_lines[:6]).strip()

    if has_errors:
        msg = error_tpl.format(ok=ok, bad=bad, total=total, errors=errors_text)
    else:
        msg = success_tpl.format(ok=ok, bad=bad, total=total, errors="")

    msg = (msg or "").strip()
    if msg:
        await _send_chunked(message.reply, msg, fallback_sender_func=message.channel.send)

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
    if not command:
        return {}
    cfg = COMMANDS.get(command) or COMMANDS.get(command.lower()) or {}
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


def _render_template(tpl: Any, context: dict) -> Any:
    """
    Replace {{...}} placeholders inside strings, recursively.
    Supports dot-path lookups like {{data.0.logs}} and preserves native types for exact matches.
    """
    if isinstance(tpl, str):
        # If the string is EXACTLY a single placeholder (e.g. "{{discord.user_roles}}"), preserve native data type
        exact_match = re.fullmatch(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}", tpl)
        if exact_match:
            key = exact_match.group(1).strip()
            cur: Any = context
            found = True
            for part in key.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                    cur = cur[int(part)]
                else:
                    found = False
                    break
            if found:
                return cur

        def repl(m: re.Match) -> str:
            key = m.group(1).strip()
            cur: Any = context
            for part in key.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                    cur = cur[int(part)]
                else:
                    _dbg("⚠️ Placeholder lookup: key '%s' not found in context.", key)
                    cur = ""
                    break
            if isinstance(cur, (dict, list)):
                return json.dumps(cur, ensure_ascii=False)
            return str(cur)

        return re.sub(r"\{\{(.+?)\}\}", repl, tpl)

    elif isinstance(tpl, dict):
        return {k: _render_template(v, context) for k, v in tpl.items()}
    elif isinstance(tpl, list):
        return [_render_template(item, context) for item in tpl]
    else:
        return tpl
    
def _panel_persist_cfg(panel_cfg: dict) -> tuple[bool, int, bool]:
    p = panel_cfg.get("persist") if isinstance(panel_cfg, dict) else None
    if not isinstance(p, dict):
        return (PANEL_PERSIST_DEFAULT, PANEL_PERSIST_INTERVAL_SECONDS, PANEL_PERSIST_CLEANUP_OLD_ACTIVE)

    enabled = p.get("enabled", PANEL_PERSIST_DEFAULT)
    interval = int(p.get("interval_seconds", PANEL_PERSIST_INTERVAL_SECONDS))
    cleanup = p.get("cleanup_old_active", PANEL_PERSIST_CLEANUP_OLD_ACTIVE)

    if isinstance(enabled, str):
        enabled = enabled.strip().lower() in ("1", "true", "yes", "y", "on")
    else:
        enabled = bool(enabled)
        
    if isinstance(cleanup, str):
        cleanup = cleanup.strip().lower() in ("1", "true", "yes", "y", "on")
    else:
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

    # SAFETY NET: If we don't know the active panel, try to find it first (prevents blind duplication)
    if active_id is None:
        existing = await _find_existing_panel_message(channel, panel_name)
        if existing:
            active_id = existing.id
            _set_active_panel_msg_id(channel.id, panel_name, active_id)

    # If our active panel is already last, do nothing
    if active_id and last_id == active_id:
        _dbg("Panel '%s' is already at the bottom of channel %s. Skipping move.", panel_name, channel.id)
        return

    log.info(f"🔄 Persistence: Moving panel '{panel_name}' to bottom of channel {channel.id}")

    # Post new panel at bottom
    await _post_panel_to_channel(channel, panel_name, panel_cfg, force_new=True)

    # Cleanup previous active panel so we don't accumulate junk
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

def _is_panel_archived(msg: discord.Message) -> bool:
    """Checks if a panel message has disabled components, marking it as historical/archived."""
    if not msg.components:
        return False
    for action_row in msg.components:
        for child in getattr(action_row, "children", []):
            if getattr(child, "disabled", False):
                return True
    return False

async def _delete_existing_panel_message(channel: discord.abc.Messageable, panel_name: str) -> None:
    if not getattr(channel, "id", None) or not bot.user:
        return

    stored = _get_panel_msg_id(channel.id, panel_name)
    if stored:
        try:
            msg = await channel.fetch_message(int(stored))  # type: ignore[attr-defined]
            if msg and msg.author and msg.author.id == bot.user.id:
                if not _is_panel_archived(msg):
                    await msg.delete()
                    log.info(f"🧹 Cleaned up stored old panel '{panel_name}' in channel {channel.id}")
                    return
        except Exception:
            pass

    try:
        async for msg in channel.history(limit=PANEL_SCAN_LIMIT):  # type: ignore[attr-defined]
            if msg.author and bot.user and msg.author.id == bot.user.id:
                match = False
                if isinstance(msg.content, str) and f"({panel_name})" in msg.content:
                    match = True
                else:
                    for action_row in msg.components:
                        for child in action_row.children:
                            cid = getattr(child, "custom_id", "") or ""
                            if cid.startswith(f"dashcord:btn:{panel_name}:") or cid.startswith(f"dashcord:sel:{panel_name}:"):
                                match = True
                                break
                        if match:
                            break
                
                if match:
                    if _is_panel_archived(msg):
                        continue
                        
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

    # 1. State cache lookup (Fastest, survives edits)
    stored = _get_panel_msg_id(channel.id, panel_name)
    if stored:
        try:
            msg = await channel.fetch_message(int(stored))
            if msg and msg.author and msg.author.id == bot.user.id:
                if not _is_panel_archived(msg):
                    return msg
        except Exception:
            _dbg("⚠️ Cached message ID %s for panel '%s' no longer exists in channel %s. Clearing cache.", stored, panel_name, channel.id)
            pass

    # 2. History scan fallback (Survives bot restarts)
    try:
        async for msg in channel.history(limit=PANEL_SCAN_LIMIT):
            if msg.author and msg.author.id == bot.user.id:
                if _is_panel_archived(msg):
                    continue
                
                # check if it is the panel by seeing if the name is in the content
                if isinstance(msg.content, str) and f"({panel_name})" in msg.content:
                    log.info(f"🔍 Found existing panel '{panel_name}' in channel {channel.id} (via text match). Attaching to it.")
                    _set_panel_msg_id(channel.id, panel_name, msg.id)
                    return msg
                
                # Check components (Buttons/Dropdowns have hidden IDs)
                for action_row in msg.components:
                    for child in action_row.children:
                        cid = getattr(child, "custom_id", "") or ""
                        # If a button or select matches this panel's internal ID
                        if cid.startswith(f"dashcord:btn:{panel_name}:") or cid.startswith(f"dashcord:sel:{panel_name}:"):
                            log.info(f"🔍 Found existing panel '{panel_name}' in channel {channel.id} (via component ID). Attaching to it.")
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
    content, embed = _build_panel_message(panel_name, panel_cfg)
    view = DashPanel(panel_name, panel_cfg)

    if not force_new:
        existing = await _find_existing_panel_message(channel, panel_name)
        if existing:
            try:
                _dbg("Updating existing message ID %s for panel '%s'", existing.id, panel_name)
                await existing.edit(content=content, embed=embed, view=view)
                _set_active_panel_msg_id(channel.id, panel_name, existing.id)
                return
            except Exception as e:
                log.warning(f"⚠️ Found existing panel '{panel_name}' but failed to edit it. Falling back to posting new. Error: {e}")

    log.info(f"🆕 Posting new panel '{panel_name}' to channel {getattr(channel, 'id', 'unknown')}")

    sent = await channel.send(content=content, embed=embed, view=view)
    if getattr(channel, "id", None):
        _set_panel_msg_id(channel.id, panel_name, sent.id)
        _set_active_panel_msg_id(channel.id, panel_name, sent.id)

def now_local_iso() -> str:
    try:
        return datetime.now(ZoneInfo(TIMEZONE)).isoformat()
    except Exception:
        return datetime.now().isoformat()

def resolve_endpoint(command: str) -> str:
    cfg = _get_cmd_cfg(command)
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
    cfg = _get_cmd_cfg(command)
    allowed = cfg.get("allowed_users", [])
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
    cfg = _get_cmd_cfg(command)
    allowed = cfg.get("allowed_channels", [])
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
            "user_roles": [str(r.id) for r in getattr(user, "roles", []) if r.name != "@everyone"],
            "user_role_names": [r.name for r in getattr(user, "roles", []) if r.name != "@everyone"],
            "message_id": str(message_id) if message_id else None,
            "interaction_id": interaction_id,
        },
        "meta": {"timezone": TIMEZONE},
    }

def _resolve_method(command: str) -> str:
    cfg = _get_cmd_cfg(command)
    m = (cfg.get("method") or "POST").strip().upper()
    if m not in ("POST", "GET"):
        raise RuntimeError(f"Invalid method for command '{command}': {m!r} (use POST or GET)")
    return m

async def post_to_webhook_async(command: str, payload: dict) -> dict:
    cfg = COMMANDS.get(command) or {}
    endpoint = resolve_endpoint(command)
    method = _resolve_method(command)

    body_template = cfg.get("body_template")
    out_json = payload
    if body_template is not None:
        out_json = _render_template(body_template, payload)

    headers = {"Content-Type": "application/json"}

    # Dynamically inject User-Specific API Token if available
    discord_user_id = (payload.get("discord") or {}).get("user_id")
    user_token = None
    if discord_user_id:
        user_token = os.getenv(f"USER_TOKEN_{discord_user_id}")

    if user_token:
        headers["Authorization"] = f"Bearer {user_token}"
        log.info(f"🔑 Dynamically injected Personal API Key for Discord ID: {discord_user_id}")
        
        # Preserving X-DashCord-Token for internal legacy/n8n dependencies
        if DASHCORD_SHARED_SECRET:
            headers["X-DashCord-Token"] = DASHCORD_SHARED_SECRET
    elif DASHCORD_SHARED_SECRET:
        headers["X-DashCord-Token"] = DASHCORD_SHARED_SECRET

    custom_headers = cfg.get("headers")
    if isinstance(custom_headers, dict):
        for h_key, h_val in custom_headers.items():
            headers[h_key] = str(h_val)

    async def parse_response(status: int, text: str, resp_headers: dict) -> dict:
        _dbg("WEBHOOK POST cmd=%s status=%s", command, status)

        if DEBUG_WEBHOOK:
            try:
                parsed_json = json.loads(text)
                preview = json.dumps(parsed_json, indent=2)
            except Exception:
                # Provide the full raw string, no truncation
                preview = text

            log.info(
                "\n================ WEBHOOK RESPONSE ================\n"
                f"command: {command}\n"
                f"endpoint: {endpoint}\n"
                f"status: {status}\n"
                f"content-type: {resp_headers.get('Content-Type')}\n"
                f"text_preview:\n{preview}\n"
                "=================================================="
            )

        try:
            data = json.loads(text)
            
            resp_tpl = cfg.get("response_template")
            if resp_tpl:
                context = data if isinstance(data, dict) else {"root": data}
                data = _render_template(resp_tpl, context)

        except Exception as e:
            if 200 <= status < 300 and text.strip():
                log.warning(f"⚠️ Webhook response for '{command}' returned HTTP {status} but was not valid JSON. Falling back to plain text reply.")
            data = None

        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            data = data[0]

        if isinstance(data, dict) and isinstance(data.get("response"), dict):
            data = data["response"]

        if not isinstance(data, dict):
            data = {"ok": (200 <= status < 300), "reply": {"content": text}}

        # Normalize error responses (Removed truncation here as well)
        if not (200 <= status < 300):
            log.warning(f"❌ Webhook Error [{command}]: HTTP {status} - {text}")
            data["ok"] = False
            data.setdefault("reply", {})
            if not isinstance(data["reply"], dict):
                data["reply"] = {"content": str(data["reply"])}
            data["reply"].setdefault("content", f"Webhook HTTP {status}: {text}")

        data.setdefault("reply", {})
        if not isinstance(data["reply"], dict):
            data["reply"] = {"content": str(data["reply"])}

        if "stdout" in data and not data["reply"].get("content"):
            stdout_str = str(data["stdout"]).strip()
            if stdout_str:
                data["reply"]["content"] = f"```\n{stdout_str}\n```"
                
        if DEBUG_WEBHOOK:
            reply_obj = data.get("reply")
            is_dict = isinstance(reply_obj, dict)
            reply_keys = list(reply_obj.keys()) if is_dict else None
            c = reply_obj.get("content") if is_dict else None
            c_len = len(c) if isinstance(c, str) else None
            c_preview = c.replace("\n", "\\n") if isinstance(c, str) else None # Removed truncation

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

    t0 = time.monotonic()
    _dbg("WEBHOOK request cmd=%s method=%s endpoint=%s timeout=%s verify_tls=%s",
         command, method, endpoint, HTTP_TIMEOUT_SECONDS, VERIFY_TLS)

    custom_timeout = float(cfg.get("timeout", HTTP_TIMEOUT_SECONDS))
    timeout = aiohttp.ClientTimeout(total=custom_timeout)
    
    global AIOHTTP_SESSION
    session = AIOHTTP_SESSION
    close_session = False
    
    # Fallback if somehow called before setup_hook initializes the global session
    if session is None:
        session = aiohttp.ClientSession(timeout=timeout)
        close_session = True

    try:
        if method == "POST":
            async with session.post(endpoint, headers=headers, json=out_json, ssl=VERIFY_TLS, timeout=timeout) as r:
                text = await r.text()
                _dbg("WEBHOOK response cmd=%s status=%s elapsed=%.2fs", command, r.status, time.monotonic() - t0)

                # missing POST route fallback to GET
                if r.status == 404 and "not registered for POST requests" in text:
                    async with session.get(endpoint, headers=headers, params={"payload": json.dumps(out_json, separators=(",", ":"))}, ssl=VERIFY_TLS, timeout=timeout) as r2:
                        text2 = await r2.text()
                        return await parse_response(r2.status, text2, dict(r2.headers))
                
                return await parse_response(r.status, text, dict(r.headers))

        else: # GET method
            async with session.get(endpoint, headers=headers, params={"payload": json.dumps(out_json, separators=(",", ":"))}, ssl=VERIFY_TLS, timeout=timeout) as r:
                text = await r.text()
                _dbg("WEBHOOK response cmd=%s status=%s elapsed=%.2fs", command, r.status, time.monotonic() - t0)
                return await parse_response(r.status, text, dict(r.headers))
                
    except Exception as e:
        log.error(f"⚠️ Webhook Exception cmd={command}: {e}")
        raise
    finally:
        if close_session:
            await session.close()
            
async def send_reply(channel: discord.abc.Messageable, data: dict) -> None:
    reply = (data or {}).get("reply") or {}
    if not isinstance(reply, dict):
        reply = {"content": str(reply)}

    # honor suppress flag (support both spellings)
    suppress = parse_bool(reply.get("suppress") or reply.get("supress"))
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

    await _send_chunked(channel.send, content, embeds=embeds)

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

def _build_panel_message(panel_name: str, panel_cfg: dict) -> tuple[str | None, discord.Embed | None]:
    """Generates the content and Embed for a panel based on its config."""
    
    # 1. Determine if we show the DashCord Title Header
    # Priority: 1. panel config override, 2. global env default
    show_title = panel_cfg.get("show_title", PANEL_SHOW_TITLE_DEFAULT)
    
    parts = []
    
    # Add the Title Header if enabled
    if show_title:
        parts.append(f"🧩 **DashCord Panel** ({panel_name})")
        
    # Add Custom Content from routes.json if it exists
    custom_content = panel_cfg.get("content")
    if custom_content:
        parts.append(str(custom_content).strip())
        
    # Join them with a newline (or None if both are empty)
    content = "\n".join(parts) if parts else None
    
    # 2. Build the Embed (standard logic)
    embed_cfg = panel_cfg.get("embed")
    embed = None
    if isinstance(embed_cfg, dict):
        color_hex = str(embed_cfg.get("color", "0x2b2d31")).replace("#", "0x")
        embed = discord.Embed(
            title=embed_cfg.get("title", f"Panel: {panel_name}"),
            description=embed_cfg.get("description", ""),
            color=int(color_hex, 16)
        )
        if embed_cfg.get("thumbnail"):
            embed.set_thumbnail(url=embed_cfg.get("thumbnail"))
        if embed_cfg.get("image"):
            embed.set_image(url=embed_cfg.get("image"))
            
    # 3. Emergency Fallback: Discord rejects empty messages
    if not content and not embed:
        content = f"🧩 **DashCord Panel** ({panel_name})"
        
    return content, embed

def trigger_immediate_persist(channel_id: int):
    """Resets the timer so the background loop moves the panel immediately."""
    if not PANEL_PERSIST_ON_RESPONSE:
        return

    for panel_name, panel_cfg in PANELS.items():
        if str(channel_id) in [str(c) for c in (panel_cfg.get("channels") or [])]:
            key = f"{channel_id}:{panel_name}"
            log.info(f"🔄 Queuing immediate persistence check for panel '{panel_name}' in channel {channel_id}...")
            PANEL_PERSIST_LAST[key] = 0  # Set to 0 so the 5-second loop picks it up NOW

async def _delayed_persist(channel_id: int, delay: float):
    """Waits for X seconds before triggering a persist (fixes n8n async race conditions)."""
    log.info(f"⏳ Scheduling delayed panel persistence in channel {channel_id} (delay: {delay}s)...")
    await asyncio.sleep(delay)
    log.info(f"⏳ Delay finished for channel {channel_id}. Activating persistence check.")
    trigger_immediate_persist(channel_id)

async def _animate_pending_message(msg: discord.Message, base_content: str | None, base_embed: discord.Embed | None, archived_view: discord.ui.View, start_time: float, opts: dict):
    """Animates a pending panel message by alternating emojis and/or ticking up an elapsed timer."""
    
    if not opts.get("animate_pending_emoji") and not opts.get("animate_elapsed_time"):
        return

    emoji1 = opts.get("emoji_pending")
    emoji2 = opts.get("emoji_pending_alt")
    current_emoji = emoji1

    try:
        while True:
            await asyncio.sleep(PANEL_STATUS_ANIMATE_INTERVAL)
            
            anim_content = base_content
            anim_embed = base_embed.copy() if base_embed else None
            
            # 1. Handle Emoji Swap Animation
            if opts.get("animate_pending_emoji"):
                current_emoji = emoji2 if current_emoji == emoji1 else emoji1

                # Swap status line text
                if anim_content and opts.get("show_status_line") and opts.get("emoji_in_status_line"):
                    target = f"{emoji1} Last:"
                    if target in anim_content:
                        anim_content = anim_content.replace(target, f"{current_emoji} Last:")
                
                # Swap embed title
                if anim_embed and opts.get("emoji_in_embed_title"):
                    title = anim_embed.title or ""
                    if title.endswith(f" {emoji1}"):
                        title = title[:-len(emoji1)-1]
                    elif title.endswith(f" {emoji2}"):
                        title = title[:-len(emoji2)-1]
                    anim_embed.title = f"{title} {current_emoji}".strip()

                # 2. Handle Live Elapsed Time Animation
                if opts.get("show_elapsed_time") and opts.get("animate_elapsed_time"):
                    if anim_content and opts.get("show_status_line") and "Last:" in anim_content:
                        elapsed = time.monotonic() - start_time
                        anim_content += f" ({elapsed:.1f}s)"

            # 3. Fire the Edit Request to Discord
            try:
                await msg.edit(content=anim_content, embed=anim_embed, view=archived_view)
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = e.response.headers.get("Retry-After") if e.response else None
                    sleep_time = float(retry_after) if retry_after else PANEL_STATUS_ANIMATE_INTERVAL + 1
                    await asyncio.sleep(sleep_time)
                else:
                    break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.warning(f"⚠️ Animation task encountered an error: {e}")

async def _animate_text_loading(msg: discord.Message, base_text: str, start_time: float):
    """Animates a temporary chat loading message by ticking up the elapsed time."""
    try:
        while True:
            await asyncio.sleep(PANEL_STATUS_ANIMATE_INTERVAL)
            elapsed = time.monotonic() - start_time
            new_text = f"{base_text} ({elapsed:.1f}s)"
            try:
                await msg.edit(content=new_text)
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = float(e.response.headers.get("Retry-After", PANEL_STATUS_ANIMATE_INTERVAL + 1))
                    await asyncio.sleep(retry_after)
                else:
                    break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.error(f"⚠️ Animation loop error: {e}")

async def process_panel_action(interaction: discord.Interaction, panel_name: str, command: str, args: list, modal_data: dict = None):
    """Shared execution logic for Buttons, Selects, and Modals."""
    animation_task = None
    log.info(f"🖱️ User '{interaction.user.display_name}' clicked action '{command}' on panel '{panel_name}'")

    cfg = _get_cmd_cfg(command)
    if cfg.get("accept_attachments"):
        log.warning(f"⚠️ User '{interaction.user.display_name}' clicked action '{command}' but it requires a file upload.")
        await interaction.followup.send("❌ This command requires a file upload.", ephemeral=True)
        return

    payload = build_payload(
        event_type="panel_action", command=command, args=args,
        raw=f"[panel] {command} {' '.join(args)}".strip(),
        guild=interaction.guild, channel=interaction.channel, user=interaction.user,
        interaction_id=str(interaction.id),
    )
    if modal_data:
        payload["modal_inputs"] = modal_data

    msg = interaction.message
    current_embed = None
    current_content = None
    archived_view = None
    start_time = time.monotonic() 
    
    # ====================================================================
    # MAX CONFIGURATION RESOLUTION (Panel Config overrides ENV Globals)
    # ====================================================================
    panel_cfg = PANELS.get(panel_name) or {}
    status_opts = panel_cfg.get("status", {})
    
    # Read explicit panel config, fallback to Global ENV variables
    opt_show_status_line       = status_opts.get("show_status_line", PANEL_STATUS_LINE)
    opt_show_elapsed_time      = status_opts.get("show_elapsed_time", PANEL_STATUS_SHOW_ELAPSED)
    opt_emoji_in_status_line   = status_opts.get("emoji_in_status_line", PANEL_STATUS_EMOJI_TITLE)
    opt_emoji_in_embed_title   = status_opts.get("emoji_in_embed_title", PANEL_STATUS_EMOJI_IN_EMBED)
    opt_animate_pending        = status_opts.get("animate_pending_emoji", PANEL_STATUS_ANIMATE_PENDING)
    opt_animate_elapsed        = status_opts.get("animate_elapsed_time", PANEL_STATUS_ANIMATE_ELAPSED)
    opt_append_status_to_reply = status_opts.get("append_status_to_reply", False)

    # SAFETY CHECK: If this panel is orphaned (missing from memory), we cannot spawn a replacement. 
    # Therefore, we must forcefully prevent the UI from being destroyed.
    if not PANELS.get(panel_name):
        opt_spawn_new = False
        opt_archive_disable = False
    else:
        opt_spawn_new       = panel_cfg.get("spawn_new_on_click", PANEL_SPAWN_NEW_ON_CLICK)
        opt_archive_disable = panel_cfg.get("archive_disable_buttons", PANEL_ARCHIVE_DISABLE_BUTTONS)

    # Custom Panel Emojis
    emojis_cfg = status_opts.get("emojis", {})
    emoji_pending     = emojis_cfg.get("pending", PANEL_STATUS_EMOJI_PENDING)
    emoji_pending_alt = emojis_cfg.get("pending_alt", PANEL_STATUS_EMOJI_PENDING_ALT)
    emoji_success     = emojis_cfg.get("success", PANEL_STATUS_EMOJI_SUCCESS)
    emoji_fail        = emojis_cfg.get("fail", PANEL_STATUS_EMOJI_FAIL)
    
    anim_opts = {
        "animate_pending_emoji": opt_animate_pending,
        "animate_elapsed_time": opt_animate_elapsed,
        "show_status_line": opt_show_status_line,
        "emoji_in_status_line": opt_emoji_in_status_line,
        "emoji_in_embed_title": opt_emoji_in_embed_title,
        "show_elapsed_time": opt_show_elapsed_time,
        "emoji_pending": emoji_pending,
        "emoji_pending_alt": emoji_pending_alt
    }

    # 1. Archive immediately & Set Pending State
    try:
        if msg:
            content, embed = _build_panel_message(panel_name, panel_cfg)
            
            # Fallback for dynamic edits: Prevent static titles from overwriting webhook reports
            if not panel_cfg.get("content") and msg.content:
                content = msg.content
                for marker in [
                    f"\n{emoji_success} Last: `", f"\n{emoji_fail} Last: `", f"\n{emoji_pending} Last: `", "\nLast: `",
                    f"{emoji_success} Last: `", f"{emoji_fail} Last: `", f"{emoji_pending} Last: `", "Last: `"
                ]:
                    if marker in content:
                        content = content.split(marker)[0].strip()
                        break
                embed = msg.embeds[0] if msg.embeds else None
            
            # Append audit status line if enabled
            if opt_show_status_line:
                ts = datetime.now(ZoneInfo(TIMEZONE)).strftime("%-I:%M %p") if TIMEZONE else datetime.now().strftime("%I:%M %p").lstrip("0")
                user_display = getattr(interaction.user, "display_name", None) or getattr(interaction.user, "name", "Someone")
                last_cmd = f"{command} {' '.join(args)}".strip()
                safe_content = content if content else ""
                emoji_prefix = f"{emoji_pending} " if opt_emoji_in_status_line else ""
                content = f"{safe_content}\n{emoji_prefix}Last: `{last_cmd}` • {user_display} • {ts}".strip()

                if len(content) > 2000: content = content[:1997] + "..."

            if embed and opt_emoji_in_embed_title:
                embed.title = f"{embed.title or ''} {emoji_pending}".strip()
                
            current_embed = embed
            current_content = content
            
            if panel_cfg:
                archived_view = DashPanel(panel_name, panel_cfg, disabled=opt_archive_disable)
            elif msg.components:
                archived_view = discord.ui.View.from_message(msg)
                if opt_archive_disable:
                    for child in archived_view.children:
                        child.disabled = True
            else:
                archived_view = DashPanel(panel_name, panel_cfg, disabled=opt_archive_disable)
            
            await msg.edit(content=content, embed=embed, view=archived_view)
            if opt_animate_pending or opt_animate_elapsed:
                animation_task = asyncio.create_task(_animate_pending_message(msg, content, embed, archived_view, start_time, anim_opts))

            if opt_archive_disable and interaction.channel:
                cid_str = str(interaction.channel.id)
                if _get_active_panel_msg_id(interaction.channel.id, panel_name) == str(msg.id):
                    PANEL_ACTIVE.get(cid_str, {}).pop(panel_name, None)
                if _get_panel_msg_id(interaction.channel.id, panel_name) == str(msg.id):
                    PANEL_STATE.get(cid_str, {}).pop(panel_name, None)
    except Exception as e:
        log.warning(f"⚠️ Failed to edit/archive panel message: {e}")

    # 2. Spawn the new one immediately
    if opt_spawn_new and interaction.channel and PANELS.get(panel_name):
        try:
            await _post_panel_to_channel(interaction.channel, panel_name, PANELS.get(panel_name, {}), force_new=True)
        except Exception as e:
            log.error(f"⚠️ Failed to spawn new panel '{panel_name}': {e}", exc_info=True)

    # 3. Webhook call
    is_success = False
    loading_msg = None
    loading_anim_task = None
    
    # Panels require explicit 'show_loading_message: true' in config to display loading state
    opt_show_loading = status_opts.get("show_loading_message", False)
    opt_append_status_to_reply = status_opts.get("append_status_to_reply", False)
    
    # Spawn the temporary animated loading message
    if opt_show_loading and interaction.channel:
        display_cmd = f"/{command} {' '.join(args)}".strip()
        loading_text = cfg.get("loading_text", COMMAND_LOADING_MESSAGE_TEXT).replace("{command}", display_cmd)
        try:
            loading_msg = await interaction.followup.send(loading_text, wait=True)
            if opt_animate_elapsed or PANEL_STATUS_ANIMATE_ELAPSED:
                loading_anim_task = asyncio.create_task(_animate_text_loading(loading_msg, loading_text, start_time))
        except Exception as e:
            log.warning(f"⚠️ Failed to post loading message: {e}")

    try:
        data = await post_to_webhook_async(command, payload)
        elapsed = time.monotonic() - start_time
        
        # Cancel loading animation task before editing message
        if loading_anim_task:
            loading_anim_task.cancel()
            try: await loading_anim_task
            except asyncio.CancelledError: pass

        is_success = data.get("ok", True) if isinstance(data, dict) else True

        reply = (data or {}).get("reply") or {}
        if not isinstance(reply, dict): reply = {"content": str(reply)}

        suppress = parse_bool(reply.get("suppress") or reply.get("supress"))
        reply_content = (reply.get("content") or "").strip()
        
        if opt_append_status_to_reply:
            status_emoji = emoji_success if is_success else emoji_fail
            ts = datetime.now(ZoneInfo(TIMEZONE)).strftime("%-I:%M %p") if TIMEZONE else datetime.now().strftime("%I:%M %p").lstrip("0")
            user_display = getattr(interaction.user, "display_name", None) or getattr(interaction.user, "name", "Someone")
            
            full_cmd = f"{command} {' '.join(args)}".strip()
            status_line = f"{status_emoji} Last: `{full_cmd[:120]}` • {user_display} • {ts} ({elapsed:.1f}s)"
            
            reply_content = f"{reply_content}\n\n{status_line}".strip() if reply_content else status_line

        is_ephemeral = parse_bool(reply.get("ephemeral", cfg.get("ephemeral_replies", False)))
        reply_to_msg = parse_bool(reply.get("reply_to_message", cfg.get("reply_to_message", COMMAND_REPLY_TO_MESSAGE)))

        embeds_raw = reply.get("embeds") or []
        embeds = []
        if isinstance(embeds_raw, list):
            for e in embeds_raw[:10]:
                if isinstance(e, dict):
                    try: embeds.append(discord.Embed.from_dict(e))
                    except Exception: pass

        panel_cfg_dyn = reply.get("panel") or data.get("panel")
        view = None
        if isinstance(panel_cfg_dyn, dict):
            panel_id = panel_cfg_dyn.get("id", f"dyn_{command}")
            view = DashPanel(panel_id, panel_cfg_dyn)
            PANELS[panel_id] = panel_cfg_dyn
            DYNAMIC_PANELS[panel_id] = panel_cfg_dyn
            _save_dynamic_routes()

        has_display_data = bool(reply_content or embeds)

        # Sender wrapper to update loading message or send as a new response
        first_chunk = True
        async def smart_sender(content=None, **kwargs):
            nonlocal first_chunk
            
            # 🧹 Create a safe copy of kwargs for methods that reject the 'ephemeral' argument
            safe_kwargs = kwargs.copy()
            safe_kwargs.pop("ephemeral", None)
            
            if first_chunk:
                first_chunk = False
                if loading_msg:
                    try:
                        # Message.edit DOES NOT accept ephemeral
                        await loading_msg.edit(content=content, **safe_kwargs)
                        return
                    except Exception as e:
                        log.error(f"⚠️ Discord rejected final message edit in panel action: {e}")
                
                # Fallback if no loading message exists
                if not is_ephemeral and interaction.channel and not reply_to_msg:
                    # channel.send DOES NOT accept ephemeral
                    await interaction.channel.send(content=content, **safe_kwargs)
                else:
                    # interaction.followup DOES accept ephemeral (so we use original kwargs)
                    await interaction.followup.send(content=content, **kwargs)
            else:
                # Chunk 2+ always goes to channel, which DOES NOT accept ephemeral
                await interaction.channel.send(content=content, **safe_kwargs)

        if not suppress and has_display_data:
            kwargs = {"ephemeral": is_ephemeral, "embeds": embeds}
            if view: kwargs["view"] = view
            await _send_chunked(smart_sender, reply_content, **kwargs)
        else:
            # If there is no chat content, clean up the loading pane
            if loading_msg:
                try: await loading_msg.delete()
                except: pass
            
            # If a view was returned without text content, apply it to the original panel in-place
            if view and not suppress:
                archived_view = view

    except Exception as e:
        if loading_anim_task: loading_anim_task.cancel()
        if loading_msg: 
            try: await loading_msg.delete()
            except: pass
        log.error(f"⚠️ Exception triggering button command '{command}': {e}", exc_info=True)
        await interaction.followup.send(f"⚠️ Trigger failed: {type(e).__name__}: {e}", ephemeral=True)
        is_success = False
        
    finally:
        if animation_task: animation_task.cancel()
        elapsed_time = time.monotonic() - start_time

        # 4. Update the archived message with final status
        if msg:
            try:
                status_emoji = emoji_success if is_success else emoji_fail
                kwargs = {}

                if current_embed and opt_emoji_in_embed_title:
                    if current_embed.title:
                        if current_embed.title.endswith(f" {emoji_pending}"):
                            current_embed.title = current_embed.title[:-len(emoji_pending)-1]
                        elif current_embed.title.endswith(f" {emoji_pending_alt}"):
                            current_embed.title = current_embed.title[:-len(emoji_pending_alt)-1]
                    current_embed.title = f"{current_embed.title or ''} {status_emoji}".strip()
                    kwargs["embed"] = current_embed
                    
                if current_content and opt_show_status_line:
                    if opt_emoji_in_status_line:
                        target = f"{emoji_pending} Last:"
                        if target in current_content:
                            current_content = current_content.replace(target, f"{status_emoji} Last:")
                        
                    if opt_show_elapsed_time:
                        current_content += f" ({elapsed_time:.1f}s)"
                        
                    kwargs["content"] = current_content
                    
                if archived_view: 
                    kwargs["view"] = archived_view
                    
                if kwargs:
                    try:
                        # This kills the inline spinner AND updates the panel instantly
                        await interaction.edit_original_response(**kwargs)
                    except:
                        # Fallback just in case
                        await msg.edit(**kwargs)
            except Exception as e:
                log.warning(f"⚠️ Failed to update panel with final success/fail status: {e}")

        # Schedule panel persistence check
        if interaction.channel:
            p_persist = panel_cfg.get("persist", {})
            if p_persist.get("on_response", PANEL_PERSIST_ON_RESPONSE):
                panel_delay = float(p_persist.get("response_delay_sec", PANEL_PERSIST_ON_RESPONSE_DELAY))
                delay = float(cfg.get("action_persist_delay", cfg.get("panel_persist_delay", panel_delay)))
                
                if delay > 0:
                    asyncio.create_task(_delayed_persist(interaction.channel.id, delay))
                else:
                    trigger_immediate_persist(interaction.channel.id)

class DashModal(discord.ui.Modal):
    def __init__(self, panel_name: str, command: str, args: list, modal_cfg: dict):
        super().__init__(title=modal_cfg.get("title", "Input Required")[:45])
        self.panel_name = panel_name
        self.command = command
        self.args = args
        self.inputs_dict = {}

        for inp in modal_cfg.get("inputs", [])[:5]:
            placeholder_text = str(inp.get("placeholder", ""))[:100] if inp.get("placeholder") else None
            ti = discord.ui.TextInput(
                label=str(inp.get("label", "Input"))[:45],
                custom_id=str(inp.get("id", f"inp_{len(self.inputs_dict)}")),
                style=discord.TextStyle.paragraph if inp.get("long") else discord.TextStyle.short,
                placeholder=placeholder_text,
                required=inp.get("required", True)
            )
            self.add_item(ti)
            self.inputs_dict[inp.get("id")] = ti

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        modal_data = {k: v.value for k, v in self.inputs_dict.items()}
        await process_panel_action(interaction, self.panel_name, self.command, self.args, modal_data)

class DashButton(discord.ui.Button):
    def __init__(self, panel_name: str, cfg: dict, index: int):
        label = cfg.get("label", "Button")
        command = cfg.get("command")
        args = cfg.get("args", []) or []
        style_name = (cfg.get("style") or "secondary").lower()

        if not isinstance(command, str) or not command:
            raise RuntimeError(f"Panel button missing command: {cfg}")

        super().__init__(
            label=label,
            emoji=cfg.get("emoji"),
            style=STYLE_MAP.get(style_name, discord.ButtonStyle.secondary),
            # Added index to guarantee unique IDs
            custom_id=f"dashcord:btn:{panel_name}:{index}:{command}:{'-'.join(args)}"[:100]
        )

        self.panel_name = panel_name
        self.command = command
        self.args = args
        self.cfg = cfg

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

        if "modal" in self.cfg:
            await interaction.response.send_modal(DashModal(self.panel_name, self.command, self.args, self.cfg["modal"]))
            return

        # DYNAMIC DEFER: Prevents sticky "Bot is thinking" messages
        cfg = COMMANDS.get(self.command) or {}
        is_ephemeral = parse_bool(cfg.get("ephemeral_replies", False))
        await interaction.response.defer(ephemeral=is_ephemeral)

        await process_panel_action(interaction, self.panel_name, self.command, self.args)

class DashSelect(discord.ui.Select):
    def __init__(self, panel_name: str, select_cfg: dict, index: int):
        self.panel_name = panel_name
        self.select_cfg = select_cfg
        
        options = []
        for i, opt in enumerate(select_cfg.get("options", [])[:25]):
            cmd = opt.get("command")
            args_str = "|".join(opt.get("args", []))
            # Keep the index 'i' in the value so we can map it back in the callback
            val = f"{i}::{cmd}::{args_str}"
            
            options.append(discord.SelectOption(
                label=opt.get("label", "Option")[:100],
                value=val[:100],
                emoji=opt.get("emoji"),
                description=opt.get("description")[:100] if opt.get("description") else None
            ))
            
        super().__init__(
            placeholder=select_cfg.get("placeholder", "Select an option...")[:150],
            options=options,
            # Added index to guarantee unique IDs across multiple dropdowns
            custom_id=f"dashcord:sel:{panel_name}:{index}"[:100]
        )

    async def callback(self, interaction: discord.Interaction):
        if not self.values or not interaction.channel: 
            return

        parts = self.values[0].split("::")
        opt_index = int(parts[0])
        command = parts[1]
        args = parts[2].split("|") if parts[2] else []
        
        if not is_channel_allowed(command, interaction.channel.id):
            await interaction.response.send_message("⛔ Not allowed in this channel.", ephemeral=True)
            return

        if not is_user_allowed(command, interaction.user.id):
            await interaction.response.send_message("⛔ Not allowed for your user.", ephemeral=True)
            return

        # 1. Look up the specific option's original configuration
        options_list = self.select_cfg.get("options", [])
        opt_cfg = options_list[opt_index] if opt_index < len(options_list) else {}

        # 2. Check if this option has a modal configured
        if "modal" in opt_cfg:
            # Send the modal directly as the initial response (DO NOT DEFER)
            await interaction.response.send_modal(
                DashModal(self.panel_name, command, args, opt_cfg["modal"])
            )
            
            if interaction.message:
                for opt in self.options: 
                    opt.default = False
                try:
                    await interaction.message.edit(view=self.view)
                except Exception:
                    pass
            return

        # 3. If there is no modal, proceed with normal execution (defer & trigger webhook)
        for opt in self.options: 
            opt.default = False

        # DYNAMIC DEFER: Prevents sticky "Bot is thinking" messages
        cfg = COMMANDS.get(command) or {}
        is_ephemeral = parse_bool(cfg.get("ephemeral_replies", False))
        await interaction.response.defer(ephemeral=is_ephemeral)

        await process_panel_action(interaction, self.panel_name, command, args)
class DashPanel(discord.ui.View):
    def __init__(self, panel_name: str, panel_cfg: dict, *, disabled: bool = False):
        super().__init__(timeout=None)
        
        # True if archived OR if the API explicitly disabled the panel in the config
        is_disabled = disabled or panel_cfg.get("disabled", False)
        
        for i, btn_cfg in enumerate(panel_cfg.get("buttons") or []):
            b = DashButton(panel_name, btn_cfg, index=i)
            b.disabled = is_disabled
            self.add_item(b)
            
        for i, sel_cfg in enumerate(panel_cfg.get("selects") or []):
            s = DashSelect(panel_name, sel_cfg, index=i)
            s.disabled = is_disabled
            self.add_item(s)


async def post_panels():
    log.info("⚙️ Initializing active panels on startup...")
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
    log.info("⚙️ Startup panel initialization complete.")

# ----------------------------
# DYNAMIC UI API (INBOUND)
# ----------------------------
def _json_reply(data: dict, status: int = 200) -> web.Response:
    """Helper to return properly formatted JSON strings with trailing newlines for cURL."""
    return web.Response(
        text=json.dumps(data) + "\n",
        status=status,
        content_type="application/json"
    )

def _is_api_protected(cfg: dict) -> bool:
    """Checks if a command or panel has the api_protected flag set to true."""
    if not isinstance(cfg, dict):
        return False
    val = cfg.get("api_protected", False)
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes")
    return bool(val)

def _is_api_writable(cfg: dict, is_static: bool) -> bool:
    """Checks if an item is allowed to be overwritten/refreshed by the API."""
    if _is_api_protected(cfg):
        return False  # Protected items are NEVER writable
        
    # Per-item override check in the JSON config
    if "api_writable" in cfg:
        val = cfg["api_writable"]
        if isinstance(val, str):
            return val.strip().lower() in ("1", "true", "yes")
        return bool(val)
        
    # Fallbacks: dynamic items are always writable. Static items rely on the global env flag.
    return API_ALLOW_STATIC_OVERWRITE if is_static else True

def _filter_protected(inventory: dict) -> dict:
    """Removes any protected items from API dumps."""
    return {k: v for k, v in inventory.items() if not _is_api_protected(v)}

async def api_dynamic_handler(request: web.Request) -> web.Response:
    """
    Advanced Dynamic Routing Engine API.
    Expects JSON:
    {
       "type": "panel" | "command",
       "action": "upsert" | "delete" | "refresh" | "get",
       "id": "my_element_id",       # Optional for "get" (omitting returns all)
       "config": { ... optional update data ... }
    }
    """
    client_ip = request.remote
    user_agent = request.headers.get("User-Agent", "Unknown")
    
    log.info(f"🌐 [API] Connection attempt from IP: {client_ip} | Agent: {user_agent}")

    auth_header = request.headers.get("Authorization") or request.headers.get("X-DashCord-Token")
    if auth_header and auth_header.startswith("Bearer "):
        auth_header = auth_header[7:].strip()

    if DASHCORD_SHARED_SECRET and auth_header != DASHCORD_SHARED_SECRET:
        log.warning(f"🚫 [API] UNAUTHORIZED access attempt from IP: {client_ip}")
        return _json_reply({"error": "Unauthorized"}, status=401)
    
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object")
    except Exception as e:
        log.error(f"⚠️ [API] Invalid JSON from IP: {client_ip} - {e}")
        return _json_reply({"error": f"Invalid JSON: {e}"}, status=400)
        
    req_type = payload.get("type", "panel")
    action = payload.get("action", "upsert")
    item_id = payload.get("id")
    config = payload.get("config", {})
    
    # Backwards compatibility check for old /api/send_panel behavior
    if not item_id and req_type == "panel" and action != "get":
        item_id = payload.get("panel_name", f"Dynamic_{uuid.uuid4().hex[:8]}")
        config = payload.get("config", payload) # move flat config under 'config'
        if "channel_id" in payload:
            config["channels"] = [payload["channel_id"]]

    # If action is 'get' and no ID is provided, default to 'all' to list inventory
    if not item_id and action == "get":
        item_id = "all"

    if not item_id:
        log.warning(f"⚠️ [API] Request from {client_ip} missing 'id' field.")
        return _json_reply({"error": "Missing 'id' in payload"}, status=400)
        
    # Super detailed logging
    log.info(f"⚙️ [API] Processing '{action}' for {req_type} '{item_id}' from IP: {client_ip}")
    if config:
        log.info(f"📦 [API] Payload config provided:\n{json.dumps(config, indent=2)}")
        
    # --- GET ACTION (READ) ---
    if action == "get":
        if req_type == "command":
            if item_id == "all":
                log.info(f"🔍 [API] Listing ALL accessible commands successfully for IP: {client_ip}")
                return _json_reply({"status": "success", "commands": _filter_protected(COMMANDS)})
            
            cmd_cfg = COMMANDS.get(item_id)
            if not cmd_cfg or _is_api_protected(cmd_cfg):
                log.warning(f"⚠️ [API] Command '{item_id}' not found or protected (IP: {client_ip})")
                return _json_reply({"error": f"Command '{item_id}' not found"}, status=404)
            
            log.info(f"🔍 [API] GET command '{item_id}' successfully retrieved by IP: {client_ip}")
            return _json_reply({"status": "success", "id": item_id, "config": cmd_cfg})
            
        elif req_type == "panel":
            if item_id == "all":
                log.info(f"🔍 [API] Listing ALL accessible panels successfully for IP: {client_ip}")
                return _json_reply({"status": "success", "panels": _filter_protected(PANELS)})
                
            panel_cfg = PANELS.get(item_id)
            if not panel_cfg or _is_api_protected(panel_cfg):
                log.warning(f"⚠️ [API] Panel '{item_id}' not found or protected (IP: {client_ip})")
                return _json_reply({"error": f"Panel '{item_id}' not found"}, status=404)
                
            log.info(f"🔍 [API] GET panel '{item_id}' successfully retrieved by IP: {client_ip}")
            return _json_reply({"status": "success", "id": item_id, "config": panel_cfg})
            
        return _json_reply({"error": f"Invalid type for get: {req_type}"}, status=400)

    # --- COMMANDS (WRITE/DELETE) ---
    if req_type == "command":
        is_static = item_id in STATIC_COMMANDS
        existing_cmd = COMMANDS.get(item_id)

        if existing_cmd:
            if _is_api_protected(existing_cmd):
                log.warning(f"🛡️ [API] Security block: IP {client_ip} attempted to modify protected command '{item_id}'")
                return _json_reply({"error": f"Command '{item_id}' is protected and cannot be modified via API."}, status=403)
            
            if not _is_api_writable(existing_cmd, is_static):
                log.warning(f"🛡️ [API] Security block: IP {client_ip} attempted to modify STATIC command '{item_id}' without permission")
                return _json_reply({"error": f"Command '{item_id}' is a static route and lacks 'api_writable: true'."}, status=403)

        if action in ("upsert", "refresh"):
            if config:
                existing = _clone_payload(DYNAMIC_COMMANDS.get(item_id, COMMANDS.get(item_id, {})))
                new_config = _deep_update(existing, config)

                DYNAMIC_COMMANDS[item_id] = new_config
                COMMANDS[item_id] = new_config
                _save_dynamic_routes()
            
            log.info(f"✅ [API] Command '{item_id}' {action.upper()}ED successfully by {client_ip}")
            return _json_reply({"status": "success", "message": f"Command '{item_id}' updated"})
            
        elif action == "delete":
            DYNAMIC_COMMANDS.pop(item_id, None)
            COMMANDS.pop(item_id, None)
            _save_dynamic_routes()
            
            log.info(f"🗑️ [API] Command '{item_id}' DELETED successfully by {client_ip}")
            return _json_reply({"status": "success", "message": f"Command '{item_id}' deleted"})
            
        return _json_reply({"error": f"Invalid action for command: {action}"}, status=400)
            
    # --- PANELS (WRITE/DELETE) ---
    elif req_type == "panel":
        is_static = item_id in STATIC_PANELS
        existing_panel = PANELS.get(item_id)

        if existing_panel:
            if _is_api_protected(existing_panel):
                log.warning(f"🛡️ [API] Security block: IP {client_ip} attempted to modify protected panel '{item_id}'")
                return _json_reply({"error": f"Panel '{item_id}' is protected and cannot be modified via API."}, status=403)

            if not _is_api_writable(existing_panel, is_static):
                log.warning(f"🛡️ [API] Security block: IP {client_ip} attempted to modify STATIC panel '{item_id}' without permission")
                return _json_reply({"error": f"Panel '{item_id}' is a static route and lacks 'api_writable: true'."}, status=403)

        if action == "delete":
            DYNAMIC_PANELS.pop(item_id, None)
            panel_cfg = PANELS.pop(item_id, None)
            _save_dynamic_routes()
            
            # Try to delete from Discord channels
            if panel_cfg:
                for cid in panel_cfg.get("channels", []):
                    try:
                        channel = bot.get_channel(int(cid)) or await bot.fetch_channel(int(cid))
                        await _delete_existing_panel_message(channel, item_id)
                    except Exception:
                        pass
                        
            log.info(f"🗑️ [API] Panel '{item_id}' DELETED successfully by {client_ip}")
            return _json_reply({"status": "success", "message": f"Panel '{item_id}' deleted"})
            
        elif action in ("upsert", "refresh"):
            if config:
                existing = _clone_payload(DYNAMIC_PANELS.get(item_id, PANELS.get(item_id, {})))
                new_config = _deep_update(existing, config)

                DYNAMIC_PANELS[item_id] = new_config
                PANELS[item_id] = new_config
                _save_dynamic_routes()
                
            panel_cfg = PANELS.get(item_id)
            if not panel_cfg:
                log.warning(f"⚠️ [API] Attempt to refresh non-existent panel '{item_id}' by {client_ip}")
                return _json_reply({"error": f"Panel '{item_id}' not found"}, status=404)
                
            results = []
            for cid in panel_cfg.get("channels", []):
                try:
                    channel = bot.get_channel(int(cid)) or await bot.fetch_channel(int(cid))
                    await _post_panel_to_channel(channel, item_id, panel_cfg, force_new=False)
                    msg_id = _get_panel_msg_id(int(cid), item_id)
                    results.append({"channel_id": cid, "message_id": str(msg_id) if msg_id else None})
                    log.info(f"🌐 [API] Panel '{item_id}' updated in Discord channel {cid} (Message ID: {msg_id})")
                except Exception as e:
                    results.append({"channel_id": cid, "error": str(e)})
                    log.error(f"⚠️ [API] Failed to update panel '{item_id}' in channel {cid}: {e}")
                    
            log.info(f"✅ [API] Panel '{item_id}' {action.upper()}ED successfully by {client_ip}")
            return _json_reply({"status": "success", "message": f"Panel '{item_id}' {action}ed", "results": results})
            
    return _json_reply({"error": f"Invalid type: {req_type}"}, status=400)


def create_dynamic_slash_command(cmd_name: str, cmd_cfg: dict):
    
    async def slash_callback(interaction: discord.Interaction, arguments: str = None):
        if not is_channel_allowed(cmd_name, interaction.channel_id):
            await interaction.response.send_message("⛔ Not allowed in this channel.", ephemeral=True)
            return
        if not is_user_allowed(cmd_name, interaction.user.id):
            await interaction.response.send_message("⛔ Not allowed for your user.", ephemeral=True)
            return
            
        # 1. Read the ephemeral config directly from the command!
        cmd_ephemeral = bool(cmd_cfg.get("ephemeral_replies", False))
        await interaction.response.defer(ephemeral=cmd_ephemeral)
        
        parsed_args = arguments.split() if arguments else []
        raw_input = f"/{cmd_name} {arguments}".strip() if arguments else f"/{cmd_name}"
        
        payload = build_payload(
            event_type="command",
            command=cmd_name,
            args=parsed_args,
            raw=raw_input,
            guild=interaction.guild,
            channel=interaction.channel,
            user=interaction.user,
            interaction_id=str(interaction.id),
        )
        
        log.info(f"⚡ User '{interaction.user.display_name}' triggered slash command '/{cmd_name}' in channel {interaction.channel_id}")
        
        start_time = time.monotonic()
        show_elapsed = cmd_cfg.get("show_elapsed_time", COMMAND_SHOW_ELAPSED_TIME)

        try:
            data = await post_to_webhook_async(cmd_name, payload)
            elapsed = time.monotonic() - start_time
            
            # Parse the reply
            reply = (data or {}).get("reply") or {}
            if not isinstance(reply, dict):
                reply = {"content": str(reply)}

            # Dynamically inject the final elapsed time and context
            if show_elapsed:
                content = reply.get("content", "")
                
                # Build a panel-quality audit line
                status_emoji = COMMAND_REACTION_SUCCESS if data.get("ok", True) else COMMAND_REACTION_FAIL
                ts = datetime.now(ZoneInfo(TIMEZONE)).strftime("%-I:%M %p") if TIMEZONE else datetime.now().strftime("%I:%M %p").lstrip("0")
                user_display = getattr(interaction.user, "display_name", None) or getattr(interaction.user, "name", "Someone")
                full_cmd = f"/{cmd_name} {arguments}".strip() if arguments else f"/{cmd_name}"
                
                status_line = f"{status_emoji} Last: `{full_cmd[:120]}` • {user_display} • {ts} ({elapsed:.1f}s)"
                
                reply["content"] = f"{content}\n\n{status_line}".strip() if content else status_line

            suppress = bool(reply.get("suppress") or reply.get("supress"))
            content = (reply.get("content") or "").strip()
            
            embeds_raw = reply.get("embeds") or []
            embeds: list[discord.Embed] = []
            if isinstance(embeds_raw, list):
                for e in embeds_raw[:10]:
                    if isinstance(e, dict):
                        try: embeds.append(discord.Embed.from_dict(e))
                        except Exception: pass
            
            # Parse Dynamic Panel config and SAVE IT to memory/disk
            panel_cfg_dyn = reply.get("panel") or data.get("panel")
            view = None
            if isinstance(panel_cfg_dyn, dict):
                panel_id = panel_cfg_dyn.get("id", f"dyn_{cmd_name}")
                view = DashPanel(panel_id, panel_cfg_dyn)
                PANELS[panel_id] = panel_cfg_dyn
                DYNAMIC_PANELS[panel_id] = panel_cfg_dyn
                _save_dynamic_routes()

            # 3. Allow the Webhook JSON payload to override the config ephemeral state
            final_ephemeral = parse_bool(reply.get("ephemeral", cmd_ephemeral))
            reply_to_msg = parse_bool(reply.get("reply_to_message", cmd_cfg.get("reply_to_message", COMMAND_REPLY_TO_MESSAGE)))

            if not suppress and (content or embeds or view):
                kwargs = {"ephemeral": final_ephemeral, "embeds": embeds}
                if view:
                    kwargs["view"] = view
                
                # Post as a General Message if reply_to_message is False
                if not final_ephemeral and interaction.channel and not reply_to_msg:
                    try: await interaction.delete_original_response()
                    except: pass
                    kwargs.pop("ephemeral", None)
                    await _send_chunked(interaction.channel.send, content, **kwargs)
                else:
                    await _send_chunked(interaction.followup.send, content, **kwargs)
                
        except Exception as e:
            await interaction.followup.send(f"⚠️ Trigger failed: {e}", ephemeral=cmd_ephemeral)
            
        finally:
            if interaction.channel_id:
                delay = float(cmd_cfg.get("action_persist_delay", cmd_cfg.get("panel_persist_delay", PANEL_PERSIST_ON_RESPONSE_DELAY)))
                if delay > 0:
                    asyncio.create_task(_delayed_persist(interaction.channel_id, delay))
                else:
                    trigger_immediate_persist(interaction.channel_id)

    desc = cmd_cfg.get("description", f"Trigger the {cmd_name} webhook")[:100]
    cmd = app_commands.Command(name=cmd_name, description=desc, callback=slash_callback)
    return cmd

# ----------------------------
# EVENTS
# ----------------------------
@bot.event
async def on_ready():
    global BOT_STARTED_AT_UTC
    BOT_STARTED_AT_UTC = datetime.now(timezone.utc)
    log.info(f"✅ DashCord online as {bot.user}")

    # Clear and rebuild the slash commands
    bot.tree.clear_commands(guild=None)

    for cmd_name, cmd_cfg in COMMANDS.items():
        try:
            slash_cmd = create_dynamic_slash_command(cmd_name, cmd_cfg)
            bot.tree.add_command(slash_cmd)
        except Exception as e:
            log.error(f"⚠️ Failed to register slash command '{cmd_name}': {e}")

    # Tell Discord's API to update the Slash Command menu globally
    try:
        await bot.tree.sync()
        log.info("Synced application commands successfully.")
    except Exception as e:
        log.error(f"⚠️ Failed to sync application commands with Discord: {e}")

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

            if COMMAND_REACTION_ENABLED:
                await _add_reaction_safe(message, COMMAND_REACTION_PENDING)

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
    
    allow_reactions = cfg.get("reactions_enabled", COMMAND_REACTION_ENABLED)
    show_loading = cfg.get("loading_message", COMMAND_LOADING_MESSAGE_ENABLED)
    show_elapsed = cfg.get("show_elapsed_time", COMMAND_SHOW_ELAPSED_TIME)
    
    # Safely display the full command and arguments without trimming (capped at 120 chars)
    display_cmd = message.content[:120] + ("..." if len(message.content) > 120 else "")
    loading_text = cfg.get("loading_text", COMMAND_LOADING_MESSAGE_TEXT).replace("{command}", display_cmd)

    if cfg.get("accept_attachments") and message.attachments:
        log.info(f"📤 User '{message.author.display_name}' triggered command '{command}' with {len(message.attachments)} file(s)")
        await _fanout_attachments_to_command(message, command, payload)
        return
    
    log.info(f"⚡ User '{message.author.display_name}' triggered command '{command}' in channel {message.channel.id}")

    if allow_reactions:
        await _add_reaction_safe(message, COMMAND_REACTION_PENDING)

    loading_msg = None
    anim_task = None
    start_time = time.monotonic()

    # 1. Spawn the temporary loading pane
    if show_loading:
        try:
            loading_msg = await message.reply(loading_text)
            if PANEL_STATUS_ANIMATE_ELAPSED:
                anim_task = asyncio.create_task(_animate_text_loading(loading_msg, loading_text, start_time))
        except Exception as e:
            log.warning(f"⚠️ Failed to post loading message: {e}")

    try:
        data = await post_to_webhook_async(command, payload)
        elapsed = time.monotonic() - start_time
        
        # Cancel loading animation task before editing message
        if anim_task:
            anim_task.cancel()
            try:
                await anim_task
            except asyncio.CancelledError:
                pass

        if allow_reactions:
            await _remove_reaction_safe(message, COMMAND_REACTION_PENDING)
            if data is not None and data.get("ok", True):
                await _add_reaction_safe(message, COMMAND_REACTION_SUCCESS)
            else:
                await _add_reaction_safe(message, COMMAND_REACTION_FAIL)
                
        # 2. Inject context-rich status line into the final response
        if show_elapsed and data:
            reply = data.setdefault("reply", {})
            if not isinstance(reply, dict):
                reply = {"content": str(reply)}
                data["reply"] = reply
            
            c = reply.get("content", "")
            
            # Build a panel-quality audit line
            status_emoji = COMMAND_REACTION_SUCCESS if data.get("ok", True) else COMMAND_REACTION_FAIL
            ts = datetime.now(ZoneInfo(TIMEZONE)).strftime("%-I:%M %p") if TIMEZONE else datetime.now().strftime("%I:%M %p").lstrip("0")
            user_display = getattr(message.author, "display_name", None) or getattr(message.author, "name", "Someone")
            
            status_line = f"{status_emoji} Last: `{display_cmd}` • {user_display} • {ts} ({elapsed:.1f}s)"
            
            # Append it nicely (or make it the only content if webhook returned empty text)
            reply["content"] = f"{c}\n\n{status_line}".strip() if c else status_line

        # 3. Handle formatting and chunking
        reply = (data or {}).get("reply") or {}
        if not isinstance(reply, dict): reply = {"content": str(reply)}
        suppress = bool(reply.get("suppress") or reply.get("supress"))
        reply_content = (reply.get("content") or "").strip()
        
        embeds_raw = reply.get("embeds") or []
        embeds = []
        if isinstance(embeds_raw, list):
            for e in embeds_raw[:10]:
                if isinstance(e, dict):
                    try: embeds.append(discord.Embed.from_dict(e))
                    except Exception: pass

        panel_cfg_dyn = reply.get("panel") or data.get("panel")
        view = None
        if isinstance(panel_cfg_dyn, dict):
            panel_id = panel_cfg_dyn.get("id", f"dyn_{command}")
            view = DashPanel(panel_id, panel_cfg_dyn)
            PANELS[panel_id] = panel_cfg_dyn
            DYNAMIC_PANELS[panel_id] = panel_cfg_dyn
            _save_dynamic_routes()
            
        # 4. Handle response delivery via message edit or new reply
        first_chunk = True
        
        # Determine if we use an Interaction Reply or a General Channel Message
        reply_to_msg = parse_bool(reply.get("reply_to_message", cfg.get("reply_to_message", COMMAND_REPLY_TO_MESSAGE)))

        async def smart_sender(content=None, **kwargs):
            nonlocal first_chunk
            if first_chunk:
                first_chunk = False
                if loading_msg:
                    try:
                        await loading_msg.edit(content=content, **kwargs)
                        return
                    except discord.HTTPException as e:
                        log.error(f"⚠️ Discord rejected the final message edit: {e}")
                    except Exception as e:
                        log.error(f"⚠️ Unexpected error editing final message: {e}", exc_info=True)
                
                # Fallback if no loading message, check if we should reply
                if reply_to_msg:
                    await message.reply(content=content, **kwargs)
                else:
                    await message.channel.send(content=content, **kwargs)
            else:
                # Chunks 2+ are sent as channel messages
                await message.channel.send(content=content, **kwargs)

        if not suppress and (reply_content or embeds or view):
            kwargs = {"embeds": embeds}
            if view:
                kwargs["view"] = view
            await _send_chunked(smart_sender, reply_content, **kwargs)
        elif loading_msg:
            # Clean up the loading message if the webhook suppressed output
            try: await loading_msg.delete()
            except: pass

    except Exception as e:
        if anim_task: anim_task.cancel()
        if loading_msg: 
            try: await loading_msg.delete()
            except: pass
        log.error(f"⚠️ Exception triggering command '{command}': {e}", exc_info=True)
        await _remove_reaction_safe(message, COMMAND_REACTION_PENDING)
        await _add_reaction_safe(message, COMMAND_REACTION_FAIL)
        await message.reply(f"⚠️ Trigger failed: {type(e).__name__}: {e}")

    finally:
        if message.channel:
            delay = float(cfg.get("action_persist_delay", cfg.get("panel_persist_delay", PANEL_PERSIST_ON_RESPONSE_DELAY)))
            if delay > 0:
                asyncio.create_task(_delayed_persist(message.channel.id, delay))
            else:
                trigger_immediate_persist(message.channel.id)

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

async def api_send_message_handler(request: web.Request) -> web.Response:
    """API Endpoint to send a raw message/embed to a specific Discord channel."""
    client_ip = request.remote
    auth_header = request.headers.get("Authorization") or request.headers.get("X-DashCord-Token")
    if auth_header and auth_header.startswith("Bearer "):
        auth_header = auth_header[7:].strip()
    
    if DASHCORD_SHARED_SECRET and auth_header != DASHCORD_SHARED_SECRET:
        log.warning(f"🚫 [API] UNAUTHORIZED message attempt from IP: {client_ip}")
        return _json_reply({"error": "Unauthorized"}, status=401)
        
    try:
        payload = await request.json()
    except Exception as e:
        return _json_reply({"error": f"Invalid JSON: {e}"}, status=400)
        
    channel_id = payload.get("channel_id")
    content    = str(payload.get("content", "") or "")
    embeds_raw = payload.get("embeds", []) or []
    
    try:
        delay = max(0.0, float(payload.get("delay", 0)))
    except (ValueError, TypeError):
        delay = 0.0
    
    if not channel_id:
        return _json_reply({"error": "Missing 'channel_id'"}, status=400)
        
    try:
        cid_int = int(channel_id)
    except (ValueError, TypeError):
        return _json_reply({"error": f"Invalid channel_id: {channel_id!r}"}, status=400)

    if not content and not embeds_raw:
        return _json_reply({"error": "Must provide 'content' or 'embeds'"}, status=400)

    try:
        # Fetch the destination channel
        channel = bot.get_channel(cid_int) or await bot.fetch_channel(cid_int)
        if not channel:
            return _json_reply({"error": f"Channel {channel_id} not found or inaccessible."}, status=404)
            
        # Parse embeds safely
        embeds = []
        if isinstance(embeds_raw, list):
            for e in embeds_raw[:10]:
                try: embeds.append(discord.Embed.from_dict(e))
                except Exception: pass
                
        # Background task to handle delay and sending
        async def background_send():
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                await _send_chunked(channel.send, content, embeds=embeds)
                log.info(f"📤 [API] Successfully sent automated message to channel {channel_id}")
            except Exception as e:
                log.error(f"⚠️ [API] Failed to send background message to {channel_id}: {e}", exc_info=True)

        # Fire it in the background so the API responds instantly to n8n
        asyncio.create_task(background_send())
        
        return _json_reply({"status": "success", "message": f"Message queued with {delay}s delay"})
        
    except Exception as e:
        log.error(f"⚠️ [API] Failed to queue message to {channel_id}: {e}", exc_info=True)
        return _json_reply({"error": str(e)}, status=500)
    
# Attach the API server to the bot's background loop natively
async def _setup_hook():
    global AIOHTTP_SESSION
    AIOHTTP_SESSION = aiohttp.ClientSession()

    async def init_state():
        await bot.wait_until_ready()
        
        # 1. Fire the post_panels() function on startup if enabled
        if PANEL_REPOST_ON_STARTUP:
            await post_panels()
            
        # 2. Start the periodic persistence check loop ONLY AFTER panels are attached
        if not panel_persist_loop.is_running():
            panel_persist_loop.start()
            
    asyncio.create_task(init_state())

    if not API_ENABLED:
        log.info("🛡️ API Server is disabled by API_ENABLED flag. Skipping boot.")
        return

    app = web.Application()
    app.router.add_post('/api/dynamic', api_dynamic_handler)
    app.router.add_post('/api/send_panel', api_dynamic_handler) 
    app.router.add_post('/api/send_message', api_send_message_handler) 
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', API_PORT)
    await site.start()
    log.info(f"🌐 Dynamic UI API listening on port {API_PORT}")

# Bind clean session teardown on shutdown
_orig_bot_close = bot.close

async def _bot_close_cleanup():
    global AIOHTTP_SESSION
    if AIOHTTP_SESSION and not AIOHTTP_SESSION.closed:
        await AIOHTTP_SESSION.close()
    await _orig_bot_close()

bot.close = _bot_close_cleanup
bot.setup_hook = _setup_hook

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