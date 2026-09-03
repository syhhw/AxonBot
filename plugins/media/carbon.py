"""
plugins/carbon.py
  ,carbon [código] — gera uma imagem estilizada do código via carbon.now.sh.
  Responda a uma mensagem de texto ou passe o código direto.
"""
import os
import tempfile

import aiohttp

from utils.commands import cmd
from utils.helpers import tr

_CARBON_URL = "https://carbonara.solopov.dev/api/cook"
_CARBON_THEMES = ["monokai", "dracula", "one-dark", "nord", "night-owl"]


async def _render_carbon(code: str, theme: str = "dracula") -> bytes:
    payload = {
        "code": code,
        "theme": theme,
        "fontFamily": "JetBrains Mono",
        "fontSize": "14px",
        "lineNumbers": True,
        "dropShadow": True,
        "paddingVertical": "48px",
        "paddingHorizontal": "32px",
        "backgroundColor": "#1a1a2e",
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(
            _CARBON_URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            if r.status != 200:
                raise ValueError(f"carbonara HTTP {r.status}")
            return await r.read()


@cmd("carbon")
async def cmd_carbon(client, message):
    """Gera imagem do código via carbon. ,carbon [código] ou responda a texto."""
    parts = message.text.split(None, 1)
    code = parts[1].strip() if len(parts) > 1 else None

    if not code:
        reply = message.reply_to_message
        if reply and (reply.text or reply.caption):
            code = reply.text or reply.caption

    if not code:
        return await message.edit_text(tr(
            "⚠️ Uso: `,carbon [código]` ou responda a uma mensagem de texto.",
            "⚠️ Usage: `,carbon [code]` or reply to a text message.",
        ))

    await message.edit_text(tr("🎨 **Gerando imagem...**", "🎨 **Generating image...**"))

    try:
        img_bytes = await _render_carbon(code)
    except Exception as e:
        return await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))

    tmp = tempfile.mktemp(suffix=".png")
    try:
        with open(tmp, "wb") as f:
            f.write(img_bytes)
        await message.delete()
        await client.send_photo(message.chat.id, tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
