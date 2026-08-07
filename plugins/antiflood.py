"""
plugins/antiflood.py
Controle de flood por grupo — detecta envio rápido de mensagens e muta
o usuário automaticamente. Unmute automático após 60 segundos.

Créditos: antiflood é um módulo padrão de moderação em userbots Telegram
(Man-Userbot e forks).
"""
import logging
import asyncio
import time
from collections import defaultdict
from pyrogram import filters, Client
from pyrogram.types import ChatPermissions
from utils.helpers import cmd_filter, prefixo, carregar, salvar, tr
logger = logging.getLogger("AxonBot.antiflood")


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
    except Exception as e:
        logger.debug(f"[antiflood.py] ignorado: {e}")


@Client.on_message(cmd_filter("setflood") & filters.me)
async def cmd_setflood(client, message):
    """Define o limite de mensagens/5s e a duração do mute para este grupo."""
    if message.chat.type.name not in ("GROUP", "SUPERGROUP"):
        return await message.edit_text(tr(
            "❌ Antiflood só funciona em grupos.",
            "❌ Antiflood only works in groups."
        ))
    p = prefixo(client)
    partes = message.text.split(None, 2)

    if len(partes) < 2 or not partes[1].strip().isdigit():
        return await message.edit_text(tr(
            f"⚠️ **Uso:** `{p}setflood [msgs] [segundos]`\n\n"
            f"• `[msgs]` — mensagens por 5s antes de mutar (padrão: 7)\n"
            f"• `[segundos]` — duração do mute (padrão: 60, máx: 3600)\n\n"
            f"**Exemplos:**\n"
            f"`{p}setflood 5` → 5 msgs/5s, mute de 60s\n"
            f"`{p}setflood 5 120` → 5 msgs/5s, mute de 120s",
            f"⚠️ **Usage:** `{p}setflood [msgs] [seconds]`\n\n"
            f"• `[msgs]` — messages per 5s before muting (default: 7)\n"
            f"• `[seconds]` — mute duration (default: 60, max: 3600)\n\n"
            f"**Examples:**\n"
            f"`{p}setflood 5` → 5 msgs/5s, 60s mute\n"
            f"`{p}setflood 5 120` → 5 msgs/5s, 120s mute"
        ))

    limite = int(partes[1].strip())
    if limite < 2:
        return await message.edit_text(tr(
            "⚠️ Mínimo de 2 mensagens por limite.",
            "⚠️ Minimum limit is 2 messages."
        ))

    duracao = 60
    if len(partes) > 2 and partes[2].strip().isdigit():
        duracao = max(10, min(int(partes[2].strip()), 3600))

    dados = carregar(_chave(message.chat.id), {})
    dados["limite"]  = limite
    dados["duracao"] = duracao
    dados["ativo"]   = True
    salvar(_chave(message.chat.id), dados)

    dur_str = f"{duracao}s" if duracao < 60 else (f"{duracao // 60}min" if duracao % 60 == 0 else f"{duracao // 60}min {duracao % 60}s")
    await message.edit_text(tr(
        f"✅ **Antiflood ativado!**\n"
        f"├ 🚨 Limite: `{limite}` msgs / 5s\n"
        f"└ ⏱️ Mute: `{dur_str}`",
        f"✅ **Antiflood enabled!**\n"
        f"├ 🚨 Limit: `{limite}` msgs / 5s\n"
        f"└ ⏱️ Mute: `{dur_str}`"
    ))


@Client.on_message(cmd_filter("noflood") & filters.me)
async def cmd_noflood(client, message):
    """Desativa o antiflood neste grupo."""
    if message.chat.type.name not in ("GROUP", "SUPERGROUP"):
        return await message.edit_text(tr(
            "❌ Antiflood só funciona em grupos.",
            "❌ Antiflood only works in groups."
        ))
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
    if message.chat.type.name not in ("GROUP", "SUPERGROUP"):
        return await message.edit_text(tr(
            "❌ Antiflood só funciona em grupos.",
            "❌ Antiflood only works in groups."
        ))
    p = prefixo(client)
    dados = carregar(_chave(message.chat.id), {})
    if not dados or not dados.get("ativo"):
        return await message.edit_text(tr(
            f"🟢 **Antiflood inativo** neste grupo.\n"
            f"Use `{p}setflood [msgs] [segundos]` para ativar.",
            f"🟢 **Antiflood inactive** in this group.\n"
            f"Use `{p}setflood [msgs] [seconds]` to enable."
        ))
    duracao = dados.get("duracao", 60)
    dur_str = f"{duracao}s" if duracao < 60 else (f"{duracao // 60}min" if duracao % 60 == 0 else f"{duracao // 60}min {duracao % 60}s")
    await message.edit_text(tr(
        f"🚨 **Antiflood ativo**\n"
        f"├ 🔢 Limite: `{dados['limite']}` msgs / 5s\n"
        f"└ ⏱️ Mute: `{dur_str}`",
        f"🚨 **Antiflood active**\n"
        f"├ 🔢 Limit: `{dados['limite']}` msgs / 5s\n"
        f"└ ⏱️ Mute: `{dur_str}`"
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

        duracao = dados.get("duracao", 60)
        dur_str = f"{duracao}s" if duracao < 60 else (f"{duracao // 60}min" if duracao % 60 == 0 else f"{duracao // 60}min {duracao % 60}s")
        nome    = message.from_user.first_name or "Usuário"
        mention = f"[{nome}](tg://user?id={uid})"

        try:
            await client.restrict_chat_member(
                cid, uid,
                ChatPermissions(can_send_messages=False)
            )
            await client.send_message(cid, tr(
                f"🚨 **Flood detectado!** {mention} foi mutado por `{dur_str}`.",
                f"🚨 **Flood detected!** {mention} has been muted for `{dur_str}`."
            ))
        except Exception:
            _MUTADOS.discard((cid, uid))
            return

        asyncio.create_task(_unmute_after(client, cid, uid, delay=duracao))
