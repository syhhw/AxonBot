"""
plugins/account.py
Comandos de conta e monitoramento: afk, unafk, permit + handlers passivos (pm_permit, auto_unafk, monitor)

Créditos: ,afk é um padrão popularizado por TeamUltroid (Ultroid) no
ecossistema de userbots Telegram.
"""
import logging
import os
import time
import asyncio
from datetime import datetime
logger = logging.getLogger("AxonBot.account")

from pyrogram import filters, enums, Client
from utils.helpers import cmd_filter, prefixo, carregar, salvar, verificar_admin, tr
from utils.i18n import tr_log

# Estado global do AFK (compartilhado dentro deste módulo)
AFK_ATIVO  = False
AFK_MOTIVO = ""
AFK_INICIO: float = 0.0
CAPTCHA_PENDENTE = {}
_AFK_ULTIMO_REPLY: dict[int, float] = {}
_AFK_COOLDOWN = 60          # segundos entre auto-respostas AFK para o mesmo usuário
_LOG_PM_COOLDOWN: dict[int, float] = {}
_LOG_PM_COOLDOWN_S = 300    # log de PM: apenas 1x por usuário a cada 5 minutos

# Conta oficial de notificações de serviço do Telegram (códigos de login, avisos).
# Nunca deve receber captcha nem ter mensagens encaminhadas/logadas — contém dados sensíveis.
TELEGRAM_SERVICE_ID = 777000


def _e_conta_oficial(sender, uid: int) -> bool:
    """Identifica contas oficiais/de serviço do Telegram (777000, suporte, verificadas).

    Encaminhar, forwardar ou até responder automaticamente mensagens dessas
    contas faz o Telegram enxergar o userbot "lendo" notificações de segurança
    (ex.: código de login), o que pode disparar bloqueios/atrasos ao tentar
    logar a conta em um novo aparelho. Por isso essas contas nunca são
    monitoradas, independente de qual handler passivo está rodando.
    """
    if uid == TELEGRAM_SERVICE_ID:
        return True
    if sender and (getattr(sender, "is_verified", False) or getattr(sender, "is_support", False)):
        return True
    return False


def _tempo_afk() -> str:
    """Retorna quanto tempo o AFK está ativo em formato legível."""
    s = int(time.time() - AFK_INICIO)
    if s < 60:
        return f"{s}s"
    m = s // 60
    if m < 60:
        return f"{m}min"
    h, mr = divmod(m, 60)
    if h < 24:
        return f"{h}h {mr}min" if mr else f"{h}h"
    d, hr = divmod(h, 24)
    return f"{d}d {hr}h"

CATEGORIAS = {
    '.apk': 'Apps', '.zip': 'Zips', '.rar': 'Zips', '.7z': 'Zips',
    '.exe': 'Windows', '.msi': 'Windows',
    '.mp4': 'Videos', '.mkv': 'Videos', '.avi': 'Videos',
    '.mp3': 'Audios', '.ogg': 'Audios', '.wav': 'Audios',
    '.pdf': 'Docs', '.docx': 'Docs', '.txt': 'Docs',
    '.jpg': 'Fotos', '.jpeg': 'Fotos', '.png': 'Fotos', '.gif': 'Fotos'
}


def obter_pasta(client, nome):
    from plugins.drive import obter_pasta as _obter_pasta
    return _obter_pasta(client, nome)


@Client.on_message(cmd_filter("afk") & filters.me)
async def cmd_afk(client, message):
    """Ativa o modo AFK com motivo opcional."""
    global AFK_ATIVO, AFK_MOTIVO, AFK_INICIO
    partes = message.text.split(None, 1)
    AFK_MOTIVO = partes[1].strip() if len(partes) > 1 else tr("Ausente.", "Away.")
    AFK_ATIVO  = True
    AFK_INICIO = time.time()
    await message.edit_text(tr(
        f"💤 **Modo AFK Ativado**\n└ 📝 **Motivo:** `{AFK_MOTIVO}`",
        f"💤 **AFK Mode Activated**\n└ 📝 **Reason:** `{AFK_MOTIVO}`"
    ))


@Client.on_message(cmd_filter("unafk") & filters.me)
async def cmd_unafk(client, message):
    """Desativa o modo AFK manualmente."""
    global AFK_ATIVO
    tempo = _tempo_afk() if AFK_ATIVO else "—"
    AFK_ATIVO = False
    await message.edit_text(tr(
        f"✅ **Modo AFK desativado.**\n└ ⏱️ Ausente por: `{tempo}`",
        f"✅ **AFK Mode deactivated.**\n└ ⏱️ Away for: `{tempo}`"
    ))


@Client.on_message(cmd_filter("permit") & filters.me)
async def cmd_permit(client, message):
    """Autoriza um usuário a enviar mensagens privadas."""
    if message.reply_to_message:
        if not message.reply_to_message.from_user:
            return await message.edit_text(tr("⚠️ Não foi possível identificar o usuário.", "⚠️ Could not identify the user."))
        uid = message.reply_to_message.from_user.id
    elif message.chat.type == enums.ChatType.PRIVATE:
        uid = message.chat.id
    else:
        return await message.edit_text(tr("⚠️ Use em PV ou responda a alguém.", "⚠️ Use in PM or reply to someone."))
    permitidos = carregar("permitidos.json", [])
    if uid not in permitidos:
        permitidos.append(uid)
        salvar("permitidos.json", permitidos)
    await message.edit_text(tr(f"✅ **PV autorizado para `{uid}`**", f"✅ **PM authorized for `{uid}`**"))


# ==========================================
# 📡 HANDLERS PASSIVOS (Monitoramento)
# ==========================================

@Client.on_message(filters.private & ~filters.me & ~filters.bot, group=-2)
async def pm_permit_checker(client, message):
    """Bloqueia mensagens privadas de usuários não autorizados."""
    permitidos = carregar("permitidos.json", [])
    uid = message.from_user.id if message.from_user else message.chat.id

    if _e_conta_oficial(message.from_user, uid):
        return

    if uid not in permitidos:
        if uid in CAPTCHA_PENDENTE:
            esperado = CAPTCHA_PENDENTE[uid]["resposta"]
            if message.text and message.text.strip() == str(esperado):
                permitidos.append(uid)
                salvar("permitidos.json", permitidos)
                del CAPTCHA_PENDENTE[uid]
                await message.reply_text(tr("✅ **Verificação concluída!** Você agora pode me enviar mensagens.", "✅ **Verification complete!** You can now send me messages."))
                message.stop_propagation()
                return
            else:
                await message.reply_text(tr("❌ **Resposta incorreta.** Tente novamente.", "❌ **Incorrect answer.** Try again."))
                message.stop_propagation()
                return
                
        import random
        n1 = random.randint(1, 10)
        n2 = random.randint(1, 10)
        CAPTCHA_PENDENTE[uid] = {"resposta": n1 + n2}
        
        try:
            await message.reply_text(tr(
                f"🛡️ **Firewall de Segurança**\n\nMensagens restritas. Para provar que é humano, resolva a conta:\n👉 **{n1} + {n2} = ?**",
                f"🛡️ **Security Firewall**\n\nRestricted messages. To prove you are human, solve this:\n👉 **{n1} + {n2} = ?**"
            ))
        except Exception as e:
            logger.debug(f"[account.py] ignorado: {e}")
        cfg = getattr(client, "config", {})
        log_id = cfg.get("ID_CANAL_LOGS")
        if log_id:
            try:
                await message.forward(log_id)
            except Exception as e:
                logger.debug(f"[account.py] ignorado: {e}")
        message.stop_propagation()


@Client.on_message(filters.me, group=-1)
async def auto_unafk(client, message):
    """Desativa o AFK automaticamente quando o usuário envia uma mensagem."""
    global AFK_ATIVO
    if AFK_ATIVO and message.text:
        p = prefixo(client)
        if not message.text.startswith(f"{p}afk"):
            tempo = _tempo_afk()
            AFK_ATIVO = False
            try:
                aviso = await message.reply_text(tr(
                    f"✅ **AFK desativado automaticamente.**\n└ ⏱️ Você ficou ausente por: `{tempo}`",
                    f"✅ **AFK automatically deactivated.**\n└ ⏱️ You were away for: `{tempo}`"
                ))
                await asyncio.sleep(4)
                await aviso.delete()
            except Exception as e:
                logger.debug(f"[account.py] ignorado: {e}")


@Client.on_message((filters.private | filters.mentioned) & ~filters.me)
async def monitor_central(client, message):
    """Monitora menções, PVs, perda de admin e faz auto-upload de arquivos."""
    cfg    = getattr(client, "config", {})
    log_id = cfg.get("ID_CANAL_LOGS")

    # Resolve sender logo de início (usado em múltiplos blocos abaixo)
    sender     = message.from_user
    uid_sender = sender.id if sender else 0

    if log_id and message.chat and message.chat.id == log_id:
        return

    # Conta oficial/de serviço do Telegram (códigos de login etc.) — nunca monitorar/encaminhar.
    if _e_conta_oficial(sender, uid_sender) or message.chat.id == TELEGRAM_SERVICE_ID:
        return

    ts = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Verifica perda de admin (apenas em grupos)
    if log_id and message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        cache = carregar("admin_cache.json", {})
        cid   = str(message.chat.id)
        if cid in cache and cache[cid].get("era_admin"):
            is_admin_atual = await verificar_admin(client, message.chat.id)
            if not is_admin_atual:
                try:
                    await client.send_message(log_id, tr_log(
                        f"⚠️ **PERDA DE CARGO**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"├ 💬 **Grupo:** {message.chat.title}\n"
                        f"├ 🆔 `{message.chat.id}`\n"
                        f"└ 🕐 `{ts}`",
                        f"⚠️ **DEMOTION ALERT**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"├ 💬 **Group:** {message.chat.title}\n"
                        f"├ 🆔 `{message.chat.id}`\n"
                        f"└ 🕐 `{ts}`",
                    ))
                except Exception as e:
                    logger.debug(f"[account.py] ignorado: {e}")
                cache[cid]["era_admin"] = False
                salvar("admin_cache.json", cache)

    # Auto-resposta AFK (com cooldown por usuário para evitar spam)
    global AFK_ATIVO, AFK_MOTIVO
    if AFK_ATIVO:
        agora_afk = time.time()
        if agora_afk - _AFK_ULTIMO_REPLY.get(uid_sender, 0) >= _AFK_COOLDOWN:
            _AFK_ULTIMO_REPLY[uid_sender] = agora_afk
            try:
                await message.reply_text(tr(
                    f"💤 **Estou AFK há {_tempo_afk()}**\n└ 📝 Motivo: `{AFK_MOTIVO}`",
                    f"💤 **I've been AFK for {_tempo_afk()}**\n└ 📝 Reason: `{AFK_MOTIVO}`"
                ))
            except Exception as e:
                logger.debug(f"[account.py] ignorado: {e}")

    if not log_id:
        return  # sem canal de logs, não há mais nada a fazer

    is_pm = message.chat.type == enums.ChatType.PRIVATE

    # Rate-limit do log para PMs: só encaminha a primeira mensagem de cada
    # remetente a cada 5 minutos — evita spam no canal quando alguém manda
    # várias mensagens seguidas.
    if is_pm:
        agora_log = time.time()
        if agora_log - _LOG_PM_COOLDOWN.get(uid_sender, 0) < _LOG_PM_COOLDOWN_S:
            return
        _LOG_PM_COOLDOWN[uid_sender] = agora_log

    # Cabeçalho de contexto + forward para o canal de logs
    if sender:
        nome     = sender.first_name or "?"
        mention  = f"[{nome}](tg://user?id={uid_sender})"
        user_tag = f" • @{sender.username}" if sender.username else ""
    else:
        mention  = tr_log("Desconhecido", "Unknown")
        user_tag = ""

    tipo_icon  = "💬" if is_pm else "📣"
    tipo_label = tr_log(
        "Mensagem Privada" if is_pm else "Menção em Grupo",
        "Private Message"  if is_pm else "Group Mention",
    )
    chat_nome = tr_log("Chat Privado", "Private Chat") if is_pm else (message.chat.title or "?")

    header = tr_log(
        f"{tipo_icon} **{tipo_label}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"├ 👤 **De:** {mention}{user_tag}\n"
        f"├ 💬 **Em:** {chat_nome}\n"
        f"└ 🕐 `{ts}`",
        f"{tipo_icon} **{tipo_label}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"├ 👤 **From:** {mention}{user_tag}\n"
        f"├ 💬 **In:** {chat_nome}\n"
        f"└ 🕐 `{ts}`",
    )
    try:
        await client.send_message(log_id, header)
        await message.forward(log_id)
    except Exception as e:
        logger.debug(f"[account.py] ignorado: {e}")

    limite = cfg.get("LIMITE_AUTO_UPLOAD", 20971520)
    drive = getattr(client, "drive", None)
    if drive and message.document and message.document.file_size and message.document.file_size <= limite:
        path = None
        try:
            nome = message.document.file_name or f"doc_{message.id}"
            ext = os.path.splitext(nome)[1].lower()
            cat = CATEGORIAS.get(ext, 'Outros')
            path = await message.download()

            def upload_drive_sync():
                from plugins.drive import obter_pasta
                id_pasta = obter_pasta(client, cat)
                f_drive = drive.CreateFile({'title': os.path.basename(path), 'parents': [{'id': id_pasta}]})
                f_drive.SetContentFile(path)
                f_drive.Upload()

            await asyncio.to_thread(upload_drive_sync)
        except Exception as e:
            logger.debug(f"[account.py] ignorado: {e}")
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    logger.debug(f"[account.py] ignorado: {e}")
