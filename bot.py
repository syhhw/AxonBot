#!/usr/bin/env python3
"""
bot.py — Painel de manutenção do Userbot Pro via Telegram Bot.

Uso:    python bot.py
Requer: BOT_TOKEN e DONO_ID definidos em config.json

Funcionalidades:
  📊 Status     — online/offline, uptime, AFK, prefixo, CPU/RAM/disco
  📋 Logs       — últimas linhas + modo Live (atualização a cada 5s)
  🔌 Plugins    — listar, instalar (enviar .py), remover
  💻 Sistema    — CPU, RAM, disco com barra visual
  ⚙️ Config     — configurações atuais (somente leitura)
  🔄 Reiniciar  — reinicia o userbot com confirmação
  ⬆️ Atualizar  — git pull + reinicia com confirmação
  🛑 Desligar   — encerra o userbot com confirmação
"""
import json
import time
import os
import asyncio
from datetime import datetime
from pathlib import Path

from telegram import Update, InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ── Config ─────────────────────────────────────────────────────────────────────
try:
    with open("config.json", "r", encoding="utf-8") as _f:
        _cfg = json.load(_f)
except FileNotFoundError:
    raise SystemExit("❌  config.json não encontrado. Execute a partir da raiz do projeto.")
except json.JSONDecodeError as _e:
    raise SystemExit(f"❌  config.json malformado: {_e}")

_TOKEN = _cfg.get("BOT_TOKEN", "")
_OWNER = int(_cfg.get("DONO_ID", 0))

if not _TOKEN:
    raise SystemExit(
        "❌  BOT_TOKEN ausente em config.json.\n"
        "    Crie um bot no @BotFather e adicione: \"BOT_TOKEN\": \"<token>\""
    )
if not _OWNER:
    raise SystemExit(
        "❌  DONO_ID ausente em config.json.\n"
        "    Adicione seu ID: \"DONO_ID\": <número>\n"
        "    (envie /start para @userinfobot)"
    )

_CMD     = "_panel_cmd.json"
_RESULT  = "_panel_result.json"
_STATUS  = "_panel_status.json"
_LOG     = "userbot.log"
_PLUGINS = Path("plugins")
_STALE   = 60   # segundos até heartbeat ser considerado stale

# ── Estado global ──────────────────────────────────────────────────────────────
_live_msgs: dict[int, int] = {}    # chat_id → message_id (log live ativo)
_waiting_plugin: set[int]  = set() # user_ids aguardando upload de .py

# ── IPC ────────────────────────────────────────────────────────────────────────
def _read_status() -> dict:
    try:
        with open(_STATUS, encoding="utf-8") as f:
            d = json.load(f)
        if time.time() - d.get("ts", 0) > _STALE:
            d["online"] = False
        return d
    except Exception:
        return {}


async def _send_cmd(action: str, timeout: float = 12.0) -> dict:
    ts = int(time.time())
    try:
        with open(_CMD, "w", encoding="utf-8") as f:
            json.dump({"action": action, "ts": ts}, f)
    except Exception as e:
        return {"status": "error", "data": str(e)}

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await asyncio.sleep(0.5)
        try:
            with open(_RESULT, encoding="utf-8") as f:
                r = json.load(f)
            if r.get("ts") == ts:
                try:
                    os.remove(_RESULT)
                except OSError:
                    pass
                return r
        except Exception:
            pass
    return {"status": "timeout", "data": "Userbot não respondeu a tempo."}

# ── Formatadores ───────────────────────────────────────────────────────────────
def _uptime(s: float) -> str:
    s = int(s)
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s" if m else f"{s}s"


def _bar(pct: float) -> str:
    filled = max(0, min(10, int(pct / 10)))
    return "█" * filled + "░" * (10 - filled)


def _log_tail(n: int = 30) -> str:
    try:
        with open(_LOG, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = "".join(lines[-n:]).strip()
        if len(tail) > 3200:
            tail = "…" + tail[-3200:]
        return tail or "(log vazio)"
    except FileNotFoundError:
        return "(userbot.log não encontrado)"
    except Exception as e:
        return f"(erro: {e})"


def _list_plugins() -> list[str]:
    try:
        return sorted(p.stem for p in _PLUGINS.glob("*.py") if not p.name.startswith("_"))
    except Exception:
        return []

# ── Textos ─────────────────────────────────────────────────────────────────────
def _txt_main() -> str:
    st     = _read_status()
    online = st.get("online", False)
    versao = st.get("versao", "2.3")
    ts     = st.get("ts", 0)
    hora   = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "—"
    ic     = "🟢" if online else "🔴"
    return (
        f"<b>⚡ Userbot Pro v{versao}</b>\n"
        f"└ {ic} {'Online' if online else 'Offline'} · <code>{hora}</code>"
    )


def _txt_status() -> str:
    st     = _read_status()
    online = st.get("online", False)
    ic     = "🟢" if online else "🔴"
    afk    = "✅ Ativo" if st.get("afk") else "❌ Inativo"
    ts     = st.get("ts", 0)
    hora   = datetime.fromtimestamp(ts).strftime("%d/%m %H:%M:%S") if ts else "—"
    return (
        f"<b>📊 Status</b>\n\n"
        f"├ {ic} {'Online' if online else 'Offline'}\n"
        f"├ 📦 Versão: <code>v{st.get('versao', '?')}</code>\n"
        f"├ ⏱ Uptime: <code>{_uptime(st.get('uptime_s', 0))}</code>\n"
        f"├ 🔧 Prefixo: <code>{st.get('prefixo', ',')}</code>\n"
        f"├ 😴 AFK: {afk}\n"
        f"├ 🌐 Idioma: <code>{st.get('lang', 'pt').upper()}</code>\n"
        f"├ 🖥️ CPU: <code>{st.get('cpu_pct', 0)}%</code>\n"
        f"├ 🧠 RAM: <code>{st.get('ram_used_mb', 0)} / {st.get('ram_total_mb', 0)} MB</code>\n"
        f"├ 💾 Disco: <code>{st.get('disk_pct', 0)}%</code>\n"
        f"└ 🕐 Heartbeat: <code>{hora}</code>"
    )


def _txt_sistema() -> str:
    st    = _read_status()
    cpu   = st.get("cpu_pct", 0)
    ram_p = st.get("ram_pct", 0)
    ram_u = st.get("ram_used_mb", 0)
    ram_t = st.get("ram_total_mb", 0)
    disk  = st.get("disk_pct", 0)
    ts    = st.get("ts", 0)
    hora  = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "—"
    return (
        f"<b>💻 Sistema</b>\n\n"
        f"├ 🖥️ CPU:   <code>{_bar(cpu)} {cpu}%</code>\n"
        f"├ 🧠 RAM:   <code>{_bar(ram_p)} {ram_u}/{ram_t} MB</code>\n"
        f"├ 💾 Disco: <code>{_bar(disk)} {disk}%</code>\n"
        f"├ ⏱ Uptime: <code>{_uptime(st.get('uptime_s', 0))}</code>\n"
        f"└ 🕐 {hora}"
    )


def _txt_config() -> str:
    limit    = _cfg.get("LIMITE_AUTO_UPLOAD", 0)
    limit_mb = f"{limit // 1024 // 1024} MB" if limit else "—"
    drive    = "✅ Ativo"      if _cfg.get("ID_PASTA_RAIZ_DRIVE") else "❌ Inativo"
    gemini   = "✅ Configurado" if _cfg.get("GEMINI_API_KEY")      else "❌ Ausente"
    return (
        f"<b>⚙️ Configurações</b>\n\n"
        f"├ 🔧 Prefixo: <code>{_cfg.get('PREFIXO', ',')}</code>\n"
        f"├ 🌐 Idioma: <code>{_cfg.get('LANGUAGE', 'pt').upper()}</code>\n"
        f"├ 📤 Auto-upload: <code>{limit_mb}</code>\n"
        f"├ 📂 Google Drive: {drive}\n"
        f"├ 🧠 Gemini AI: {gemini}\n"
        f"└ 🤖 Painel Bot: ✅ Ativo"
    )

# ── Keyboards ──────────────────────────────────────────────────────────────────
def _kb_main() -> Markup:
    ic = "🟢" if _read_status().get("online") else "🔴"
    return Markup([
        [Btn(f"{ic} Status",  callback_data="status"),      Btn("📋 Logs",     callback_data="logs")],
        [Btn("🔌 Plugins",    callback_data="plugins"),     Btn("💻 Sistema",  callback_data="sistema")],
        [Btn("⚙️ Config",     callback_data="config")],
        [Btn("🔄 Reiniciar",  callback_data="ask_restart"), Btn("⬆️ Atualizar", callback_data="ask_update")],
        [Btn("🛑 Desligar",   callback_data="ask_shutdown")],
    ])


def _kb_back() -> Markup:
    return Markup([[Btn("◀️ Voltar", callback_data="main")]])


def _kb_confirm(action: str, label: str) -> Markup:
    return Markup([[
        Btn(f"✅ {label}", callback_data=f"do_{action}"),
        Btn("❌ Cancelar", callback_data="main"),
    ]])


def _kb_logs(live: bool = False) -> Markup:
    if live:
        return Markup([[Btn("⏹ Parar Live", callback_data="logs_stop"), Btn("◀️ Voltar", callback_data="main")]])
    return Markup([[
        Btn("🔄 Atualizar", callback_data="logs_refresh"),
        Btn("📡 Live",      callback_data="logs_live"),
        Btn("◀️ Voltar",   callback_data="main"),
    ]])


def _kb_plugins() -> Markup:
    rows = []
    for name in _list_plugins():
        rows.append([
            Btn(f"🔌 {name}", callback_data=f"plugin_info_{name}"),
            Btn("🗑️",         callback_data=f"plugin_del_{name}"),
        ])
    rows.append([Btn("📥 Instalar novo plugin", callback_data="plugin_install")])
    rows.append([Btn("◀️ Voltar", callback_data="main")])
    return Markup(rows)


def _kb_sistema() -> Markup:
    return Markup([[Btn("🔄 Atualizar", callback_data="sistema_refresh"), Btn("◀️ Voltar", callback_data="main")]])

# ── Live log ───────────────────────────────────────────────────────────────────
async def _live_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.data["chat_id"]
    msg_id  = context.job.data["msg_id"]
    hora    = datetime.now().strftime("%H:%M:%S")
    tail    = _log_tail(30)
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=f"<b>📋 Logs</b> (🔴 Live · <code>{hora}</code>)\n\n<pre>{tail}</pre>",
            reply_markup=_kb_logs(live=True),
            parse_mode="HTML",
        )
    except Exception:
        context.job.schedule_removal()
        _live_msgs.pop(chat_id, None)


def _start_live(app: Application, chat_id: int, msg_id: int) -> None:
    _stop_live(app, chat_id)
    if app.job_queue:
        app.job_queue.run_repeating(
            _live_job,
            interval=5,
            first=1,
            data={"chat_id": chat_id, "msg_id": msg_id},
            name=f"live_{chat_id}",
        )
    _live_msgs[chat_id] = msg_id


def _stop_live(app: Application, chat_id: int) -> None:
    if app.job_queue:
        for job in app.job_queue.get_jobs_by_name(f"live_{chat_id}"):
            job.schedule_removal()
    _live_msgs.pop(chat_id, None)

# ── Segurança ──────────────────────────────────────────────────────────────────
async def _is_owner(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    if uid != _OWNER:
        if update.callback_query:
            await update.callback_query.answer("⛔ Acesso negado.", show_alert=True)
        return False
    return True

# ── /start ─────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_owner(update):
        return
    chat_id = update.effective_chat.id
    _stop_live(ctx.application, chat_id)
    _waiting_plugin.discard(_OWNER)
    if update.callback_query:
        await update.callback_query.edit_message_text(_txt_main(), reply_markup=_kb_main(), parse_mode="HTML")
    else:
        await update.message.reply_text(_txt_main(), reply_markup=_kb_main(), parse_mode="HTML")

# ── Upload de plugin ───────────────────────────────────────────────────────────
async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_owner(update):
        return
    uid = update.effective_user.id
    if uid not in _waiting_plugin:
        return

    doc = update.message.document
    if not doc.file_name.endswith(".py"):
        await update.message.reply_text("❌ Envie um arquivo <code>.py</code>.", parse_mode="HTML")
        return

    _waiting_plugin.discard(uid)
    dest     = _PLUGINS / doc.file_name
    tg_file  = await ctx.bot.get_file(doc.file_id)
    await tg_file.download_to_drive(dest)

    await update.message.reply_text(
        f"✅ Plugin <code>{doc.file_name}</code> instalado.\n"
        f"Reinicie o userbot para carregá-lo.",
        reply_markup=Markup([[
            Btn("🔄 Reiniciar agora", callback_data="ask_restart"),
            Btn("◀️ Menu",           callback_data="main"),
        ]]),
        parse_mode="HTML",
    )

# ── Callbacks ──────────────────────────────────────────────────────────────────
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_owner(update):
        return
    q       = update.callback_query
    data    = q.data
    chat_id = update.effective_chat.id

    # plugin_info usa popup — responde com alerta antes de retornar
    if data.startswith("plugin_info_"):
        name = data[len("plugin_info_"):]
        path = _PLUGINS / f"{name}.py"
        try:
            st    = path.stat()
            info  = f"📄 {name}.py\n{st.st_size:,} bytes · {datetime.fromtimestamp(st.st_mtime).strftime('%d/%m/%Y %H:%M')}"
        except Exception:
            info = f"📄 {name}.py\n(informação indisponível)"
        await q.answer(info, show_alert=True)
        return

    await q.answer()

    # ── Main ──────────────────────────────────────────────────────────────────
    if data == "main":
        _stop_live(ctx.application, chat_id)
        _waiting_plugin.discard(_OWNER)
        await q.edit_message_text(_txt_main(), reply_markup=_kb_main(), parse_mode="HTML")
        return

    # ── Status ────────────────────────────────────────────────────────────────
    if data == "status":
        await q.edit_message_text(_txt_status(), reply_markup=_kb_back(), parse_mode="HTML")
        return

    # ── Logs ──────────────────────────────────────────────────────────────────
    if data in ("logs", "logs_refresh"):
        hora = datetime.now().strftime("%H:%M:%S")
        await q.edit_message_text(
            f"<b>📋 Logs</b> · <code>{hora}</code>\n\n<pre>{_log_tail(30)}</pre>",
            reply_markup=_kb_logs(),
            parse_mode="HTML",
        )
        return

    if data == "logs_live":
        if not ctx.application.job_queue:
            await q.edit_message_text(
                "❌ Live mode requer APScheduler.\n"
                "<code>pip install apscheduler --break-system-packages</code>",
                reply_markup=_kb_back(), parse_mode="HTML",
            )
            return
        hora = datetime.now().strftime("%H:%M:%S")
        await q.edit_message_text(
            f"<b>📋 Logs</b> (🔴 Live · <code>{hora}</code>)\n\n<pre>{_log_tail(30)}</pre>",
            reply_markup=_kb_logs(live=True),
            parse_mode="HTML",
        )
        _start_live(ctx.application, chat_id, q.message.message_id)
        return

    if data == "logs_stop":
        _stop_live(ctx.application, chat_id)
        hora = datetime.now().strftime("%H:%M:%S")
        await q.edit_message_text(
            f"<b>📋 Logs</b> · <code>{hora}</code>\n\n<pre>{_log_tail(30)}</pre>",
            reply_markup=_kb_logs(),
            parse_mode="HTML",
        )
        return

    # ── Plugins ───────────────────────────────────────────────────────────────
    if data == "plugins":
        n = len(_list_plugins())
        await q.edit_message_text(
            f"<b>🔌 Plugins</b> ({n} carregados)\n\n"
            f"Toque no nome para ver info · 🗑️ para remover.\n"
            f"Reinicie o userbot após qualquer alteração.",
            reply_markup=_kb_plugins(),
            parse_mode="HTML",
        )
        return

    if data == "plugin_install":
        _waiting_plugin.add(_OWNER)
        await q.edit_message_text(
            "📥 <b>Instalar Plugin</b>\n\n"
            "Envie o arquivo <code>.py</code> agora.\n"
            "Pressione Voltar para cancelar.",
            reply_markup=_kb_back(),
            parse_mode="HTML",
        )
        return

    if data.startswith("plugin_del_confirm_"):
        name = data[len("plugin_del_confirm_"):]
        try:
            (_PLUGINS / f"{name}.py").unlink()
            msg = f"✅ <code>{name}.py</code> removido.\nReinicie o userbot para efetivar."
        except Exception as e:
            msg = f"❌ Erro ao remover: <code>{e}</code>"
        await q.edit_message_text(
            msg,
            reply_markup=Markup([[
                Btn("🔄 Reiniciar agora", callback_data="ask_restart"),
                Btn("◀️ Plugins",        callback_data="plugins"),
            ]]),
            parse_mode="HTML",
        )
        return

    if data.startswith("plugin_del_"):
        name = data[len("plugin_del_"):]
        await q.edit_message_text(
            f"⚠️ <b>Remover <code>{name}.py</code>?</b>\n\nO arquivo será deletado permanentemente.",
            reply_markup=Markup([[
                Btn("✅ Remover",  callback_data=f"plugin_del_confirm_{name}"),
                Btn("❌ Cancelar", callback_data="plugins"),
            ]]),
            parse_mode="HTML",
        )
        return

    # ── Sistema ───────────────────────────────────────────────────────────────
    if data in ("sistema", "sistema_refresh"):
        await q.edit_message_text(_txt_sistema(), reply_markup=_kb_sistema(), parse_mode="HTML")
        return

    # ── Config ────────────────────────────────────────────────────────────────
    if data == "config":
        await q.edit_message_text(_txt_config(), reply_markup=_kb_back(), parse_mode="HTML")
        return

    # ── Confirmações ──────────────────────────────────────────────────────────
    if data == "ask_restart":
        await q.edit_message_text(
            "⚠️ <b>Reiniciar o userbot?</b>\n\nFicará offline por alguns segundos.",
            reply_markup=_kb_confirm("restart", "Reiniciar"), parse_mode="HTML",
        )
        return

    if data == "ask_shutdown":
        await q.edit_message_text(
            "⚠️ <b>Desligar o userbot?</b>\n\nVocê precisará iniciá-lo manualmente.",
            reply_markup=_kb_confirm("shutdown", "Desligar"), parse_mode="HTML",
        )
        return

    if data == "ask_update":
        await q.edit_message_text(
            "⚠️ <b>Atualizar o userbot?</b>\n\nFará git pull e reiniciará.",
            reply_markup=_kb_confirm("update", "Atualizar"), parse_mode="HTML",
        )
        return

    # ── Execução ──────────────────────────────────────────────────────────────
    if data.startswith("do_"):
        action = data[3:]
        labels = {"restart": "Reiniciando", "shutdown": "Desligando", "update": "Atualizando"}
        await q.edit_message_text(f"⏳ {labels.get(action, action)}...", parse_mode="HTML")
        result = await _send_cmd(action)
        if result.get("status") == "ok":
            await q.edit_message_text(
                f"✅ <b>Executado</b>\n\n<code>{result.get('data', '')}</code>",
                reply_markup=_kb_back(), parse_mode="HTML",
            )
        else:
            await q.edit_message_text(
                f"⚠️ <b>Sem resposta do userbot</b>\n\n"
                f"<code>{result.get('data', 'timeout')}</code>",
                reply_markup=_kb_back(), parse_mode="HTML",
            )
        return

# ── Entry point ────────────────────────────────────────────────────────────────
def _launch_companion_userbot() -> None:
    """Sobe main.py junto se bot.py não foi iniciado por ele."""
    if os.environ.get("PANEL_CHILD"):
        return
    if not os.path.exists("main.py"):
        return
    import subprocess
    env = os.environ.copy()
    env["PANEL_CHILD"] = "1"
    try:
        subprocess.Popen([sys.executable, "main.py", "--debug"], env=env)
        print("⚙️ main.py iniciado como companion.")
    except Exception as e:
        print(f"⚠️ Falha ao iniciar main.py: {e}")


def main() -> None:
    print("🤖 Iniciando painel bot...")
    _launch_companion_userbot()
    app = Application.builder().token(_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.ALL & filters.User(_OWNER), handle_document))
    print(f"✅ Online — dono: {_OWNER}")
    print("   Envie /start para o bot no Telegram.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
