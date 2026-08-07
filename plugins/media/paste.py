"""
plugins/paste.py
  ,paste — envia o texto (ou mensagem respondida) para um pastebin e retorna o link.
"""
import aiohttp

from pyrogram import filters, Client
from utils.helpers import tr
from utils.commands import cmd


async def _paste_to_katbin(text: str) -> str:
    """Paste to katb.in and return the URL."""
    async with aiohttp.ClientSession() as s:
        async with s.post(
            "https://katb.in/api/paste",
            json={"paste": {"content": text}},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            data = await r.json(content_type=None)
            slug = data.get("id") or data.get("slug")
            if not slug:
                raise ValueError(f"katb.in: unexpected response {data}")
            return f"https://katb.in/{slug}"


async def _paste_to_dpaste(text: str) -> str:
    """Fallback: paste to dpaste.com."""
    async with aiohttp.ClientSession() as s:
        async with s.post(
            "https://dpaste.com/api/v2/",
            data={"content": text, "expiry_days": 30},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            if r.status in (200, 201):
                url = (await r.text()).strip().strip('"')
                if not url.endswith(".txt"):
                    url += ".txt"
                return url
            raise ValueError(f"dpaste HTTP {r.status}")


@cmd("paste")
async def cmd_paste(client, message):
    """Envia texto ou mensagem respondida para um pastebin. Retorna o link."""
    parts = message.text.split(None, 1)
    text  = parts[1].strip() if len(parts) > 1 else None

    if not text:
        reply = message.reply_to_message
        if reply and reply.text:
            text = reply.text
        elif reply and reply.caption:
            text = reply.caption

    if not text:
        return await message.edit_text(tr(
            "⚠️ Uso: `,paste [texto]` ou responda a uma mensagem.",
            "⚠️ Usage: `,paste [text]` or reply to a message.",
        ))

    await message.edit_text(tr("⏳ Enviando para pastebin...", "⏳ Uploading to pastebin..."))

    try:
        url = await _paste_to_katbin(text)
    except Exception:
        try:
            url = await _paste_to_dpaste(text)
        except Exception as e:
            return await message.edit_text(tr(
                f"❌ Falha ao fazer paste: `{e}`",
                f"❌ Paste failed: `{e}`",
            ))

    await message.edit_text(tr(
        f"📋 **Paste criado:**\n{url}",
        f"📋 **Paste created:**\n{url}",
    ), disable_web_page_preview=True)
