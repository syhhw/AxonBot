#!/usr/bin/env python3
"""
bot.py — Kira Antispam · Gerenciamento de grupos + painel de manutenção do Userbot Pro.

Uso:    python bot.py
Requer: BOT_TOKEN e DONO_ID definidos em config.json

Recursos públicos:
  /start /help /id /info

Moderação (admins do grupo):
  /ban /unban /kick /mute /unmute /warn /unwarn /warns /resetwarns /pin /unpin

Gerenciamento (admins do grupo):
  /setwelcome /clearwelcome /welcome
  /note /notes /delnote  (recuperar: #nomedanota)
  /filter /stop /filters
  /addbl /unblacklist /blacklist

Painel admin (apenas dono — acessado via /painel ou botão em /start):
  Status, Logs (live), Plugins, Sistema, Config, Reiniciar/Atualizar/Desligar
"""
import json
import time
import os
import sys
import re
import asyncio
from datetime import datetime
from pathlib import Path

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from telegram import (
    Update,
    InlineKeyboardButton as Btn,
    InlineKeyboardMarkup as Markup,
    ChatPermissions,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    filters as tfilters,
    ContextTypes,
)
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import BadRequest, Forbidden

# ── Config ─────────────────────────────────────────────────────────────────────
try:
    with open("config.json", "r", encoding="utf-8") as _f:
        _cfg = json.load(_f)
except FileNotFoundError:
    raise SystemExit("❌  config.json não encontrado.")
except json.JSONDecodeError as _e:
    raise SystemExit(f"❌  config.json malformado: {_e}")

_TOKEN = _cfg.get("BOT_TOKEN", "")
_OWNER = int(_cfg.get("DONO_ID", 0))

if not _TOKEN:
    raise SystemExit("❌  BOT_TOKEN ausente em config.json.")
if not _OWNER:
    raise SystemExit("❌  DONO_ID ausente em config.json.")

_CMD      = "_panel_cmd.json"
_RESULT   = "_panel_result.json"
_STATUS   = "_panel_status.json"
_LOG      = "userbot.log"
_PLUGINS  = Path("plugins")
_STALE    = 60
_DATA_DIR = Path("bot_data")
_DATA_DIR.mkdir(exist_ok=True)

_MUTE_PERMS   = ChatPermissions(can_send_messages=False)
_UNMUTE_PERMS = ChatPermissions(
    can_send_messages=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)

# ── Estado global ──────────────────────────────────────────────────────────────
_live_msgs: dict[int, int] = {}
_waiting_plugin: set[int] = set()

# ── Persistência de dados do grupo ─────────────────────────────────────────────
def _data_path(name: str) -> Path:
    return _DATA_DIR / name


def _load(name: str) -> dict:
    p = _data_path(name)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(name: str, data: dict) -> None:
    try:
        _data_path(name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _gid(chat_id: int) -> str:
    return str(chat_id)

def _get_groups()     -> dict: return _load("groups.json")
def _save_groups(d)   -> None: _save("groups.json", d)
def _get_notes()      -> dict: return _load("notes.json")
def _save_notes(d)    -> None: _save("notes.json", d)
def _get_filters()    -> dict: return _load("filters.json")
def _save_filters(d)  -> None: _save("filters.json", d)
def _get_blacklist()  -> dict: return _load("blacklist.json")
def _save_blacklist(d)-> None: _save("blacklist.json", d)
def _get_warns()      -> dict: return _load("warns.json")
def _save_warns(d)    -> None: _save("warns.json", d)

# ── IPC ─────────────────────────────────────────────────────────────────────────
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
    return {"status": "timeout", "data": "O userbot não respondeu ao decreto."}

# ── Formatadores ────────────────────────────────────────────────────────────────
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

# ── Permissões ──────────────────────────────────────────────────────────────────
async def _is_owner(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    if uid != _OWNER:
        if update.callback_query:
            await update.callback_query.answer("⛔ Acesso negado. Este poder pertence apenas a Kira.", show_alert=True)
        return False
    return True


async def _is_group_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return False
    if user.id == _OWNER:
        return True
    try:
        member = await ctx.bot.get_chat_member(chat.id, user.id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def _resolve_target(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> tuple[int | None, str, bool]:
    """Resolve o usuário alvo. Retorna (user_id, name, via_reply).
    via_reply=True → todos os ctx.args são motivo.
    via_reply=False → ctx.args[0] é o usuário; ctx.args[1:] é o motivo.
    """
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        u = msg.reply_to_message.from_user
        return u.id, u.first_name, True

    args = ctx.args
    if not args:
        return None, "", False

    raw = args[0].lstrip("@")
    chat_id = update.effective_chat.id

    # 1) get_chat_member no grupo atual — resolve qualquer membro/banido do grupo
    try:
        target = int(raw) if raw.isdigit() else f"@{raw}"
        member = await ctx.bot.get_chat_member(chat_id, target)
        u = member.user
        return u.id, u.first_name or raw, False
    except Exception:
        pass

    # 2) get_chat global — funciona se o bot já viu o usuário antes
    try:
        u = await ctx.bot.get_chat(raw)
        return u.id, u.first_name or raw, False
    except Exception:
        pass

    return None, "", False


def _reason(ctx: ContextTypes.DEFAULT_TYPE, via_reply: bool, default: str = "Nenhum motivo declarado.") -> str:
    if not ctx.args:
        return default
    return " ".join(ctx.args if via_reply else ctx.args[1:]) or default

# ── Textos e teclados do painel ─────────────────────────────────────────────────
def _txt_main() -> str:
    st     = _read_status()
    online = st.get("online", False)
    versao = st.get("versao", "2.3")
    ts     = st.get("ts", 0)
    hora   = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "—"
    ic     = "🟢" if online else "🔴"
    return (
        f"<b>📓 Kira — Painel de Controle</b>\n"
        f"<i>Userbot Pro v{versao}</i>\n\n"
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
        f"<b>📊 Status do Reino</b>\n\n"
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
        f"<b>💻 Recursos do Sistema</b>\n\n"
        f"├ 🖥️ CPU:   <code>{_bar(cpu)} {cpu}%</code>\n"
        f"├ 🧠 RAM:   <code>{_bar(ram_p)} {ram_u}/{ram_t} MB</code>\n"
        f"├ 💾 Disco: <code>{_bar(disk)} {disk}%</code>\n"
        f"├ ⏱ Uptime: <code>{_uptime(st.get('uptime_s', 0))}</code>\n"
        f"└ 🕐 {hora}"
    )


def _txt_config() -> str:
    limit    = _cfg.get("LIMITE_AUTO_UPLOAD", 0)
    limit_mb = f"{limit // 1024 // 1024} MB" if limit else "—"
    drive    = "✅ Ativo"       if _cfg.get("ID_PASTA_RAIZ_DRIVE") else "❌ Inativo"
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


def _kb_main() -> Markup:
    ic = "🟢" if _read_status().get("online") else "🔴"
    return Markup([
        [Btn(f"{ic} Status",  callback_data="status"),      Btn("📋 Logs",      callback_data="logs")],
        [Btn("🔌 Plugins",    callback_data="plugins"),     Btn("💻 Sistema",   callback_data="sistema")],
        [Btn("⚙️ Config",     callback_data="config")],
        [Btn("🔄 Reiniciar",  callback_data="ask_restart"), Btn("⬆️ Atualizar", callback_data="ask_update")],
        [Btn("🛑 Desligar",   callback_data="ask_shutdown")],
        [Btn("❌ Fechar",     callback_data="panel_close")],
    ])


def _kb_back() -> Markup:
    return Markup([[Btn("◀️ Voltar", callback_data="panel_main")]])


def _kb_confirm(action: str, label: str) -> Markup:
    return Markup([[
        Btn(f"✅ {label}", callback_data=f"do_{action}"),
        Btn("❌ Cancelar",  callback_data="panel_main"),
    ]])


def _kb_logs(live: bool = False) -> Markup:
    if live:
        return Markup([[Btn("⏹ Parar Live", callback_data="logs_stop"), Btn("◀️ Voltar", callback_data="panel_main")]])
    return Markup([[
        Btn("🔄 Atualizar",  callback_data="logs_refresh"),
        Btn("📡 Live",       callback_data="logs_live"),
        Btn("◀️ Voltar",    callback_data="panel_main"),
    ]])


def _kb_plugins() -> Markup:
    rows = []
    for name in _list_plugins():
        rows.append([
            Btn(f"🔌 {name}", callback_data=f"plugin_info_{name}"),
            Btn("🗑️",          callback_data=f"plugin_del_{name}"),
        ])
    rows.append([Btn("📥 Instalar módulo", callback_data="plugin_install")])
    rows.append([Btn("◀️ Voltar", callback_data="panel_main")])
    return Markup(rows)


def _kb_sistema() -> Markup:
    return Markup([[Btn("🔄 Atualizar", callback_data="sistema_refresh"), Btn("◀️ Voltar", callback_data="panel_main")]])

# ── Live log ─────────────────────────────────────────────────────────────────────
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
            parse_mode=ParseMode.HTML,
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

# ─────────────────────────────────────────────────────────────────────────────
# COMANDOS PÚBLICOS
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    txt = (
        f"👁️ <b>Eu sou Kira.</b>\n\n"
        f"Olá, <b>{user.first_name}</b>. Você entrou no Novo Mundo.\n\n"
        f"Neste grupo, os inocentes vivem sob minha proteção.\n"
        f"Os culpados... terão seus nomes escritos.\n\n"
        f"Use /help para conhecer as leis deste mundo."
    )
    kb = None
    if user.id == _OWNER:
        kb = Markup([[Btn("📓 Painel de Kira", callback_data="panel_main")]])
    await update.message.reply_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    txt = (
        "<b>📓 As Leis do Novo Mundo</b>\n\n"
        "<i>Quem segue as regras existe em paz.\n"
        "Quem ousa quebrá-las... será julgado.</i>\n\n"
        "<b>⚖️ Punições</b> <i>(aliados de Kira — admins):</i>\n"
        "• /ban — Sentença definitiva no Death Note\n"
        "• /unban — Clemência de Kira\n"
        "• /kick — Expulsão do reino\n"
        "• /mute [tempo] — Silêncio forçado\n"
        "• /unmute — Voz restaurada\n"
        "• /warn — Aviso formal (3 = sentença)\n"
        "• /unwarn — Aviso revogado\n"
        "• /warns — Consultar registros\n"
        "• /resetwarns — Apagar registros\n"
        "• /pin /unpin — Fixar / remover decretos\n\n"
        "<b>🏛️ Governança</b> <i>(admins):</i>\n"
        "• /setwelcome [texto] — Mensagem de chegada\n"
        "  Variáveis: {name} {username} {id} {chat}\n"
        "• /clearwelcome /welcome\n"
        "• /note [nome] [texto] — Salvar decreto\n"
        "• /notes /delnote — Listar / apagar\n"
        "• #nome — Recuperar decreto\n"
        "• /filter [palavra] [resposta] — Resposta automática\n"
        "• /stop [palavra] /filters\n"
        "• /addbl /unblacklist /blacklist\n\n"
        "<b>ℹ️ Gerais:</b>\n"
        "• /id — Consultar identidade\n"
        "• /info — Ficha completa"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def cmd_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        u = msg.reply_to_message.from_user
        await msg.reply_text(
            f"🪪 <b>Identidade registrada</b>\n\n"
            f"├ Nome: <b>{u.first_name}</b>\n"
            f"├ ID: <code>{u.id}</code>\n"
            f"└ Username: @{u.username or '—'}",
            parse_mode=ParseMode.HTML,
        )
    else:
        u = update.effective_user
        await msg.reply_text(
            f"🪪 <b>Sua identidade</b>\n\n"
            f"├ ID: <code>{u.id}</code>\n"
            f"└ Chat ID: <code>{update.effective_chat.id}</code>",
            parse_mode=ParseMode.HTML,
        )


async def cmd_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg    = update.effective_message
    target = msg.reply_to_message.from_user if msg.reply_to_message else update.effective_user
    chat   = update.effective_chat
    txt    = (
        f"📋 <b>Ficha do Suspeito</b>\n\n"
        f"├ Nome: <b>{target.first_name} {target.last_name or ''}</b>\n"
        f"├ Username: @{target.username or '—'}\n"
        f"├ ID: <code>{target.id}</code>\n"
        f"├ Bot: {'Sim' if target.is_bot else 'Não'}\n"
    )
    if chat.type in ("group", "supergroup"):
        try:
            member = await ctx.bot.get_chat_member(chat.id, target.id)
            status_map = {
                ChatMemberStatus.OWNER:         "👑 Dono",
                ChatMemberStatus.ADMINISTRATOR: "⭐ Admin",
                ChatMemberStatus.MEMBER:        "👤 Membro",
                ChatMemberStatus.RESTRICTED:    "🔇 Restrito",
                ChatMemberStatus.LEFT:          "🚪 Saiu",
                ChatMemberStatus.BANNED:        "☠️ Banido",
            }
            txt += f"└ Status: {status_map.get(member.status, member.status)}"
        except Exception:
            pass
    await msg.reply_text(txt, parse_mode=ParseMode.HTML)

# ─────────────────────────────────────────────────────────────────────────────
# MODERAÇÃO
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem executar este julgamento.")
    uid, name, via_reply = await _resolve_target(update, ctx)
    if not uid:
        return await update.message.reply_text("⚠️ Responda à mensagem do alvo ou informe @username / ID.")
    reason = _reason(ctx, via_reply)
    try:
        await ctx.bot.ban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(
            f"📓 <b>Sentença: CULPADO.</b>\n\n"
            f"O nome de <b>{name}</b> (<code>{uid}</code>) foi escrito no Death Note.\n"
            f"└ Motivo: {reason}\n\n"
            f"<i>Que a justiça de Kira seja eterna.</i>",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        await update.message.reply_text(f"❌ Falha ao executar sentença: {e}")


async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem executar este julgamento.")
    uid, name, _ = await _resolve_target(update, ctx)
    if not uid:
        return await update.message.reply_text("⚠️ Responda à mensagem do alvo ou informe @username / ID.")
    try:
        await ctx.bot.unban_chat_member(update.effective_chat.id, uid, only_if_banned=True)
        await update.message.reply_text(
            f"⚖️ <b>Kira concedeu clemência.</b>\n\n"
            f"<b>{name}</b> (<code>{uid}</code>) foi libertado do Death Note.\n"
            f"<i>Que não ouse cruzar o caminho da justiça novamente.</i>",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        await update.message.reply_text(f"❌ Falha ao revogar sentença: {e}")


async def cmd_kick(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem executar este julgamento.")
    uid, name, via_reply = await _resolve_target(update, ctx)
    if not uid:
        return await update.message.reply_text("⚠️ Responda à mensagem do alvo ou informe @username / ID.")
    reason = _reason(ctx, via_reply)
    try:
        await ctx.bot.ban_chat_member(update.effective_chat.id, uid)
        await ctx.bot.unban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(
            f"👢 <b>Expulsão decretada.</b>\n\n"
            f"<b>{name}</b> (<code>{uid}</code>) foi removido deste mundo.\n"
            f"└ Motivo: {reason}",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        await update.message.reply_text(f"❌ Falha ao executar expulsão: {e}")


def _parse_duration(text: str | None) -> int | None:
    if not text:
        return None
    m = re.fullmatch(r"(\d+)([mhd])", text.lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return n * {"m": 60, "h": 3600, "d": 86400}[unit]


async def cmd_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem executar este julgamento.")
    uid, name, via_reply = await _resolve_target(update, ctx)
    if not uid:
        return await update.message.reply_text("⚠️ Responda à mensagem do alvo ou informe @username / ID.")
    dur_str = (ctx.args[0] if via_reply else ctx.args[1]) if ctx.args and len(ctx.args) > (0 if via_reply else 1) else None
    dur_s   = _parse_duration(dur_str)
    until   = datetime.fromtimestamp(time.time() + dur_s) if dur_s else None
    dur_txt = dur_str or "indefinido"
    try:
        await ctx.bot.restrict_chat_member(update.effective_chat.id, uid, _MUTE_PERMS, until_date=until)
        await update.message.reply_text(
            f"🤐 <b>Silêncio imposto.</b>\n\n"
            f"A voz de <b>{name}</b> foi calada por <code>{dur_txt}</code>.\n"
            f"<i>Apenas os dignos têm o direito de falar no Novo Mundo.</i>",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        await update.message.reply_text(f"❌ Falha ao impor silêncio: {e}")


async def cmd_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem executar este julgamento.")
    uid, name, _ = await _resolve_target(update, ctx)
    if not uid:
        return await update.message.reply_text("⚠️ Responda à mensagem do alvo ou informe @username / ID.")
    try:
        await ctx.bot.restrict_chat_member(update.effective_chat.id, uid, _UNMUTE_PERMS)
        await update.message.reply_text(
            f"🔊 <b>Kira restaurou sua voz.</b>\n\n"
            f"<b>{name}</b> pode falar novamente — <i>por enquanto.</i>",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        await update.message.reply_text(f"❌ Falha ao restaurar voz: {e}")


async def cmd_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem executar este julgamento.")
    uid, name, via_reply = await _resolve_target(update, ctx)
    if not uid:
        return await update.message.reply_text("⚠️ Responda à mensagem do alvo ou informe @username / ID.")
    reason = _reason(ctx, via_reply)

    gid    = _gid(update.effective_chat.id)
    warns  = _get_warns()
    limit  = _get_groups().get(gid, {}).get("warns_limit", 3)
    warns.setdefault(gid, {})[str(uid)] = warns.get(gid, {}).get(str(uid), 0) + 1
    count  = warns[gid][str(uid)]
    _save_warns(warns)

    if count >= limit:
        try:
            await ctx.bot.ban_chat_member(update.effective_chat.id, uid)
        except Exception:
            pass
        warns[gid][str(uid)] = 0
        _save_warns(warns)
        await update.message.reply_text(
            f"📓 <b>{name}</b> acumulou {limit} avisos.\n\n"
            f"Seu nome foi escrito. A sentença foi cumprida.\n"
            f"<i>Eu sou a justiça.</i>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"⚠️ <b>Aviso formal de Kira.</b>\n\n"
            f"<b>{name}</b> — este é seu <b>{count}º</b> aviso (<code>{count}/{limit}</code>).\n"
            f"└ Motivo: {reason}\n\n"
            f"<i>Ao atingir {limit} avisos, o Death Note entra em ação.</i>",
            parse_mode=ParseMode.HTML,
        )


async def cmd_unwarn(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem executar este julgamento.")
    uid, name, _ = await _resolve_target(update, ctx)
    if not uid:
        return await update.message.reply_text("⚠️ Responda à mensagem do alvo ou informe @username / ID.")
    gid   = _gid(update.effective_chat.id)
    warns = _get_warns()
    cur   = warns.get(gid, {}).get(str(uid), 0)
    if cur == 0:
        return await update.message.reply_text(f"ℹ️ <b>{name}</b> não possui avisos nos registros.", parse_mode=ParseMode.HTML)
    warns.setdefault(gid, {})[str(uid)] = max(0, cur - 1)
    _save_warns(warns)
    limit = _get_groups().get(gid, {}).get("warns_limit", 3)
    await update.message.reply_text(
        f"✂️ Um aviso de <b>{name}</b> foi apagado dos registros (<code>{cur - 1}/{limit}</code>).",
        parse_mode=ParseMode.HTML,
    )


async def cmd_warns(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid, name, _ = await _resolve_target(update, ctx)
    if not uid:
        uid  = update.effective_user.id
        name = update.effective_user.first_name
    gid   = _gid(update.effective_chat.id)
    count = _get_warns().get(gid, {}).get(str(uid), 0)
    limit = _get_groups().get(gid, {}).get("warns_limit", 3)
    await update.message.reply_text(
        f"📋 <b>Registro de {name}:</b> <code>{count}/{limit}</code> avisos acumulados.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_resetwarns(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem executar este julgamento.")
    uid, name, _ = await _resolve_target(update, ctx)
    if not uid:
        return await update.message.reply_text("⚠️ Responda à mensagem do alvo ou informe @username / ID.")
    gid   = _gid(update.effective_chat.id)
    warns = _get_warns()
    warns.setdefault(gid, {})[str(uid)] = 0
    _save_warns(warns)
    await update.message.reply_text(
        f"🗑️ Os registros de <b>{name}</b> foram apagados do Death Note.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_pin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem fixar decretos.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Responda à mensagem que deseja fixar como decreto.")
    try:
        await ctx.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await update.message.reply_text("📌 Decreto fixado por Kira.")
    except BadRequest as e:
        await update.message.reply_text(f"❌ Falha ao fixar decreto: {e}")


async def cmd_unpin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem remover decretos.")
    try:
        if update.message.reply_to_message:
            await ctx.bot.unpin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        else:
            await ctx.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📌 Decreto removido.")
    except BadRequest as e:
        await update.message.reply_text(f"❌ Falha ao remover decreto: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# BOAS-VINDAS
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_setwelcome(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem definir decretos.")
    partes = update.message.text.split(None, 1)
    if len(partes) < 2:
        return await update.message.reply_text(
            "⚠️ Use: /setwelcome [texto]\n"
            "Variáveis: {name} {username} {id} {chat}"
        )
    gid    = _gid(update.effective_chat.id)
    groups = _get_groups()
    groups.setdefault(gid, {})["welcome"] = partes[1]
    _save_groups(groups)
    await update.message.reply_text("✅ Mensagem de chegada ao Novo Mundo definida.")


async def cmd_clearwelcome(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem remover decretos.")
    gid    = _gid(update.effective_chat.id)
    groups = _get_groups()
    groups.get(gid, {}).pop("welcome", None)
    _save_groups(groups)
    await update.message.reply_text("✅ Mensagem de chegada removida dos decretos.")


async def cmd_welcome(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    gid = _gid(update.effective_chat.id)
    msg = _get_groups().get(gid, {}).get("welcome")
    if msg:
        await update.message.reply_text(f"📜 <b>Decreto de chegada atual:</b>\n\n{msg}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("ℹ️ Nenhum decreto de chegada definido neste reino.")


async def on_new_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat   = update.effective_chat
    gid    = _gid(chat.id)
    tmpl   = _get_groups().get(gid, {}).get("welcome")
    if not tmpl:
        return
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        text = tmpl.format(
            name=member.first_name,
            username=f"@{member.username}" if member.username else member.first_name,
            id=member.id,
            chat=chat.title or "",
        )
        try:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────────────────────
# NOTAS (DECRETOS)
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem registrar decretos.")
    partes = update.message.text.split(None, 2)
    if len(partes) < 3:
        return await update.message.reply_text("⚠️ Use: /note [nome] [texto]")
    gid   = _gid(update.effective_chat.id)
    notes = _get_notes()
    notes.setdefault(gid, {})[partes[1].lower()] = partes[2]
    _save_notes(notes)
    await update.message.reply_text(
        f"📜 Decreto <code>{partes[1].lower()}</code> registrado no Death Note.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    gid   = _gid(update.effective_chat.id)
    nlist = _get_notes().get(gid, {})
    if not nlist:
        return await update.message.reply_text("ℹ️ Nenhum decreto salvo neste reino.")
    txt = "📋 <b>Decretos deste reino:</b>\n\n" + "\n".join(f"• <code>#{k}</code>" for k in sorted(nlist))
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def cmd_delnote(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem apagar decretos.")
    if not ctx.args:
        return await update.message.reply_text("⚠️ Use: /delnote [nome]")
    gid   = _gid(update.effective_chat.id)
    notes = _get_notes()
    name  = ctx.args[0].lower()
    if notes.get(gid, {}).pop(name, None) is None:
        return await update.message.reply_text(
            f"❌ Decreto <code>{name}</code> não existe nos registros.", parse_mode=ParseMode.HTML
        )
    _save_notes(notes)
    await update.message.reply_text(f"🗑️ Decreto <code>{name}</code> apagado do Death Note.", parse_mode=ParseMode.HTML)


async def on_note_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg  = update.effective_message
    text = msg.text or msg.caption or ""
    m    = re.match(r"#(\w+)", text.strip())
    if not m:
        return
    gid  = _gid(update.effective_chat.id)
    name = m.group(1).lower()
    note = _get_notes().get(gid, {}).get(name)
    if note:
        await msg.reply_text(note, parse_mode=ParseMode.HTML)

# ─────────────────────────────────────────────────────────────────────────────
# FILTROS
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem definir filtros.")
    partes = update.message.text.split(None, 2)
    if len(partes) < 3:
        return await update.message.reply_text("⚠️ Use: /filter [palavra] [resposta]")
    gid     = _gid(update.effective_chat.id)
    fltrs   = _get_filters()
    keyword = partes[1].lower()
    fltrs.setdefault(gid, {})[keyword] = partes[2]
    _save_filters(fltrs)
    await update.message.reply_text(
        f"👁️ Filtro para <code>{keyword}</code> registrado.", parse_mode=ParseMode.HTML
    )


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem remover filtros.")
    if not ctx.args:
        return await update.message.reply_text("⚠️ Use: /stop [palavra]")
    gid     = _gid(update.effective_chat.id)
    fltrs   = _get_filters()
    keyword = ctx.args[0].lower()
    if fltrs.get(gid, {}).pop(keyword, None) is None:
        return await update.message.reply_text(
            f"❌ Filtro <code>{keyword}</code> não encontrado.", parse_mode=ParseMode.HTML
        )
    _save_filters(fltrs)
    await update.message.reply_text(f"✂️ Filtro <code>{keyword}</code> removido.", parse_mode=ParseMode.HTML)


async def cmd_filters(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    gid   = _gid(update.effective_chat.id)
    flist = _get_filters().get(gid, {})
    if not flist:
        return await update.message.reply_text("ℹ️ Nenhum filtro ativo neste reino.")
    txt = "🔍 <b>Filtros ativos neste reino:</b>\n\n" + "\n".join(f"• <code>{k}</code>" for k in sorted(flist))
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def on_filter_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg  = update.effective_message
    text = (msg.text or msg.caption or "").lower()
    if not text:
        return
    gid   = _gid(update.effective_chat.id)
    fltrs = _get_filters().get(gid, {})
    for keyword, response in fltrs.items():
        if keyword in text:
            try:
                await msg.reply_text(response, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            break

# ─────────────────────────────────────────────────────────────────────────────
# LISTA NEGRA
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_addbl(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem gerenciar a lista negra.")
    if not ctx.args:
        return await update.message.reply_text("⚠️ Use: /addbl [palavra(s)]")
    gid   = _gid(update.effective_chat.id)
    bl    = _get_blacklist()
    bl.setdefault(gid, [])
    added = []
    for word in ctx.args:
        w = word.lower()
        if w not in bl[gid]:
            bl[gid].append(w)
            added.append(w)
    _save_blacklist(bl)
    if added:
        await update.message.reply_text(
            f"🚫 Palavras banidas do Novo Mundo: <code>{', '.join(added)}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text("ℹ️ Essas palavras já constavam na lista negra.")


async def cmd_unblacklist(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_group_admin(update, ctx):
        return await update.message.reply_text("⛔ Apenas aliados de Kira podem gerenciar a lista negra.")
    if not ctx.args:
        return await update.message.reply_text("⚠️ Use: /unblacklist [palavra]")
    gid  = _gid(update.effective_chat.id)
    bl   = _get_blacklist()
    word = ctx.args[0].lower()
    if word in bl.get(gid, []):
        bl[gid].remove(word)
        _save_blacklist(bl)
        await update.message.reply_text(
            f"✅ <code>{word}</code> removida da lista negra.", parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            f"❌ <code>{word}</code> não consta na lista negra.", parse_mode=ParseMode.HTML
        )


async def cmd_blacklist(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    gid = _gid(update.effective_chat.id)
    bl  = _get_blacklist().get(gid, [])
    if not bl:
        return await update.message.reply_text("ℹ️ A lista negra deste reino está vazia.")
    txt = "🚫 <b>Palavras banidas do Novo Mundo:</b>\n\n" + "\n".join(f"• <code>{w}</code>" for w in sorted(bl))
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def on_blacklist_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg  = update.effective_message
    text = (msg.text or msg.caption or "").lower()
    if not text:
        return
    gid  = _gid(update.effective_chat.id)
    bl   = _get_blacklist().get(gid, [])
    for word in bl:
        if word in text:
            try:
                await msg.delete()
                await ctx.bot.send_message(
                    update.effective_chat.id,
                    f"📓 A mensagem de <b>{msg.from_user.first_name if msg.from_user else 'um usuário'}</b> "
                    f"foi removida. Palavras proibidas não existem no Novo Mundo.",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
            break

# ─────────────────────────────────────────────────────────────────────────────
# PAINEL ADMIN — oculto, apenas dono
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_owner(update):
        return
    chat_id = update.effective_chat.id
    _stop_live(ctx.application, chat_id)
    _waiting_plugin.discard(_OWNER)
    await update.message.reply_text(_txt_main(), reply_markup=_kb_main(), parse_mode=ParseMode.HTML)


async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_owner(update):
        return
    uid = update.effective_user.id
    if uid not in _waiting_plugin:
        return
    doc = update.message.document
    if not doc.file_name.endswith(".py"):
        await update.message.reply_text("❌ Envie um arquivo <code>.py</code>.", parse_mode=ParseMode.HTML)
        return
    _waiting_plugin.discard(uid)
    dest    = _PLUGINS / doc.file_name
    tg_file = await ctx.bot.get_file(doc.file_id)
    await tg_file.download_to_drive(dest)
    await update.message.reply_text(
        f"✅ Módulo <code>{doc.file_name}</code> instalado com sucesso.\n"
        f"Reinicie o userbot para ativá-lo.",
        reply_markup=Markup([[
            Btn("🔄 Reiniciar agora", callback_data="ask_restart"),
            Btn("◀️ Menu",           callback_data="panel_main"),
        ]]),
        parse_mode=ParseMode.HTML,
    )


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _is_owner(update):
        return
    q       = update.callback_query
    data    = q.data
    chat_id = update.effective_chat.id

    if data == "panel_close":
        await q.message.delete()
        return

    if data.startswith("plugin_info_"):
        name = data[len("plugin_info_"):]
        path = _PLUGINS / f"{name}.py"
        try:
            st   = path.stat()
            info = f"📄 {name}.py\n{st.st_size:,} bytes · {datetime.fromtimestamp(st.st_mtime).strftime('%d/%m/%Y %H:%M')}"
        except Exception:
            info = f"📄 {name}.py\n(informação indisponível)"
        await q.answer(info, show_alert=True)
        return

    await q.answer()

    if data in ("panel_main", "main"):
        _stop_live(ctx.application, chat_id)
        _waiting_plugin.discard(_OWNER)
        await q.edit_message_text(_txt_main(), reply_markup=_kb_main(), parse_mode=ParseMode.HTML)
        return

    if data == "status":
        await q.edit_message_text(_txt_status(), reply_markup=_kb_back(), parse_mode=ParseMode.HTML)
        return

    if data in ("logs", "logs_refresh"):
        hora = datetime.now().strftime("%H:%M:%S")
        await q.edit_message_text(
            f"<b>📋 Logs</b> · <code>{hora}</code>\n\n<pre>{_log_tail(30)}</pre>",
            reply_markup=_kb_logs(),
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "logs_live":
        if not ctx.application.job_queue:
            await q.edit_message_text(
                "❌ Live mode requer APScheduler.\n"
                "<code>pip install apscheduler --break-system-packages</code>",
                reply_markup=_kb_back(), parse_mode=ParseMode.HTML,
            )
            return
        hora = datetime.now().strftime("%H:%M:%S")
        await q.edit_message_text(
            f"<b>📋 Logs</b> (🔴 Live · <code>{hora}</code>)\n\n<pre>{_log_tail(30)}</pre>",
            reply_markup=_kb_logs(live=True),
            parse_mode=ParseMode.HTML,
        )
        _start_live(ctx.application, chat_id, q.message.message_id)
        return

    if data == "logs_stop":
        _stop_live(ctx.application, chat_id)
        hora = datetime.now().strftime("%H:%M:%S")
        await q.edit_message_text(
            f"<b>📋 Logs</b> · <code>{hora}</code>\n\n<pre>{_log_tail(30)}</pre>",
            reply_markup=_kb_logs(),
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "plugins":
        n = len(_list_plugins())
        await q.edit_message_text(
            f"<b>🔌 Módulos ativos</b> ({n} carregados)\n\n"
            f"Toque no nome para ver detalhes · 🗑️ para remover.\n"
            f"Reinicie o userbot após qualquer alteração.",
            reply_markup=_kb_plugins(),
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "plugin_install":
        _waiting_plugin.add(_OWNER)
        await q.edit_message_text(
            "📥 <b>Instalar Módulo</b>\n\n"
            "Envie o arquivo <code>.py</code> agora.\n"
            "Pressione Voltar para cancelar.",
            reply_markup=_kb_back(),
            parse_mode=ParseMode.HTML,
        )
        return

    if data.startswith("plugin_del_confirm_"):
        name = data[len("plugin_del_confirm_"):]
        try:
            (_PLUGINS / f"{name}.py").unlink()
            msg = f"✅ Módulo <code>{name}.py</code> removido.\nReinicie o userbot para efetivar."
        except Exception as e:
            msg = f"❌ Falha ao remover módulo: <code>{e}</code>"
        await q.edit_message_text(
            msg,
            reply_markup=Markup([[
                Btn("🔄 Reiniciar agora", callback_data="ask_restart"),
                Btn("◀️ Módulos",        callback_data="plugins"),
            ]]),
            parse_mode=ParseMode.HTML,
        )
        return

    if data.startswith("plugin_del_"):
        name = data[len("plugin_del_"):]
        await q.edit_message_text(
            f"⚠️ <b>Remover <code>{name}.py</code>?</b>\n\nO módulo será deletado permanentemente.",
            reply_markup=Markup([[
                Btn("✅ Remover",  callback_data=f"plugin_del_confirm_{name}"),
                Btn("❌ Cancelar", callback_data="plugins"),
            ]]),
            parse_mode=ParseMode.HTML,
        )
        return

    if data in ("sistema", "sistema_refresh"):
        await q.edit_message_text(_txt_sistema(), reply_markup=_kb_sistema(), parse_mode=ParseMode.HTML)
        return

    if data == "config":
        await q.edit_message_text(_txt_config(), reply_markup=_kb_back(), parse_mode=ParseMode.HTML)
        return

    if data == "ask_restart":
        await q.edit_message_text(
            "⚠️ <b>Reiniciar o userbot?</b>\n\nFicará offline por alguns segundos.",
            reply_markup=_kb_confirm("restart", "Reiniciar"), parse_mode=ParseMode.HTML,
        )
        return

    if data == "ask_shutdown":
        await q.edit_message_text(
            "⚠️ <b>Desligar o userbot?</b>\n\nVocê precisará iniciá-lo manualmente.",
            reply_markup=_kb_confirm("shutdown", "Desligar"), parse_mode=ParseMode.HTML,
        )
        return

    if data == "ask_update":
        await q.edit_message_text(
            "⚠️ <b>Atualizar o userbot?</b>\n\nFará git pull e reiniciará.",
            reply_markup=_kb_confirm("update", "Atualizar"), parse_mode=ParseMode.HTML,
        )
        return

    if data.startswith("do_"):
        action = data[3:]
        labels = {"restart": "Reiniciando", "shutdown": "Desligando", "update": "Atualizando"}
        await q.edit_message_text(f"⏳ {labels.get(action, action)}...", parse_mode=ParseMode.HTML)
        result = await _send_cmd(action)
        if result.get("status") == "ok":
            await q.edit_message_text(
                f"✅ <b>Executado</b>\n\n<code>{result.get('data', '')}</code>",
                reply_markup=_kb_back(), parse_mode=ParseMode.HTML,
            )
        else:
            await q.edit_message_text(
                f"⚠️ <b>O userbot não respondeu ao decreto</b>\n\n<code>{result.get('data', 'timeout')}</code>",
                reply_markup=_kb_back(), parse_mode=ParseMode.HTML,
            )
        return

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def _launch_companion_userbot() -> None:
    if os.environ.get("PANEL_CHILD"):
        return
    import subprocess
    _dir    = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(_dir, "main.py")
    if not os.path.exists(main_py):
        print(f"⚠️ main.py não encontrado em {_dir}")
        return
    env = os.environ.copy()
    env["PANEL_CHILD"] = "1"
    try:
        proc = subprocess.Popen([sys.executable, main_py], env=env, cwd=_dir)
        print(f"⚙️ main.py iniciado (PID {proc.pid}).")
    except Exception as e:
        print(f"⚠️ Falha ao iniciar main.py: {e}")


def main() -> None:
    print("👁️ Kira Antispam iniciando...")
    _launch_companion_userbot()
    app = Application.builder().token(_TOKEN).build()

    # Públicos
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("id",     cmd_id))
    app.add_handler(CommandHandler("info",   cmd_info))

    # Moderação
    app.add_handler(CommandHandler("ban",        cmd_ban))
    app.add_handler(CommandHandler("unban",      cmd_unban))
    app.add_handler(CommandHandler("kick",       cmd_kick))
    app.add_handler(CommandHandler("mute",       cmd_mute))
    app.add_handler(CommandHandler("unmute",     cmd_unmute))
    app.add_handler(CommandHandler("warn",       cmd_warn))
    app.add_handler(CommandHandler("unwarn",     cmd_unwarn))
    app.add_handler(CommandHandler("warns",      cmd_warns))
    app.add_handler(CommandHandler("resetwarns", cmd_resetwarns))
    app.add_handler(CommandHandler("pin",        cmd_pin))
    app.add_handler(CommandHandler("unpin",      cmd_unpin))

    # Grupo
    app.add_handler(CommandHandler("setwelcome",   cmd_setwelcome))
    app.add_handler(CommandHandler("clearwelcome", cmd_clearwelcome))
    app.add_handler(CommandHandler("welcome",      cmd_welcome))
    app.add_handler(CommandHandler("note",         cmd_note))
    app.add_handler(CommandHandler("notes",        cmd_notes))
    app.add_handler(CommandHandler("delnote",      cmd_delnote))
    app.add_handler(CommandHandler("filter",       cmd_filter))
    app.add_handler(CommandHandler("stop",         cmd_stop))
    app.add_handler(CommandHandler("filters",      cmd_filters))
    app.add_handler(CommandHandler("addbl",        cmd_addbl))
    app.add_handler(CommandHandler("unblacklist",  cmd_unblacklist))
    app.add_handler(CommandHandler("blacklist",    cmd_blacklist))

    # Painel oculto
    app.add_handler(CommandHandler("painel", cmd_panel))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(tfilters.Document.ALL & tfilters.User(_OWNER), handle_document))

    # Handlers passivos
    app.add_handler(MessageHandler(tfilters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(MessageHandler(
        tfilters.TEXT & tfilters.Regex(r"^#\w+") & ~tfilters.COMMAND,
        on_note_request,
    ))
    app.add_handler(MessageHandler(
        (tfilters.TEXT | tfilters.CAPTION) & ~tfilters.COMMAND,
        on_blacklist_check,
    ), group=1)
    app.add_handler(MessageHandler(
        (tfilters.TEXT | tfilters.CAPTION) & ~tfilters.COMMAND,
        on_filter_check,
    ), group=2)

    print(f"✅ Online — dono: {_OWNER}")
    print("   /start · /help · /painel (oculto)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
