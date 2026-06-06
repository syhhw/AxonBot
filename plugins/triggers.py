"""
plugins/triggers.py
Sistema de Auto-Respostas Passivas (Gatilhos)
"""
import re
from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, carregar, salvar, tr


def _trigger_matches(gatilho: str, texto: str) -> bool:
    """Verifica se o gatilho está presente no texto com word boundary para termos simples."""
    if " " in gatilho:
        return gatilho in texto.lower()
    return bool(re.search(r'(?<!\w)' + re.escape(gatilho) + r'(?!\w)', texto, re.IGNORECASE))


@Client.on_message(cmd_filter("addtrigger") & filters.me)
async def cmd_addtrigger(client, message):
    """Adiciona um gatilho de resposta automática."""
    p = prefixo(client)
    matches = re.findall(r'"([^"]*)"', message.text)
    if len(matches) < 2:
        return await message.edit_text(tr(
            f'⚠️ Use: `{p}addtrigger "palavra" "resposta"`',
            f'⚠️ Use: `{p}addtrigger "word" "response"`'
        ))

    gatilho = matches[0].lower()
    resposta = matches[1]

    triggers = carregar("triggers.json", {})
    triggers[gatilho] = resposta
    salvar("triggers.json", triggers)

    await message.edit_text(tr(
        f"✅ **Trigger salvo!**\nSe disserem: `{gatilho}`\nResponderei: `{resposta}`",
        f"✅ **Trigger saved!**\nIf they say: `{gatilho}`\nI'll reply: `{resposta}`"
    ))


@Client.on_message(cmd_filter("deltrigger") & filters.me)
async def cmd_deltrigger(client, message):
    """Remove um gatilho de resposta."""
    p = prefixo(client)
    matches = re.findall(r'"([^"]*)"', message.text)
    if not matches:
        return await message.edit_text(tr(
            f'⚠️ Use: `{p}deltrigger "palavra"`',
            f'⚠️ Use: `{p}deltrigger "word"`'
        ))
    gatilho = matches[0].lower()

    triggers = carregar("triggers.json", {})
    if gatilho in triggers:
        del triggers[gatilho]
        salvar("triggers.json", triggers)
        await message.edit_text(tr(f"🗑️ **Trigger removido:** `{gatilho}`", f"🗑️ **Trigger removed:** `{gatilho}`"))
    else:
        await message.edit_text(tr(f"❌ **Trigger não encontrado:** `{gatilho}`", f"❌ **Trigger not found:** `{gatilho}`"))


@Client.on_message(cmd_filter("triggers") & filters.me)
async def cmd_triggers(client, message):
    """Lista todos os gatilhos ativos."""
    triggers = carregar("triggers.json", {})
    if not triggers:
        return await message.edit_text(tr("⚠️ **Nenhum trigger configurado.**", "⚠️ **No triggers configured.**"))

    linhas = "".join([f"• `{k}` → `{v}`\n" for k, v in triggers.items()])
    await message.edit_text(tr("⚡ **Meus Triggers:**\n\n", "⚡ **My Triggers:**\n\n") + linhas)


@Client.on_message(filters.incoming & ~filters.bot & ~filters.me, group=5)
async def trigger_handler(client, message):
    """Ouve mensagens e responde caso acerte o gatilho."""
    if not message.text:
        return
    texto = message.text
    for gatilho, resposta in carregar("triggers.json", {}).items():
        if _trigger_matches(gatilho, texto):
            await message.reply_text(resposta)
            return
