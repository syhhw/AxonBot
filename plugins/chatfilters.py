"""
plugins/chatfilters.py
Filtros automáticos por grupo — diferente dos triggers globais, cada filtro
existe apenas no chat onde foi criado. Ideal para grupos com regras próprias.

Créditos: filtros por grupo seguem o padrão popularizado por
Ultroid/TeamUltroid no ecossistema de userbots Telegram.
"""
import re
from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, carregar, salvar, tr


def _chave(chat_id: int) -> str:
    return f"chatfilter_{chat_id}"


def _match(palavra: str, texto: str) -> bool:
    if " " in palavra:
        return palavra in texto.lower()
    return bool(re.search(r'(?<!\w)' + re.escape(palavra) + r'(?!\w)', texto, re.IGNORECASE))


@Client.on_message(cmd_filter("addfiltro") & filters.me)
async def cmd_addfilter(client, message):
    """Adiciona um filtro de resposta automática para este grupo."""
    p = prefixo(client)
    matches = re.findall(r'"([^"]*)"', message.text)
    if len(matches) < 2:
        return await message.edit_text(tr(
            f'⚠️ **Uso:** `{p}addfiltro "palavra" "resposta"`\n\n'
            f'Filtros são exclusivos deste grupo — não afetam outros chats.',
            f'⚠️ **Usage:** `{p}addfilter "word" "response"`\n\n'
            f'Filters are group-specific — they don\'t affect other chats.'
        ))
    palavra, resposta = matches[0].lower(), matches[1]
    dados = carregar(_chave(message.chat.id), {})
    dados[palavra] = resposta
    salvar(_chave(message.chat.id), dados)
    await message.edit_text(tr(
        f"✅ **Filtro salvo neste grupo!**\n"
        f"├ 🔍 Palavra: `{palavra}`\n"
        f"└ 💬 Resposta: `{resposta}`",
        f"✅ **Filter saved in this group!**\n"
        f"├ 🔍 Word: `{palavra}`\n"
        f"└ 💬 Response: `{resposta}`"
    ))


@Client.on_message(cmd_filter("delfiltro") & filters.me)
async def cmd_delfilter(client, message):
    """Remove um filtro do grupo atual."""
    p = prefixo(client)
    matches = re.findall(r'"([^"]*)"', message.text)
    if not matches:
        return await message.edit_text(tr(
            f'⚠️ **Uso:** `{p}delfiltro "palavra"`',
            f'⚠️ **Usage:** `{p}delfilter "word"`'
        ))
    palavra = matches[0].lower()
    dados = carregar(_chave(message.chat.id), {})
    if palavra not in dados:
        return await message.edit_text(tr(
            f"❌ Filtro `{palavra}` não encontrado neste grupo.",
            f"❌ Filter `{palavra}` not found in this group."
        ))
    del dados[palavra]
    salvar(_chave(message.chat.id), dados)
    await message.edit_text(tr(
        f"🗑️ **Filtro removido:** `{palavra}`",
        f"🗑️ **Filter removed:** `{palavra}`"
    ))


@Client.on_message(cmd_filter("filtros") & filters.me)
async def cmd_listfilters(client, message):
    """Lista todos os filtros ativos neste grupo."""
    p = prefixo(client)
    dados = carregar(_chave(message.chat.id), {})
    if not dados:
        return await message.edit_text(tr(
            f"📋 **Nenhum filtro configurado neste grupo.**\n"
            f"Use `{p}addfiltro \"palavra\" \"resposta\"` para criar um.",
            f"📋 **No filters set in this group.**\n"
            f"Use `{p}addfilter \"word\" \"response\"` to create one."
        ))
    chat_nome = getattr(message.chat, "title", "este grupo")
    linhas = "".join([f"• `{k}` → `{v[:40]}{'...' if len(v) > 40 else ''}`\n" for k, v in dados.items()])
    await message.edit_text(tr(
        f"🔍 **Filtros em {chat_nome}** ({len(dados)}):\n\n{linhas}",
        f"🔍 **Filters in {chat_nome}** ({len(dados)}):\n\n{linhas}"
    ))


@Client.on_message(filters.incoming & ~filters.me & ~filters.bot, group=6)
async def filter_handler(client, message):
    """Dispara resposta automática ao detectar palavra-chave filtrada."""
    if not message.text:
        return
    dados = carregar(_chave(message.chat.id), {})
    if not dados:
        return
    for palavra, resposta in dados.items():
        if _match(palavra, message.text):
            await message.reply_text(resposta)
            return
