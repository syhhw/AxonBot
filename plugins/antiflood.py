"""
plugins/antiflood.py
Controle de flood por grupo — detecta envio rápido de mensagens e muta
o usuário automaticamente. Unmute automático após 60 segundos.
"""
import asyncio
import time
from collections import defaultdict
from pyrogram import filters, Client
from pyrogram.types import ChatPermissions
from utils.helpers import cmd_filter, prefixo, carregar, salvar, tr


def _chave(chat_id: int) -> str:
    return f"antiflood_{chat_id}"


# Estado em memória: {(chat_id, user_id): [timestamps]}
_HISTORICO: dict = defaultdict(list)
# Usuários atualmente mutados para evitar double-mute
_MUTADOS: set = set()


async def _unmute_after(client, chat_id: int, user_id: int, delay: int = 60):
    await asyncio.sleep(delay)
    _MUTADOS.discard((chat_id, user_id))
    try:
        await client.restrict_chat_member(
            chat_id, user_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
    except Exception:
        pass


@Client.on_message(cmd_filter("setflood") & filters.me)
async def cmd_setflood(client, message):
    """Define o limite de mensagens por janela de 5s para este grupo."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2 or not partes[1].strip().isdigit():
        return await message.edit_text(tr(
            f"⚠️ **Uso:** `{p}setflood [número]`\n\n"
            f"Define quantas mensagens por 5 segundos um usuário pode enviar.\n"
            f"Recomendado: 5–10 mensagens.",
            f"⚠️ **Usage:** `{p}setflood [number]`\n\n"
            f"Sets how many messages per 5 seconds a user may send.\n"
            f"Recommended: 5–10 messages."
        ))
    limite = int(partes[1].strip())
    if limite < 2:
        return await message.edit_text(tr(
            "⚠️ Mínimo de 2 mensagens por limite.",
            "⚠️ Minimum limit is 2 messages."
        ))
    dados = carregar(_chave(message.chat.id), {})
    dados["limite"] = limite
    dados["ativo"] = True
    salvar(_chave(message.chat.id), dados)
    await message.edit_text(tr(
        f"✅ **Antiflood ativado!**\n"
        f"├ 🚨 Limite: `{limite}` mensagens / 5s\n"
        f"└ ⏱️ Punição: mute automático por 60s",
        f"✅ **Antiflood enabled!**\n"
        f"├ 🚨 Limit: `{limite}` messages / 5s\n"
        f"└ ⏱️ Penalty: auto-mute for 60s"
    ))


@Client.on_message(cmd_filter("noflood") & filters.me)
async def cmd_noflood(client, message):
    """Desativa o antiflood neste grupo."""
    dados = carregar(_chave(message.chat.id), {})
    dados["ativo"] = False
    salvar(_chave(message.chat.id), dados)
    await message.edit_text(tr(
        "🟢 **Antiflood desativado** neste grupo.",
        "🟢 **Antiflood disabled** in this group."
    ))


@Client.on_message(cmd_filter("flood") & filters.me)
async def cmd_floodstatus(client, message):
    """Mostra o status atual do antiflood neste grupo."""
    p = prefixo(client)
    dados = carregar(_chave(message.chat.id), {})
    if not dados or not dados.get("ativo"):
        return await message.edit_text(tr(
            f"🟢 **Antiflood inativo** neste grupo.\n"
            f"Use `{p}setflood [número]` para ativar.",
            f"🟢 **Antiflood inactive** in this group.\n"
            f"Use `{p}setflood [number]` to enable."
        ))
    await message.edit_text(tr(
        f"🚨 **Antiflood ativo**\n"
        f"└ Limite: `{dados['limite']}` mensagens / 5s",
        f"🚨 **Antiflood active**\n"
        f"└ Limit: `{dados['limite']}` messages / 5s"
    ))


@Client.on_message(filters.incoming & ~filters.me & ~filters.bot, group=3)
async def flood_watcher(client, message):
    """Monitora mensagens e muta usuários que ultrapassem o limite."""
    if not message.from_user:
        return
    dados = carregar(_chave(message.chat.id), {})
    if not dados or not dados.get("ativo"):
        return

    limite = dados.get("limite", 7)
    cid = message.chat.id
    uid = message.from_user.id

    if (cid, uid) in _MUTADOS:
        return

    agora = time.time()
    chave_hist = (cid, uid)
    _HISTORICO[chave_hist] = [t for t in _HISTORICO[chave_hist] if agora - t < 5]
    _HISTORICO[chave_hist].append(agora)

    if len(_HISTORICO[chave_hist]) >= limite:
        _HISTORICO[chave_hist].clear()
        _MUTADOS.add((cid, uid))

        nome = message.from_user.first_name or "Usuário"
        mention = f"[{nome}](tg://user?id={uid})"

        try:
            await client.restrict_chat_member(
                cid, uid,
                ChatPermissions(can_send_messages=False)
            )
            await client.send_message(cid, tr(
                f"🚨 **Flood detectado!** {mention} foi mutado por 60 segundos.",
                f"🚨 **Flood detected!** {mention} has been muted for 60 seconds."
            ))
        except Exception:
            _MUTADOS.discard((cid, uid))
            return

        asyncio.create_task(_unmute_after(client, cid, uid, delay=60))
