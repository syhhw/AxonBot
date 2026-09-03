"""
plugins/welcome.py
Boas-vindas automáticas para novos membros — configurável por grupo.

Variáveis disponíveis na mensagem:
  {name}    — primeiro nome do usuário
  {mention} — menção clicável
  {chat}    — nome do grupo
  {count}   — número total de membros

Créditos: boas-vindas configuráveis são um padrão comum em userbots
Telegram (Man-Userbot e forks).
"""
import logging

from pyrogram import Client, filters

from utils.commands import cmd
from utils.helpers import carregar, prefixo, salvar, tr

logger = logging.getLogger("AxonBot.welcome")


def _chave(chat_id: int) -> str:
    return f"welcome_{chat_id}"


@cmd("setbemvindo")
async def cmd_setwelcome(client, message):
    """Define a mensagem de boas-vindas para este grupo."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(
            f"⚠️ **Uso:** `{p}setbemvindo [mensagem]`\n\n"
            f"**Variáveis disponíveis:**\n"
            f"• `{{name}}` — primeiro nome\n"
            f"• `{{mention}}` — menção clicável\n"
            f"• `{{chat}}` — nome do grupo\n"
            f"• `{{count}}` — número de membros\n\n"
            f"**Exemplo:**\n"
            f"`{p}setbemvindo 👋 Olá, {{mention}}! Seja bem-vindo ao {{chat}}!`",
            f"⚠️ **Usage:** `{p}setwelcome [message]`\n\n"
            f"**Available variables:**\n"
            f"• `{{name}}` — first name\n"
            f"• `{{mention}}` — clickable mention\n"
            f"• `{{chat}}` — group name\n"
            f"• `{{count}}` — member count\n\n"
            f"**Example:**\n"
            f"`{p}setwelcome 👋 Hey {{mention}}! Welcome to {{chat}}!`"
        ))
    texto = partes[1].strip()
    salvar(_chave(message.chat.id), {"texto": texto, "ativo": True})
    await message.edit_text(tr(
        f"✅ **Boas-vindas configurada!**\n\n"
        f"📋 **Preview** (sem substituição de variáveis):\n{texto}",
        f"✅ **Welcome message set!**\n\n"
        f"📋 **Preview** (without variable substitution):\n{texto}"
    ))


@cmd("delbemvindo")
async def cmd_delwelcome(client, message):
    """Desativa e remove a mensagem de boas-vindas deste grupo."""
    dados = carregar(_chave(message.chat.id), {})
    if not dados or not dados.get("ativo"):
        return await message.edit_text(tr(
            "⚠️ Nenhuma boas-vindas ativa neste grupo.",
            "⚠️ No active welcome message in this group."
        ))
    salvar(_chave(message.chat.id), {"ativo": False})
    await message.edit_text(tr("🗑️ **Boas-vindas removida.**", "🗑️ **Welcome message removed.**"))


@cmd("bemvindo")
async def cmd_showwelcome(client, message):
    """Mostra a mensagem de boas-vindas atual deste grupo."""
    p = prefixo(client)
    dados = carregar(_chave(message.chat.id), {})
    if not dados or not dados.get("ativo"):
        return await message.edit_text(tr(
            f"⚠️ Nenhuma boas-vindas ativa neste grupo.\n"
            f"Use `{p}setbemvindo [mensagem]` para criar.",
            f"⚠️ No active welcome in this group.\n"
            f"Use `{p}setwelcome [message]` to set one."
        ))
    await message.edit_text(tr(
        f"📋 **Boas-vindas atual:**\n\n{dados['texto']}",
        f"📋 **Current welcome:**\n\n{dados['texto']}"
    ))


@Client.on_message(filters.new_chat_members, group=4)
async def welcome_handler(client, message):
    """Envia a mensagem de boas-vindas quando novos membros entram no grupo."""
    dados = carregar(_chave(message.chat.id), {})
    if not dados or not dados.get("ativo"):
        return
    texto_template = dados.get("texto", "")
    if not texto_template:
        return

    try:
        count = await client.get_chat_members_count(message.chat.id)
    except Exception:
        count = "?"

    chat_nome = getattr(message.chat, "title", "")

    for membro in message.new_chat_members:
        if membro.is_bot:
            continue
        nome = membro.first_name or "Usuário"
        mention = f"[{nome}](tg://user?id={membro.id})"
        texto = (texto_template
            .replace("{name}", nome)
            .replace("{mention}", mention)
            .replace("{chat}", chat_nome)
            .replace("{count}", str(count))
        )
        try:
            await client.send_message(message.chat.id, texto)
        except Exception as e:
            logger.debug(f"[welcome.py] ignorado: {e}")
