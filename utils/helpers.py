"""
utils/helpers.py
Funções auxiliares compartilhadas por todos os plugins.

A camada de persistência (salvar/carregar/cache) vive em utils/db.py.
Este módulo re-exporta tudo de lá para manter compatibilidade com os
imports existentes nos plugins — nenhum plugin precisa mudar.
"""
import os
import sys
import time
import asyncio
import subprocess
import logging
from pyrogram import filters, enums
from pyrogram.handlers import MessageHandler
from utils.db import salvar, carregar       # re-export
from utils.i18n import tr, tr_log, get_lang, COMMAND_ALIASES

logger = logging.getLogger("AxonBotHelper")

__all__ = [
    # re-exports de utils.db
    "salvar", "carregar",
    # re-exports de utils.i18n
    "tr", "get_lang", "COMMAND_ALIASES",
    # próprios
    "deletar_depois", "prefixo", "listen", "cmd_filter",
    "verificar_admin", "auditoria", "resolver_alvo", "reiniciar_processo",
    "DEL_RAPIDO", "DEL_PADRAO", "DEL_LONGO",
]

# Tempos padrão de auto-delete de respostas (estilo `del_in` do plain-ub:
# github.com/thedragonsinn/plain-ub), pra não ter valor mágico solto em
# cada plugin. Usar com deletar_depois(message, DEL_*).
DEL_RAPIDO = 5    # confirmações/erros rápidos e de baixo interesse
DEL_PADRAO = 10   # confirmação padrão de uma ação (ban, mute, purge, etc.)
DEL_LONGO  = 30   # listagens e telas informativas maiores


def deletar_depois(message, tempo: int = 30) -> None:
    """Agenda a deleção de uma mensagem sem travar o event loop."""
    async def _tarefa():
        await asyncio.sleep(tempo)
        try:
            await message.delete()
        except Exception:
            pass
    asyncio.create_task(_tarefa())


def prefixo(client) -> str:
    return getattr(client, "PREFIXO", ",")


async def listen(client, chat_id: int, timeout: int = 30):
    """Aguarda a próxima mensagem enviada pelo próprio dono no chat."""
    loop = asyncio.get_event_loop()
    fut = loop.create_future()

    async def _handler(c, msg):
        if not fut.done():
            fut.set_result(msg)

    # filters.me garante que só a resposta do dono da conta aciona o listen
    h = MessageHandler(_handler, filters.chat(chat_id) & filters.me)
    client.add_handler(h, group=-100)
    try:
        return await asyncio.wait_for(asyncio.shield(fut), timeout=timeout)
    finally:
        try:
            client.remove_handler(h, group=-100)
        except Exception:
            pass


def cmd_filter(nome: str):
    """Cria filtro que aceita o comando em PT e EN independente do idioma configurado."""
    async def func(flt, client, message):
        if not message.text:
            return False
        p = prefixo(client)
        alias = COMMAND_ALIASES.get(nome, nome)
        for cmd in {nome, alias}:
            if message.text == f"{p}{cmd}" or message.text.startswith(f"{p}{cmd} "):
                chat = message.chat
                chat_name = (
                    getattr(chat, "title", None)
                    or getattr(chat, "first_name", "Private")
                )
                logger.info(f"CMD: {p}{cmd} | Chat: {chat_name} ({chat.id})")
                return True
        return False
    return filters.create(func)


async def verificar_admin(client, chat_id: int) -> bool:
    """Verifica se o userbot é admin no chat. Cache de 15 dias no SQLite."""
    agora = time.time()
    cid = str(chat_id)
    cache = carregar("admin_cache.json", {})
    if cid in cache and agora - cache[cid].get("checado_em", 0) < 1_296_000:
        return cache[cid].get("is_admin", False)
    try:
        m = await client.get_chat_member(chat_id, "me")
        is_admin = m.status in (
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        )
        cache[cid] = {"is_admin": is_admin, "checado_em": agora}
        salvar("admin_cache.json", cache)
        return is_admin
    except Exception:
        return False


_ACAO_EMOJI: dict[str, str] = {
    "BAN": "🔨", "UNBAN": "🔓", "MUTE": "🔇", "UNMUTE": "🔊",
    "GBAN": "☢️", "FBAN": "📡", "KICK": "👟", "WARN": "⚠️",
    "PIN": "📌", "UNPIN": "📌",
}


async def auditoria(client, acao: str, user, chat, motivo=None, msg_orig=None) -> None:
    """Envia log detalhado de moderação para o canal de logs."""
    cfg = getattr(client, "config", {})
    log_id = cfg.get("ID_CANAL_LOGS")
    if not log_id:
        return

    from datetime import datetime
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")

    emoji     = _ACAO_EMOJI.get(acao.upper(), "🛡️")
    nome      = getattr(user, "first_name", None) or tr_log("Desconhecido", "Unknown")
    uid       = getattr(user, "id", "?")
    username  = getattr(user, "username", None)
    chat_nome = getattr(chat, "title", None) or tr_log("Chat Privado", "Private Chat")
    chat_id   = getattr(chat, "id", "?")

    mention  = f"[{nome}](tg://user?id={uid})"
    user_tag = f" • @{username}" if username else ""

    txt = tr_log(
        f"{emoji} **{acao.upper()}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"├ 👤 **Alvo:** {mention}{user_tag}\n"
        f"├ 🆔 **ID:** `{uid}`\n"
        f"├ 💬 **Chat:** {chat_nome} (`{chat_id}`)\n",
        f"{emoji} **{acao.upper()}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"├ 👤 **Target:** {mention}{user_tag}\n"
        f"├ 🆔 **ID:** `{uid}`\n"
        f"├ 💬 **Chat:** {chat_nome} (`{chat_id}`)\n",
    )
    if motivo:
        txt += tr_log(f"├ 📝 **Motivo:** `{motivo}`\n", f"├ 📝 **Reason:** `{motivo}`\n")
    txt += f"└ 🕐 `{ts}`"

    try:
        await client.send_message(log_id, txt)
        if msg_orig:
            await msg_orig.forward(log_id)
    except Exception:
        pass


async def resolver_alvo(client, message):
    """
    Resolve o alvo de um comando de moderação (reply / @username / ID numérico).
    Retorna (user_obj, motivo, msg_origem) ou (None, None, None).
    """
    partes = message.text.split(None, 2)
    user_obj = None
    motivo = None
    msg_origem = None

    if message.reply_to_message and message.reply_to_message.from_user:
        user_obj = message.reply_to_message.from_user
        msg_origem = message.reply_to_message
        if len(partes) > 1:
            motivo = " ".join(partes[1:])
    elif len(partes) > 1:
        alvo = partes[1].strip()
        if len(partes) > 2:
            motivo = partes[2]
        try:
            # Aceita @user, user (sem @), ou ID numérico
            if alvo.lstrip("-").isdigit():
                query = int(alvo)
            elif alvo.startswith("@"):
                query = alvo
            else:
                query = f"@{alvo}"
            user_obj = await client.get_users(query)
        except Exception:
            return None, None, None

    return user_obj, motivo, msg_origem


def reiniciar_processo() -> None:
    """Reinicia o bot de forma limpa (Graceful Restart).

    Se rodando sob debug.py (DEBUG_PANEL=1), sai com código 42 para que o
    painel detecte e relance o processo sem encerrar o debug.
    """
    if os.environ.get("DEBUG_PANEL") == "1":
        os._exit(42)

    python = sys.executable
    args = sys.argv[:]
    # Um restart disparado de dentro do próprio bot (,restart/,atualizar) nunca
    # é uma execução manual nova — sempre força --background pra pular o
    # prompt interativo de main.py (input() trava/quebra com EOFError quando
    # não há terminal pra responder, derrubando o processo relançado).
    if "--background" not in args:
        args.append("--background")

    kwargs: dict = {"stdin": subprocess.DEVNULL}
    if os.name == "nt" and "--background" in args:
        python = python.replace("python.exe", "pythonw.exe")
        if not os.path.exists(python):
            python = sys.executable
        kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
    subprocess.Popen([python] + args, **kwargs)
    os._exit(0)
