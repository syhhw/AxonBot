"""
plugins/alive.py
  ,alive          — exibe status completo do userbot (uptime, versões, dono).
  ,setalivephoto  — define foto/gif exibida no ,alive (responda à mídia).
  ,delalivephoto  — remove a foto/gif do ,alive.
"""
import time
import sys
import platform
import pyrogram

from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, deletar_depois, tr, carregar, salvar

_ALIVE_KEY = "alive_media.json"


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


def _build_text(me, inicio, versao, p) -> str:
    py  = sys.version.split()[0]
    pyro = pyrogram.__version__
    so  = f"{platform.system()} {platform.release()}"
    ut  = _uptime(inicio)
    return tr(
        f"╔══「 ⚡ **AXONBOT** 」\n"
        f"║\n"
        f"║  👤 **{me.first_name}** está online!\n"
        f"║\n"
        f"╠══「 📊 **Sistema** 」\n"
        f"║  ├ ⏱ Uptime » `{ut}`\n"
        f"║  ├ 📦 Versão » `v{versao}`\n"
        f"║  ├ 🔧 Prefixo » `{p}`\n"
        f"║  ├ 🐍 Python » `{py}`\n"
        f"║  ├ ⚙️ Pyrogram » `{pyro}`\n"
        f"║  └ 💻 SO » `{so}`\n"
        f"║\n"
        f"╚══「 🤖 **AxonBot ativo e funcional** 」",

        f"╔══「 ⚡ **AXONBOT** 」\n"
        f"║\n"
        f"║  👤 **{me.first_name}** is online!\n"
        f"║\n"
        f"╠══「 📊 **System** 」\n"
        f"║  ├ ⏱ Uptime » `{ut}`\n"
        f"║  ├ 📦 Version » `v{versao}`\n"
        f"║  ├ 🔧 Prefix » `{p}`\n"
        f"║  ├ 🐍 Python » `{py}`\n"
        f"║  ├ ⚙️ Pyrogram » `{pyro}`\n"
        f"║  └ 💻 OS » `{so}`\n"
        f"║\n"
        f"╚══「 🤖 **AxonBot active and running** 」",
    )


@Client.on_message(cmd_filter("alive") & filters.me)
async def cmd_alive(client, message):
    """Verifica se o userbot está online e exibe informações de status."""
    inicio = getattr(client, "tempo_inicio", time.time())
    versao = getattr(client, "VERSAO", "?")
    p      = prefixo(client)
    me     = await client.get_me()
    txt    = _build_text(me, inicio, versao, p)

    media_cfg = carregar(_ALIVE_KEY, {})
    file_id   = media_cfg.get("file_id")
    media_type = media_cfg.get("type")  # "photo" or "animation"

    if file_id:
        await message.delete()
        try:
            if media_type == "animation":
                sent = await client.send_animation(
                    message.chat.id, file_id, caption=txt
                )
            else:
                sent = await client.send_photo(
                    message.chat.id, file_id, caption=txt
                )
            deletar_depois(sent, 45)
            return
        except Exception:
            pass  # fall through to text if media fails

    await message.edit_text(txt, disable_web_page_preview=True)
    deletar_depois(message, 45)


@Client.on_message(cmd_filter("setalivephoto") & filters.me)
async def cmd_setalivephoto(client, message):
    """Define a foto ou gif exibida no ,alive. Responda a uma foto/gif."""
    reply = message.reply_to_message

    if reply and reply.photo:
        file_id    = reply.photo.file_id
        media_type = "photo"
    elif reply and reply.animation:
        file_id    = reply.animation.file_id
        media_type = "animation"
    elif message.photo:
        file_id    = message.photo.file_id
        media_type = "photo"
    elif message.animation:
        file_id    = message.animation.file_id
        media_type = "animation"
    else:
        return await message.edit_text(tr(
            "⚠️ Responda a uma **foto** ou **gif** com este comando.",
            "⚠️ Reply to a **photo** or **gif** with this command.",
        ))

    salvar(_ALIVE_KEY, {"file_id": file_id, "type": media_type})
    icon = "🎞️" if media_type == "animation" else "🖼️"
    await message.edit_text(tr(
        f"{icon} **Foto do ,alive definida!**",
        f"{icon} **,alive photo set!**",
    ))


@Client.on_message(cmd_filter("delalivephoto") & filters.me)
async def cmd_delalivephoto(client, message):
    """Remove a foto/gif do ,alive."""
    salvar(_ALIVE_KEY, {})
    await message.edit_text(tr(
        "🗑️ **Foto do ,alive removida.**",
        "🗑️ **,alive photo removed.**",
    ))
