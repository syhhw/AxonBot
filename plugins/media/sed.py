"""
plugins/sed.py
Substituição de texto estilo sed em mensagens respondidas.
Sintaxe: {prefix}s/antigo/novo/[flags]

Flags suportadas:
  g — substituir todas as ocorrências (padrão: apenas a primeira)
  i — case-insensitive
"""
import re
from pyrogram import filters, Client
from utils.helpers import prefixo, tr


def _sed_filter(flt, client, message):
    """Retorna True se a mensagem for um comando sed válido com reply."""
    if not message.text or not message.reply_to_message:
        return False
    p = prefixo(client)
    return bool(re.match(rf'^{re.escape(p)}s/', message.text))


_sed_f = filters.create(_sed_filter)


@Client.on_message(_sed_f & filters.me)
async def cmd_sed(client, message):
    """Aplica substituição de texto na mensagem respondida."""
    texto_reply = (
        message.reply_to_message.text
        or message.reply_to_message.caption
        or ""
    )
    if not texto_reply:
        return await message.edit_text(tr(
            "⚠️ A mensagem respondida não tem texto.",
            "⚠️ The replied message has no text."
        ))

    raw = message.text
    # Extrai partes do padrão: {p}s/old/new/ ou {p}s/old/new/gi
    partes = raw.split("/")
    if len(partes) < 3:
        p = prefixo(client)
        return await message.edit_text(tr(
            f"⚠️ **Uso:** `{p}s/antigo/novo/[flags]`\n"
            f"Flags: `g` (todas), `i` (sem case)",
            f"⚠️ **Usage:** `{p}s/old/new/[flags]`\n"
            f"Flags: `g` (all), `i` (case-insensitive)"
        ))

    # partes[0] = "{p}s", partes[1] = old, partes[2] = new, partes[3] = flags (opcional)
    old = partes[1]
    new = partes[2]
    flags_str = partes[3].strip() if len(partes) > 3 else ""

    if not old:
        return await message.edit_text(tr(
            "⚠️ O padrão de busca não pode ser vazio.",
            "⚠️ Search pattern cannot be empty."
        ))

    re_flags = re.IGNORECASE if "i" in flags_str else 0
    count = 0 if "g" in flags_str else 1

    try:
        resultado = re.sub(re.escape(old), new, texto_reply, count=count, flags=re_flags)
    except re.error as e:
        return await message.edit_text(tr(
            f"❌ Erro de regex: `{e}`",
            f"❌ Regex error: `{e}`"
        ))

    if resultado == texto_reply:
        return await message.edit_text(tr(
            f"⚠️ Nenhuma ocorrência de `{old}` encontrada na mensagem.",
            f"⚠️ No occurrence of `{old}` found in the message."
        ))

    await message.edit_text(tr(
        f"✏️ **Correção:**\n{resultado}",
        f"✏️ **Correction:**\n{resultado}"
    ))
