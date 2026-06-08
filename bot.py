#!/usr/bin/env python3
"""
bot.py — Painel de controle do Userbot Pro via Telegram Bot.

Uso:    python bot.py
Requer: BOT_TOKEN e DONO_ID definidos em config.json

Como obter:
  BOT_TOKEN — crie um bot no @BotFather e copie o token
  DONO_ID   — seu ID numérico do Telegram (@userinfobot pode te dar)
"""
import json
import time
import os
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ── Config ────────────────────────────────────────────────────────────────────
try:
    with open("config.json", "r", encoding="utf-8") as _f:
        _cfg = json.load(_f)
except FileNotFoundError:
    raise SystemExit("❌  config.json não encontrado. Execute a partir da raiz do projeto.")
except json.JSONDecodeError as _e:
    raise SystemExit(f"❌  config.json malformado: {_e}")

_BOT_TOKEN = _cfg.get("BOT_TOKEN", "")
_DONO_ID   = int(_cfg.get("DONO_ID", 0))

if not _BOT_TOKEN:
    raise SystemExit(
        "❌  BOT_TOKEN ausente em config.json.\n"
        "    Crie um bot no @BotFather e adicione: \"BOT_TOKEN\": \"<token>\""
    )
if not _DONO_ID:
    raise SystemExit(
        "❌  DONO_ID ausente em config.json.\n"
        "    Adicione seu ID numérico: \"DONO_ID\": <número>\n"
        "    (envie /start para @userinfobot para descobrir o seu)"
    )

_CMD_FILE    = "_panel_cmd.json"
_RESULT_FILE = "_panel_result.json"
_STATUS_FILE = "_panel_status.json"
_LOG_FILE    = "userbot.log"
_VERSAO      = _cfg.get("VERSAO", "2.3")

# Heartbeat considerado stale após este intervalo (deve ser > panel.py HEARTBEAT)
_STALE_THRESHOLD = 90


# ── Keyboards ─────────────────────────────────────────────────────────────────
def _kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Status",       callback_data="status"),
            InlineKeyboardButton("📋 Logs",          callback_data="logs"),
        ],
        [
            InlineKeyboardButton("🔄 Reiniciar",     callback_data="ask_restart"),
            InlineKeyboardButton("⬆️ Atualizar",     callback_data="ask_update"),
        ],
        [
            InlineKeyboardButton("⚙️ Configurações", callback_data="config"),
        ],
        [
            InlineKeyboardButton("🛑 Desligar",      callback_data="ask_shutdown"),
        ],
    ])


def _kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("◀️ Voltar", callback_data="main"),
    ]])


def _kb_confirm(action: str, label: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ {label}",  callback_data=f"do_{action}"),
        InlineKeyboardButton("❌ Cancelar", callback_data="main"),
    ]])


# ── Helpers ───────────────────────────────────────────────────────────────────
def _read_status() -> dict:
    try:
        with open(_STATUS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("ts", 0) > _STALE_THRESHOLD:
            data["online"] = False
        return data
    except Exception:
        return {}


async def _send_cmd(action: str, timeout: float = 12.0) -> dict:
    ts = int(time.time())
    try:
        with open(_CMD_FILE, "w", encoding="utf-8") as f:
            json.dump({"action": action, "ts": ts}, f)
    except Exception as e:
        return {"status": "error", "data": str(e)}

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await asyncio.sleep(0.5)
        try:
            with open(_RESULT_FILE, encoding="utf-8") as f:
                result = json.load(f)
            if result.get("ts") == ts:
                try:
                    os.remove(_RESULT_FILE)
                except OSError:
                    pass
                return result
        except Exception:
            pass
    return {"status": "timeout", "data": "Userbot não respondeu a tempo."}


def _format_uptime(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _main_text(st: dict) -> str:
    online = st.get("online", False)
    versao = st.get("versao", _VERSAO)
    ts     = st.get("ts", 0)
    ultima = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "—"
    ic     = "🟢" if online else "🔴"
    return (
        f"<b>⚡ Userbot Pro v{versao}</b>\n"
        f"└ {ic} {'Online' if online else 'Offline'} • <code>{ultima}</code>"
    )


# ── Security ──────────────────────────────────────────────────────────────────
async def _check_owner(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    if uid != _DONO_ID:
        if update.callback_query:
            await update.callback_query.answer("⛔ Acesso negado.", show_alert=True)
        return False
    return True


# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_owner(update):
        return
    st   = _read_status()
    text = _main_text(st)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=_kb_main(), parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=_kb_main(), parse_mode="HTML"
        )


# ── Callback handler ──────────────────────────────────────────────────────────
async def _handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_owner(update):
        return
    q    = update.callback_query
    data = q.data
    await q.answer()

    # ── Voltar ao menu principal ──────────────────────────────────────────────
    if data == "main":
        st   = _read_status()
        await q.edit_message_text(
            _main_text(st), reply_markup=_kb_main(), parse_mode="HTML"
        )
        return

    # ── Status ────────────────────────────────────────────────────────────────
    if data == "status":
        st      = _read_status()
        online  = st.get("online", False)
        ic      = "🟢" if online else "🔴"
        afk_ic  = "✅ Ativo" if st.get("afk") else "❌ Inativo"
        ts      = st.get("ts", 0)
        ultima  = datetime.fromtimestamp(ts).strftime("%d/%m %H:%M:%S") if ts else "—"
        uptime  = _format_uptime(st.get("uptime_s", 0))
        text = (
            f"<b>📊 Status do Userbot</b>\n\n"
            f"├ {ic} {'Online' if online else 'Offline'}\n"
            f"├ 📦 v{st.get('versao', _VERSAO)}\n"
            f"├ ⏱ Uptime: <code>{uptime}</code>\n"
            f"├ 🔧 Prefixo: <code>{st.get('prefixo', ',')}</code>\n"
            f"├ 😴 AFK: {afk_ic}\n"
            f"├ 🌐 Idioma: <code>{st.get('lang', 'pt')}</code>\n"
            f"└ 🕐 Heartbeat: <code>{ultima}</code>"
        )
        await q.edit_message_text(text, reply_markup=_kb_back(), parse_mode="HTML")
        return

    # ── Logs ──────────────────────────────────────────────────────────────────
    if data == "logs":
        try:
            with open(_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = "".join(lines[-25:]).strip()
            if len(tail) > 3200:
                tail = "…" + tail[-3200:]
            if not tail:
                tail = "(log vazio)"
        except FileNotFoundError:
            tail = "(userbot.log não encontrado)"
        except Exception as e:
            tail = f"(erro ao ler log: {e})"
        await q.edit_message_text(
            f"<b>📋 Últimas linhas do log:</b>\n\n<pre>{tail}</pre>",
            reply_markup=_kb_back(),
            parse_mode="HTML",
        )
        return

    # ── Configurações ─────────────────────────────────────────────────────────
    if data == "config":
        st  = _read_status()
        afk = "✅" if st.get("afk") else "❌"
        text = (
            f"<b>⚙️ Configurações atuais</b>\n\n"
            f"├ 🔧 Prefixo: <code>{st.get('prefixo', ',')}</code>\n"
            f"├ 🌐 Idioma: <code>{st.get('lang', 'pt')}</code>\n"
            f"└ 😴 AFK: {afk}"
        )
        await q.edit_message_text(text, reply_markup=_kb_back(), parse_mode="HTML")
        return

    # ── Confirmações ──────────────────────────────────────────────────────────
    if data == "ask_restart":
        await q.edit_message_text(
            "⚠️ <b>Reiniciar o userbot?</b>\n\nFicará offline por alguns segundos.",
            reply_markup=_kb_confirm("restart", "Reiniciar"),
            parse_mode="HTML",
        )
        return

    if data == "ask_shutdown":
        await q.edit_message_text(
            "⚠️ <b>Desligar o userbot?</b>\n\nVocê precisará iniciá-lo manualmente.",
            reply_markup=_kb_confirm("shutdown", "Desligar"),
            parse_mode="HTML",
        )
        return

    if data == "ask_update":
        await q.edit_message_text(
            "⚠️ <b>Atualizar o userbot?</b>\n\nFará pull do GitHub e reiniciará.",
            reply_markup=_kb_confirm("update", "Atualizar"),
            parse_mode="HTML",
        )
        return

    # ── Execução confirmada ───────────────────────────────────────────────────
    if data.startswith("do_"):
        action = data[3:]
        labels = {
            "restart":  "Reiniciando",
            "shutdown": "Desligando",
            "update":   "Atualizando",
        }
        await q.edit_message_text(
            f"⏳ {labels.get(action, action)}...", parse_mode="HTML"
        )
        result = await _send_cmd(action)
        if result.get("status") == "ok":
            await q.edit_message_text(
                f"✅ <b>Comando executado</b>\n\n<code>{result.get('data', '')}</code>",
                reply_markup=_kb_back(),
                parse_mode="HTML",
            )
        else:
            await q.edit_message_text(
                f"⚠️ <b>Sem resposta do userbot</b>\n\n"
                f"<code>{result.get('data', 'timeout')}</code>\n\n"
                f"Verifique se o userbot está online.",
                reply_markup=_kb_back(),
                parse_mode="HTML",
            )
        return


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    print("🤖 Iniciando painel bot...")
    app = Application.builder().token(_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(_handle_callback))
    print(f"✅ Painel online. Dono ID: {_DONO_ID}")
    print("   Envie /start para o bot no Telegram.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
