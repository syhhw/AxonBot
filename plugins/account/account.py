"""
plugins/account.py
Comandos de conta e monitoramento: afk, unafk, permit + handlers passivos (pm_permit, auto_unafk, monitor)

Créditos: ,afk é um padrão popularizado por TeamUltroid (Ultroid) no
ecossistema de userbots Telegram.
"""
import asyncio
import logging
import os
import random
import time
from datetime import datetime

logger = logging.getLogger("AxonBot.account")

from pyrogram import Client, enums, filters

from utils.commands import cmd
from utils.helpers import (
    alertar_dono_via_bot,
    carregar,
    prefixo,
    salvar,
    tr,
    verificar_admin,
)
from utils.i18n import tr_log
from utils.monitor_db import registrar as registrar_monitor

# Estado global do AFK (compartilhado dentro deste módulo)
AFK_ATIVO  = False
AFK_MOTIVO = ""
AFK_INICIO: float = 0.0
CAPTCHA_PENDENTE = {}
_AFK_ULTIMO_REPLY: dict[int, float] = {}
_AFK_COOLDOWN = 60          # segundos entre auto-respostas AFK para o mesmo usuário
_LOG_PM_COOLDOWN: dict[int, float] = {}
_LOG_PM_COOLDOWN_S = 300    # log de PM: apenas 1x por usuário a cada 5 minutos
_CAPTCHA_FALHAS: dict[int, int] = {}
_CAPTCHA_FALHAS_LIMITE = 3  # falhas seguidas antes de alertar o dono via bot

# Conta oficial de notificações de serviço do Telegram (códigos de login, avisos).
# Nunca deve receber captcha nem ter mensagens encaminhadas/logadas — contém dados sensíveis.
TELEGRAM_SERVICE_ID = 777000

# ── Textos editáveis pelo painel (/painel → Mensagens) ────────────────────────
# Override fica em "mensagens_custom" (carregar/salvar) — só as chaves que o
# dono realmente customizou; o resto cai no padrão bilíngue abaixo.
_MENSAGENS_PADRAO = {
    "firewall_intro": {
        "pt": "🛡️ **Firewall de Segurança**\n\nMensagens restritas. Para provar que é humano, resolva:",
        "en": "🛡️ **Security Firewall**\n\nRestricted messages. To prove you are human, solve this:",
    },
    "firewall_sucesso": {
        "pt": "✅ **Verificação concluída!** Você agora pode me enviar mensagens.",
        "en": "✅ **Verification complete!** You can now send me messages.",
    },
    "firewall_erro": {
        "pt": "❌ **Resposta incorreta.** Tente novamente.",
        "en": "❌ **Incorrect answer.** Try again.",
    },
    "firewall_bloqueado": {
        "pt": "Mensagens privadas estão temporariamente limitadas.",
        "en": "Private messages are temporarily limited.",
    },
    "afk_ativado": {
        "pt": "💤 **Modo AFK Ativado**\n└ 📝 **Motivo:** `{motivo}`",
        "en": "💤 **AFK Mode Activated**\n└ 📝 **Reason:** `{motivo}`",
    },
    "afk_resposta": {
        "pt": "💤 **Estou AFK há {tempo}**\n└ 📝 Motivo: `{motivo}`",
        "en": "💤 **I've been AFK for {tempo}**\n└ 📝 Reason: `{motivo}`",
    },
}

_CAPTCHA_PALAVRAS = ["BANANA", "FOGUETE", "PIRATA", "OCEANO", "MONTANHA", "GIRASSOL"]
_CAPTCHA_EMOJIS   = ["🍕", "🚀", "🐱", "⚽", "🎸", "🌵", "🎲", "🦊"]


def _msg(chave: str, **kwargs) -> str:
    """Busca o texto customizado no painel; cai pro padrão bilíngue se não houver."""
    custom = carregar("mensagens_custom", {})
    texto  = custom.get(chave)
    if not texto:
        padrao = _MENSAGENS_PADRAO.get(chave, {})
        texto  = tr(padrao.get("pt", ""), padrao.get("en", ""))
    try:
        return texto.format(**kwargs)
    except Exception:
        return texto


def _gerar_captcha() -> tuple[str, str]:
    """Gera (resposta_esperada, descrição_do_desafio) conforme captcha_tipo (painel)."""
    tipo = carregar("captcha_tipo", "math")
    if tipo == "palavra":
        palavra = random.choice(_CAPTCHA_PALAVRAS)
        return palavra, tr(f"Digite a palavra: **{palavra}**", f"Type the word: **{palavra}**")
    if tipo == "emoji":
        alvo = random.choice(_CAPTCHA_EMOJIS)
        return alvo, tr(f"Envie exatamente este emoji: {alvo}", f"Send exactly this emoji: {alvo}")
    n1, n2 = random.randint(1, 10), random.randint(1, 10)
    return str(n1 + n2), tr(f"Resolva a conta:\n👉 **{n1} + {n2} = ?**", f"Solve this:\n👉 **{n1} + {n2} = ?**")


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
    from plugins.drive.drive import obter_pasta as _obter_pasta
    return _obter_pasta(client, nome)


@cmd("afk")
async def cmd_afk(client, message):
    """Ativa o modo AFK com motivo opcional."""
    global AFK_ATIVO, AFK_MOTIVO, AFK_INICIO
    partes = message.text.split(None, 1)
    AFK_MOTIVO = partes[1].strip() if len(partes) > 1 else tr("Ausente.", "Away.")
    AFK_ATIVO  = True
    AFK_INICIO = time.time()
    await message.edit_text(_msg("afk_ativado", motivo=AFK_MOTIVO))


@cmd("unafk")
async def cmd_unafk(client, message):
    """Desativa o modo AFK manualmente."""
    global AFK_ATIVO
    tempo = _tempo_afk() if AFK_ATIVO else "—"
    AFK_ATIVO = False
    await message.edit_text(tr(
        f"✅ **Modo AFK desativado.**\n└ ⏱️ Ausente por: `{tempo}`",
        f"✅ **AFK Mode deactivated.**\n└ ⏱️ Away for: `{tempo}`"
    ))


@cmd("permit")
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
    """Bloqueia mensagens privadas de usuários não autorizados.

    Liga/desliga e lista de autorizados são configurados pelo painel bot
    (/painel → 🛡️ PM Permit) — mesma chave via utils.db, aplica na hora.
    """
    if not carregar("pm_firewall_ativo", True):
        return

    permitidos = carregar("permitidos.json", [])
    uid = message.from_user.id if message.from_user else message.chat.id

    if _e_conta_oficial(message.from_user, uid):
        return

    if uid not in permitidos:
        # Captcha desativado no painel: bloqueia sem desafio — só o dono
        # consegue liberar manualmente com ,permit ou pelo painel.
        if not carregar("captcha_ativo", True):
            try:
                await message.reply_text(_msg("firewall_bloqueado"))
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
            return

        if uid in CAPTCHA_PENDENTE:
            esperado = str(CAPTCHA_PENDENTE[uid]["resposta"]).strip().upper()
            recebido = (message.text or "").strip().upper()
            if recebido == esperado:
                permitidos.append(uid)
                salvar("permitidos.json", permitidos)
                del CAPTCHA_PENDENTE[uid]
                _CAPTCHA_FALHAS.pop(uid, None)
                await message.reply_text(_msg("firewall_sucesso"))
                message.stop_propagation()
                return
            else:
                falhas = _CAPTCHA_FALHAS.get(uid, 0) + 1
                _CAPTCHA_FALHAS[uid] = falhas
                await message.reply_text(_msg("firewall_erro"))
                if falhas >= _CAPTCHA_FALHAS_LIMITE:
                    sender = message.from_user
                    nome   = (sender.first_name if sender else None) or "?"
                    tag    = f" (@{sender.username})" if sender and sender.username else ""
                    cfg    = getattr(client, "config", {})
                    await alertar_dono_via_bot(cfg, (
                        f"⚠️ <b>Possível spam detectado</b>\n\n"
                        f"<code>{uid}</code> — {nome}{tag}\n"
                        f"Falhou o captcha {falhas}x seguidas tentando te mandar PV."
                    ))
                message.stop_propagation()
                return

        resposta, desafio = _gerar_captcha()
        CAPTCHA_PENDENTE[uid] = {"resposta": resposta}

        try:
            await message.reply_text(f"{_msg('firewall_intro')}\n{desafio}")
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

    # O handler só dispara pra PV ou menção (filtro no decorator), então aqui
    # já sabemos que é um ou outro.
    is_pm = message.chat.type == enums.ChatType.PRIVATE

    # Captura pro banco de relatórios (/painel → 📊 Relatórios) — desligável
    # separado do resto (perda de admin, auto-resposta AFK continuam
    # funcionando mesmo com o monitor de mensagens desativado).
    if carregar("monitor_ativo", True):
        registrar_monitor(
            tipo="pm" if is_pm else "mencao",
            chat_id=message.chat.id,
            chat_nome=None if is_pm else (message.chat.title or "?"),
            sender_id=uid_sender,
            sender_nome=(sender.first_name if sender else None) or "?",
            sender_username=sender.username if sender else None,
            texto=message.text or message.caption or "",
            tem_midia=bool(message.media),
        )

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
                await message.reply_text(_msg("afk_resposta", tempo=_tempo_afk(), motivo=AFK_MOTIVO))
            except Exception as e:
                logger.debug(f"[account.py] ignorado: {e}")

    if not log_id:
        return  # sem canal de logs, não há mais nada a fazer (forward e auto-upload dependem dele)

    # Encaminhamento pro canal de logs é opcional (/painel → 📊 Relatórios)
    # agora que o histórico completo já foi gravado no banco acima — mas isso
    # NÃO deve afetar o auto-upload pro Drive logo abaixo, que é um recurso
    # independente (só compartilha o mesmo log_id como pré-requisito).
    if carregar("monitor_forward_ativo", True):
        # Rate-limit do log para PMs: só encaminha a primeira mensagem de cada
        # remetente a cada 5 minutos — evita spam no canal quando alguém manda
        # várias mensagens seguidas.
        pode_encaminhar = True
        if is_pm:
            agora_log = time.time()
            if agora_log - _LOG_PM_COOLDOWN.get(uid_sender, 0) < _LOG_PM_COOLDOWN_S:
                pode_encaminhar = False
            else:
                _LOG_PM_COOLDOWN[uid_sender] = agora_log

        if pode_encaminhar:
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
                from plugins.drive.drive import obter_pasta
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
