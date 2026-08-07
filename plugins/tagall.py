"""
plugins/tagall.py
Menciona todos os membros do grupo em lotes de 5. Requer que o userbot
consiga listar membros (funciona melhor como admin).

Créditos: ,tagall é um padrão comum em userbots Telegram (Man-Userbot e forks).
"""
import asyncio
from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, tr


@Client.on_message(cmd_filter("mencionar") & filters.me)
async def cmd_tagall(client, message):
    """Menciona todos os membros do grupo, em lotes de 5."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    motivo = partes[1].strip() if len(partes) > 1 else tr("Atenção!", "Attention!")

    await message.edit_text(tr("⏳ Coletando membros...", "⏳ Collecting members..."))

    membros = []
    try:
        async for membro in client.get_chat_members(message.chat.id):
            if membro.user.is_bot or membro.user.is_deleted:
                continue
            membros.append(membro.user)
    except Exception as e:
        return await message.edit_text(tr(
            f"❌ Não foi possível listar membros.\n"
            f"Certifique-se de que o userbot é admin do grupo.\n\n"
            f"Erro: `{e}`",
            f"❌ Could not list members.\n"
            f"Make sure the userbot is admin in this group.\n\n"
            f"Error: `{e}`"
        ))

    if not membros:
        return await message.edit_text(tr(
            "⚠️ Nenhum membro encontrado.",
            "⚠️ No members found."
        ))

    chat_nome = getattr(message.chat, "title", "")
    cabecalho_msg = tr(
        f"📢 **{motivo}** — {chat_nome} ({len(membros)} membros)\n\n",
        f"📢 **{motivo}** — {chat_nome} ({len(membros)} members)\n\n"
    )

    await message.delete()

    lote_size = 5
    for i in range(0, len(membros), lote_size):
        lote = membros[i:i + lote_size]
        mencoes = " ".join(
            f"[{u.first_name}](tg://user?id={u.id})" for u in lote
        )
        texto = cabecalho_msg + mencoes if i == 0 else mencoes
        await client.send_message(message.chat.id, texto)
        await asyncio.sleep(1.5)
