"""
plugins/purge.py
  ,purge    — apaga todas as mensagens desde a respondida até agora.
  ,del      — apaga a mensagem respondida (e o comando).
  ,purgeme  — apaga suas últimas N mensagens no chat.
  ,sd <n>   — mensagem que se autodestrói após N segundos.

Créditos: ,purge/,del são comandos padrão do ecossistema de userbots
Telegram (Man-Userbot e forks).
"""
import asyncio

from pyrogram import filters, Client
from utils.helpers import cmd_filter, tr


@Client.on_message(cmd_filter("purge") & filters.me)
async def cmd_purge(client, message):
    """Apaga mensagens desde a respondida até agora."""
    reply = message.reply_to_message
    if not reply:
        return await message.edit_text(tr(
            "⚠️ Responda a uma mensagem para iniciar o purge.",
            "⚠️ Reply to a message to start the purge.",
        ))

    await message.delete()

    chat_id   = message.chat.id
    start_id  = reply.id
    end_id    = message.id
    count     = 0
    batch     = []

    async for msg in client.get_chat_history(chat_id):
        if msg.id < start_id:
            break
        if msg.id > end_id:
            continue
        batch.append(msg.id)
        count += 1
        if len(batch) == 100:
            await client.delete_messages(chat_id, batch)
            batch.clear()

    if batch:
        await client.delete_messages(chat_id, batch)

    notice = await client.send_message(chat_id, tr(
        f"🗑️ **Purge concluído** — `{count}` mensagens apagadas.",
        f"🗑️ **Purge complete** — `{count}` messages deleted.",
    ))
    await asyncio.sleep(3)
    await notice.delete()


@Client.on_message(cmd_filter("del") & filters.me)
async def cmd_del(client, message):
    """Apaga a mensagem respondida e o comando."""
    reply = message.reply_to_message
    await message.delete()
    if reply:
        await reply.delete()


@Client.on_message(cmd_filter("purgeme") & filters.me)
async def cmd_purgeme(client, message):
    """Apaga suas últimas N mensagens no chat. Ex: ,purgeme 20"""
    parts = message.text.split(None, 1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        return await message.edit_text(tr(
            "⚠️ Uso: `,purgeme [número]`",
            "⚠️ Usage: `,purgeme [number]`",
        ))

    limit = int(parts[1].strip())
    me    = await client.get_me()
    batch = []
    count = 0

    async for msg in client.get_chat_history(message.chat.id):
        if count >= limit + 1:
            break
        if msg.from_user and msg.from_user.id == me.id:
            batch.append(msg.id)
            count += 1
            if len(batch) == 100:
                await client.delete_messages(message.chat.id, batch)
                batch.clear()

    if batch:
        await client.delete_messages(message.chat.id, batch)


@Client.on_message(cmd_filter("sd") & filters.me)
async def cmd_sd(client, message):
    """Envia mensagem que se autodestrói. Ex: ,sd 10 olá mundo"""
    parts = message.text.split(None, 2)
    if len(parts) < 3 or not parts[1].isdigit():
        return await message.edit_text(tr(
            "⚠️ Uso: `,sd [segundos] [texto]`",
            "⚠️ Usage: `,sd [seconds] [text]`",
        ))

    delay = min(int(parts[1]), 300)
    text  = parts[2]
    await message.delete()
    sent = await client.send_message(message.chat.id, text)
    await asyncio.sleep(delay)
    await sent.delete()
