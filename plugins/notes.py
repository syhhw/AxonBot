"""
plugins/notes.py
Notas rápidas por grupo — salve trechos de texto ou mensagens respondidas
com um nome e recupere a qualquer hora usando #nome.
"""
import re
from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, carregar, salvar, tr


def _chave(chat_id: int) -> str:
    return f"notes_{chat_id}"


@Client.on_message(cmd_filter("nota") & filters.me)
async def cmd_savenote(client, message):
    """Salva uma nota nomeada para este grupo. Use respondendo a uma mensagem ou com texto direto."""
    p = prefixo(client)
    partes = message.text.split(None, 2)

    if len(partes) < 2:
        return await message.edit_text(tr(
            f"⚠️ **Uso:**\n"
            f"• `{p}nota nome conteúdo` — salva o texto direto\n"
            f"• `{p}nota nome` respondendo a uma mensagem — salva o conteúdo dela\n\n"
            f"Recupere com `#nome` a qualquer hora.",
            f"⚠️ **Usage:**\n"
            f"• `{p}note name content` — saves the text directly\n"
            f"• `{p}note name` replying to a message — saves its content\n\n"
            f"Retrieve with `#name` anytime."
        ))

    nome = partes[1].strip().lower()

    if len(partes) > 2:
        conteudo = partes[2].strip()
    elif message.reply_to_message:
        conteudo = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        ).strip()
    else:
        conteudo = ""

    if not conteudo:
        return await message.edit_text(tr(
            "⚠️ Forneça um conteúdo ou responda a uma mensagem com texto.",
            "⚠️ Provide content or reply to a message with text."
        ))

    notas = carregar(_chave(message.chat.id), {})
    editando = nome in notas
    notas[nome] = conteudo
    salvar(_chave(message.chat.id), notas)

    acao = tr("atualizada", "updated") if editando else tr("salva", "saved")
    await message.edit_text(tr(
        f"📌 **Nota {acao}!**\n"
        f"├ 🏷️ Nome: `#{nome}`\n"
        f"└ 📝 Conteúdo: `{conteudo[:60]}{'...' if len(conteudo) > 60 else ''}`",
        f"📌 **Note {acao}!**\n"
        f"├ 🏷️ Name: `#{nome}`\n"
        f"└ 📝 Content: `{conteudo[:60]}{'...' if len(conteudo) > 60 else ''}`"
    ))


@Client.on_message(cmd_filter("delnota") & filters.me)
async def cmd_delnote(client, message):
    """Remove uma nota do grupo atual."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(
            f"⚠️ **Uso:** `{p}delnota nome`",
            f"⚠️ **Usage:** `{p}delnote name`"
        ))
    nome = partes[1].strip().lower().lstrip("#")
    notas = carregar(_chave(message.chat.id), {})
    if nome not in notas:
        return await message.edit_text(tr(
            f"❌ Nota `#{nome}` não encontrada neste grupo.",
            f"❌ Note `#{nome}` not found in this group."
        ))
    del notas[nome]
    salvar(_chave(message.chat.id), notas)
    await message.edit_text(tr(
        f"🗑️ **Nota removida:** `#{nome}`",
        f"🗑️ **Note removed:** `#{nome}`"
    ))


@Client.on_message(cmd_filter("notas") & filters.me)
async def cmd_listnotes(client, message):
    """Lista todas as notas salvas neste grupo."""
    p = prefixo(client)
    notas = carregar(_chave(message.chat.id), {})
    if not notas:
        return await message.edit_text(tr(
            f"📋 **Nenhuma nota salva neste grupo.**\n"
            f"Use `{p}nota nome conteúdo` para criar.",
            f"📋 **No notes saved in this group.**\n"
            f"Use `{p}note name content` to create one."
        ))
    chat_nome = getattr(message.chat, "title", "este grupo")
    linhas = "".join([f"• `#{k}`\n" for k in sorted(notas)])
    await message.edit_text(tr(
        f"📋 **Notas em {chat_nome}** ({len(notas)}):\n\n{linhas}\n"
        f"💡 Digite `#nome` para ver o conteúdo.",
        f"📋 **Notes in {chat_nome}** ({len(notas)}):\n\n{linhas}\n"
        f"💡 Type `#name` to retrieve content."
    ))


@Client.on_message(~filters.bot, group=7)
async def note_retriever(client, message):
    """Detecta #nome em qualquer mensagem e responde com o conteúdo da nota."""
    if not message.text:
        return
    match = re.match(r'^#(\w+)\s*$', message.text.strip())
    if not match:
        return
    nome = match.group(1).lower()
    notas = carregar(_chave(message.chat.id), {})
    if nome in notas:
        await message.reply_text(notas[nome])
