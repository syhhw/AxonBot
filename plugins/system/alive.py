"""
plugins/alive.py
  ,alive — exibe status completo do userbot (uptime, versões, usuário).

Configuração da mídia exibida (foto/vídeo/gif) é feita só pelo painel
bot agora (/painel → 🖼️ Alive) — escreve na mesma chave via utils.db,
então aplica na hora, sem precisar reiniciar o userbot.
"""
import logging
import time
import sys
import platform
import pyrogram
logger = logging.getLogger("AxonBot.alive")

from pyrogram import filters, Client
from utils.helpers import prefixo, deletar_depois, tr, carregar, DEL_LONGO
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
