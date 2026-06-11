"""
plugins/alive.py
  ,alive — exibe status completo do userbot (uptime, versões, dono).
"""
import time
import sys
import platform
import pyrogram

from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, deletar_depois, tr


def _uptime(inicio: float) -> str:
    s = int(time.time() - inicio)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}min")
    parts.append(f"{s}s")
    return " ".join(parts)


@Client.on_message(cmd_filter("alive") & filters.me)
async def cmd_alive(client, message):
    """Verifica se o userbot está online e exibe informações de status."""
    inicio = getattr(client, "tempo_inicio", time.time())
    versao = getattr(client, "VERSAO", "?")
    p      = prefixo(client)
    me     = await client.get_me()

    txt = tr(
        f"⚡ **USERBOT ONLINE**\n\n"
        f"├ 👤 **Dono:** [{me.first_name}](tg://user?id={me.id})\n"
        f"├ ⏱️ **Uptime:** `{_uptime(inicio)}`\n"
        f"├ 📦 **Versão:** `v{versao}`\n"
        f"├ 🔧 **Prefixo:** `{p}`\n"
        f"├ 🐍 **Python:** `{sys.version.split()[0]}`\n"
        f"├ ⚙️ **Pyrogram:** `{pyrogram.__version__}`\n"
        f"└ 💻 **SO:** `{platform.system()} {platform.release()}`",

        f"⚡ **USERBOT ONLINE**\n\n"
        f"├ 👤 **Owner:** [{me.first_name}](tg://user?id={me.id})\n"
        f"├ ⏱️ **Uptime:** `{_uptime(inicio)}`\n"
        f"├ 📦 **Version:** `v{versao}`\n"
        f"├ 🔧 **Prefix:** `{p}`\n"
        f"├ 🐍 **Python:** `{sys.version.split()[0]}`\n"
        f"├ ⚙️ **Pyrogram:** `{pyrogram.__version__}`\n"
        f"└ 💻 **OS:** `{platform.system()} {platform.release()}`",
    )
    await message.edit_text(txt, disable_web_page_preview=True)
    deletar_depois(message, 45)
