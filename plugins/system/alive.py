"""
plugins/alive.py
  ,alive          — exibe status completo do userbot (uptime, versões, usuário).
  ,setalivephoto  — define foto, vídeo ou gif exibido no ,alive (responda à mídia).
  ,delalivephoto  — remove a mídia do ,alive.
"""
import logging
import time
import sys
import platform
import pyrogram
logger = logging.getLogger("AxonBot.alive")

from pyrogram import filters, Client
from utils.helpers import prefixo, deletar_depois, tr, carregar, salvar, DEL_LONGO
from utils.commands import cmd

_ALIVE_KEY = "alive_media.json"
_REPO_URL  = "https://github.com/syhhw/AxonBot"


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
    py   = sys.version.split()[0]
    pyro = pyrogram.__version__
    so   = f"{platform.system()} {platform.release()}"
    ut   = _uptime(inicio)
    nome = me.first_name or "?"
    return tr(
        f"**[AxonBot]({_REPO_URL})** — userbot pessoal via Pyrogram.\n\n"
        f"› Usuário    :   `{nome}`\n"
        f"› Uptime     :   `{ut}`\n"
        f"› Build      :   `{versao}`\n"
        f"› Prefixo    :   `{p}`\n"
        f"› Python     :   `{py}`\n"
        f"› Pyrogram   :   `{pyro}`\n"
        f"› SO         :   `{so}`",

        f"**[AxonBot]({_REPO_URL})** — personal userbot powered by Pyrogram.\n\n"
        f"› User       :   `{nome}`\n"
        f"› Uptime     :   `{ut}`\n"
        f"› Build      :   `{versao}`\n"
        f"› Prefix     :   `{p}`\n"
        f"› Python     :   `{py}`\n"
        f"› Pyrogram   :   `{pyro}`\n"
        f"› OS         :   `{so}`",
    )


@cmd("alive")
async def cmd_alive(client, message):
    """Verifica se o userbot está online e exibe informações de status."""
    inicio = getattr(client, "tempo_inicio", time.time())
    versao = getattr(client, "VERSAO", "?")
    p      = prefixo(client)
    me     = await client.get_me()
    txt    = _build_text(me, inicio, versao, p)

    media_cfg = carregar(_ALIVE_KEY, {})
    file_id   = media_cfg.get("file_id")
    media_type = media_cfg.get("type")  # "photo", "animation" ou "video"

    if file_id:
        await message.delete()
        try:
            if media_type == "animation":
                sent = await client.send_animation(
                    message.chat.id, file_id, caption=txt
                )
            elif media_type == "video":
                sent = await client.send_video(
                    message.chat.id, file_id, caption=txt
                )
            else:
                sent = await client.send_photo(
                    message.chat.id, file_id, caption=txt
                )
            deletar_depois(sent, DEL_LONGO)
        except Exception as e:
            logger.debug(f"[alive.py] ignorado: {e}")
            # message já foi apagada acima — não dá pra "editar" ela, manda nova
            sent = await client.send_message(message.chat.id, txt, disable_web_page_preview=True)
            deletar_depois(sent, DEL_LONGO)
        return

    await message.edit_text(txt, disable_web_page_preview=True)
    deletar_depois(message, DEL_LONGO)


@cmd("setalivephoto")
async def cmd_setalivephoto(client, message):
    """Define a foto, vídeo ou gif exibido no ,alive. Responda à mídia."""
    reply = message.reply_to_message
    alvo  = reply if reply else message

    if alvo.photo:
        file_id, media_type = alvo.photo.file_id, "photo"
    elif alvo.animation:
        file_id, media_type = alvo.animation.file_id, "animation"
    elif alvo.video:
        file_id, media_type = alvo.video.file_id, "video"
    else:
        return await message.edit_text(tr(
            "⚠️ Responda a uma **foto**, **vídeo** ou **gif** com este comando.",
            "⚠️ Reply to a **photo**, **video** or **gif** with this command.",
        ))

    salvar(_ALIVE_KEY, {"file_id": file_id, "type": media_type})
    icon = {"animation": "🎞️", "video": "🎬"}.get(media_type, "🖼️")
    await message.edit_text(tr(
        f"{icon} **Mídia do ,alive definida!**",
        f"{icon} **,alive media set!**",
    ))


@cmd("delalivephoto")
async def cmd_delalivephoto(client, message):
    """Remove a mídia do ,alive."""
    salvar(_ALIVE_KEY, {})
    await message.edit_text(tr(
        "🗑️ **Mídia do ,alive removida.**",
        "🗑️ **,alive media removed.**",
    ))
