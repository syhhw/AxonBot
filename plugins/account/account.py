"""
plugins/account/account.py
Conta e firewall de PV: afk, unafk, permit, unpermit, permitidos, pmpermit,
captcha, monitor — mais os handlers passivos (pm_permit, auto_unafk, monitor).

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
    carregar,
    prefixo,
    salvar,
    tr,
    verificar_admin,
)
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
_CAPTCHA_FALHAS: dict[int, int] = {}
_CAPTCHA_FALHAS_LIMITE = 3  # falhas seguidas antes de avisar no canal de logs

# Conta oficial de notificações de serviço do Telegram (códigos de login, avisos).
# Nunca deve receber captcha nem ter mensagens encaminhadas/logadas — contém dados sensíveis.
TELEGRAM_SERVICE_ID = 777000

# Recursos que mexem com terceiros nascem DESLIGADOS: numa instalação nova
# ninguém leva bloqueio no PV e nenhuma mensagem privada é encaminhada pra
# lugar nenhum sem o dono ligar na mão (,pmpermit on / ,monitor on).
_FIREWALL_PADRAO = False
_MONITOR_PADRAO  = False
_CAPTCHA_PADRAO  = True   # só tem efeito quando o firewall está ligado

# ── Textos do firewall e do AFK ───────────────────────────────────────────────
_MENSAGENS = {
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
    """Texto bilíngue do firewall/AFK, já formatado."""
    padrao = _MENSAGENS.get(chave, {})
    texto  = tr(padrao.get("pt", ""), padrao.get("en", ""))
    try:
        return texto.format(**kwargs)
    except Exception:
        return texto


def _gerar_captcha() -> tuple[str, str]:
    """Gera (resposta_esperada, descrição_do_desafio) conforme o tipo em ,captcha."""
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


@cmd("unpermit")
async def cmd_unpermit(client, message):
    """Revoga a autorização de PV de um usuário."""
    if message.reply_to_message and message.reply_to_message.from_user:
        uid = message.reply_to_message.from_user.id
    elif message.chat.type == enums.ChatType.PRIVATE:
        uid = message.chat.id
    else:
        return await message.edit_text(tr("⚠️ Use em PV ou responda a alguém.", "⚠️ Use in PM or reply to someone."))

    permitidos = carregar("permitidos.json", [])
    if uid not in permitidos:
        return await message.edit_text(tr(f"ℹ️ `{uid}` não estava autorizado.", f"ℹ️ `{uid}` was not authorized."))
    permitidos.remove(uid)
    salvar("permitidos.json", permitidos)
    await message.edit_text(tr(f"🚫 **PV revogado para `{uid}`**", f"🚫 **PM revoked for `{uid}`**"))


@cmd("permitidos")
async def cmd_permitidos(client, message):
    """Lista os usuários autorizados a mandar PV."""
    permitidos = carregar("permitidos.json", [])
    if not permitidos:
        return await message.edit_text(tr("📋 Nenhum usuário autorizado ainda.", "📋 No authorized users yet."))
    linhas = "\n".join(f"├ `{uid}`" for uid in permitidos[:-1])
    linhas += f"\n└ `{permitidos[-1]}`" if linhas else f"└ `{permitidos[-1]}`"
    await message.edit_text(tr(
        f"📋 **Autorizados a mandar PV** ({len(permitidos)})\n{linhas}",
        f"📋 **Allowed to PM you** ({len(permitidos)})\n{linhas}",
    ))


_LIGAR    = ("on", "ligar", "1", "sim")
_DESLIGAR = ("off", "desligar", "0", "nao", "não")


def _aplicar_flag(chave: str, arg: str) -> bool | None:
    """Grava on/off numa flag persistida. Retorna o novo estado, ou None se
    o argumento não for reconhecido."""
    if arg in _LIGAR:
        novo = True
    elif arg in _DESLIGAR:
        novo = False
    else:
        return None
    salvar(chave, novo)
    return novo


def _estado(ativo: bool) -> str:
    return tr("ligado ✅", "on ✅") if ativo else tr("desligado ❌", "off ❌")


@cmd("pmpermit")
async def cmd_pmpermit(client, message):
    """Liga ou desliga o firewall de mensagens privadas."""
    p      = prefixo(client)
    partes = message.text.split(None, 1)

    if len(partes) < 2:
        ativo = carregar("pm_firewall_ativo", _FIREWALL_PADRAO)
        total = len(carregar("permitidos.json", []))
        return await message.edit_text(tr(
            f"🛡️ **Firewall de PV:** {_estado(ativo)}\n"
            f"└ {total} usuário(s) autorizado(s)\n\n`{p}pmpermit [on/off]`",
            f"🛡️ **PM firewall:** {_estado(ativo)}\n"
            f"└ {total} authorized user(s)\n\n`{p}pmpermit [on/off]`",
        ))

    novo = _aplicar_flag("pm_firewall_ativo", partes[1].strip().lower())
    if novo is None:
        return await message.edit_text(f"⚠️ `{p}pmpermit [on/off]`")
    await message.edit_text(tr(
        f"🛡️ **Firewall de PV {_estado(novo)}**",
        f"🛡️ **PM firewall {_estado(novo)}**",
    ))


@cmd("captcha")
async def cmd_captcha(client, message):
    """Liga/desliga o captcha do firewall e escolhe o tipo do desafio."""
    p      = prefixo(client)
    partes = message.text.split(None, 1)
    tipos  = {"math": "math", "conta": "math", "palavra": "palavra",
              "word": "palavra", "emoji": "emoji"}

    if len(partes) < 2:
        ativo = carregar("captcha_ativo", _CAPTCHA_PADRAO)
        tipo  = carregar("captcha_tipo", "math")
        return await message.edit_text(tr(
            f"🤖 **Captcha:** {_estado(ativo)}\n└ Tipo: `{tipo}`\n\n"
            f"`{p}captcha [on/off]`\n`{p}captcha [math/palavra/emoji]`",
            f"🤖 **Captcha:** {_estado(ativo)}\n└ Type: `{tipo}`\n\n"
            f"`{p}captcha [on/off]`\n`{p}captcha [math/word/emoji]`",
        ))

    arg = partes[1].strip().lower()
    if arg in tipos:
        salvar("captcha_tipo", tipos[arg])
        return await message.edit_text(tr(
            f"🤖 **Tipo de captcha:** `{tipos[arg]}`",
            f"🤖 **Captcha type:** `{tipos[arg]}`",
        ))

    novo = _aplicar_flag("captcha_ativo", arg)
    if novo is None:
        return await message.edit_text(f"⚠️ `{p}captcha [on/off/math/palavra/emoji]`")
    await message.edit_text(tr(f"🤖 **Captcha {_estado(novo)}**", f"🤖 **Captcha {_estado(novo)}**"))


@cmd("monitor")
async def cmd_monitor(client, message):
    """Liga/desliga o encaminhamento de PVs e menções pro canal de logs."""
    p      = prefixo(client)
    partes = message.text.split(None, 1)

    if len(partes) < 2:
        ativo = carregar("monitor_forward_ativo", _MONITOR_PADRAO)
        return await message.edit_text(tr(
            f"📡 **Encaminhar PVs/menções pro canal de logs:** {_estado(ativo)}\n\n`{p}monitor [on/off]`",
            f"📡 **Forward PMs/mentions to the log channel:** {_estado(ativo)}\n\n`{p}monitor [on/off]`",
        ))

    novo = _aplicar_flag("monitor_forward_ativo", partes[1].strip().lower())
    if novo is None:
        return await message.edit_text(f"⚠️ `{p}monitor [on/off]`")
    await message.edit_text(tr(
        f"📡 **Encaminhamento {_estado(novo)}**",
        f"📡 **Forwarding {_estado(novo)}**",
    ))


# ==========================================
# 📡 HANDLERS PASSIVOS (Monitoramento)
# ==========================================

@Client.on_message(filters.private & ~filters.me & ~filters.bot, group=-2)
async def pm_permit_checker(client, message):
    """Bloqueia mensagens privadas de usuários não autorizados.

    Liga/desliga em ,pmpermit, tipo do desafio em ,captcha, liberação
    manual em ,permit.
    """
    if not carregar("pm_firewall_ativo", _FIREWALL_PADRAO):
        return

    permitidos = carregar("permitidos.json", [])
    uid = message.from_user.id if message.from_user else message.chat.id

    if _e_conta_oficial(message.from_user, uid):
        return

    if uid not in permitidos:
        # Captcha desligado (,captcha off): bloqueia sem desafio — só o dono
        # libera, manualmente, com ,permit.
        if not carregar("captcha_ativo", _CAPTCHA_PADRAO):
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
                log_id = getattr(client, "config", {}).get("ID_CANAL_LOGS")
                if falhas >= _CAPTCHA_FALHAS_LIMITE and log_id:
                    sender = message.from_user
                    nome   = (sender.first_name if sender else None) or "?"
                    tag    = f" (@{sender.username})" if sender and sender.username else ""
                    try:
                        await client.send_message(log_id, tr_log(
                            f"⚠️ **Possível spam**\n`{uid}` — {nome}{tag}\n"
                            f"Errou o captcha {falhas}x seguidas tentando te mandar PV.",
                            f"⚠️ **Possible spam**\n`{uid}` — {nome}{tag}\n"
                            f"Failed the captcha {falhas} times in a row trying to PM you.",
                        ))
                    except Exception as e:
                        logger.debug(f"[account.py] ignorado: {e}")
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

    # Encaminhar PVs/menções pro canal de logs é opcional (,monitor on/off) e
    # NÃO afeta o auto-upload pro Drive logo abaixo, que é independente — os
    # dois só compartilham o log_id como pré-requisito.
    if carregar("monitor_forward_ativo", _MONITOR_PADRAO):
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
