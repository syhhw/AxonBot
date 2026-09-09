"""
plugins/system/alive.py
  ,alive     — status do userbot (uptime, build, versões, sistema).
  ,setalive  — define a mídia mostrada junto do status.
  ,delalive  — volta a mostrar só o texto.

A mídia é guardada como file_id da própria sessão do userbot, então enviar
de novo não reenvia o arquivo — o Telegram já tem. (Quando existia um bot
de painel isso precisava de três níveis de fallback, porque file_id de bot
e de conta de usuário não são intercambiáveis; com um processo só, não.)
"""
import html
import logging
import platform
import sys
import time

import pyrogram

logger = logging.getLogger("AxonBot.alive")

from utils.commands import cmd
from utils.helpers import DEL_LONGO, carregar, deletar_depois, prefixo, salvar, tr

_ALIVE_KEY = "alive_media.json"
_REPO_URL  = "https://github.com/syhhw/AxonBot"

# Ordem importa: um GIF chega como animation e também tem .document.
_TIPOS = ("animation", "video", "photo", "document")


def _uptime(inicio: float) -> str:
    s = int(time.time() - inicio)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    partes = []
    if d: partes.append(f"{d}d")
    if h: partes.append(f"{h}h")
    if m: partes.append(f"{m}min")
    partes.append(f"{s}s")
    return " ".join(partes)


def _texto(me, inicio, versao, p) -> str:
    nome = html.escape(me.first_name or "?")
    return tr(
        f'⚡ <b><a href="{_REPO_URL}">AxonBot</a></b> — online\n\n'
        f"👤 <b>Usuário</b>  ·  {nome}\n"
        f"⏱️ <b>Uptime</b>   ·  <code>{_uptime(inicio)}</code>\n"
        f"🏷️ <b>Build</b>    ·  <code>{versao}</code>\n"
        f"⌨️ <b>Prefixo</b>  ·  <code>{p}</code>\n"
        f"🐍 <b>Python</b>   ·  <code>{sys.version.split()[0]}</code>\n"
        f"📨 <b>Pyrogram</b> ·  <code>{pyrogram.__version__}</code>\n"
        f"💻 <b>Sistema</b>  ·  <code>{platform.system()} {platform.release()}</code>",

        f'⚡ <b><a href="{_REPO_URL}">AxonBot</a></b> — online\n\n'
        f"👤 <b>User</b>     ·  {nome}\n"
        f"⏱️ <b>Uptime</b>   ·  <code>{_uptime(inicio)}</code>\n"
        f"🏷️ <b>Build</b>    ·  <code>{versao}</code>\n"
        f"⌨️ <b>Prefix</b>   ·  <code>{p}</code>\n"
        f"🐍 <b>Python</b>   ·  <code>{sys.version.split()[0]}</code>\n"
        f"📨 <b>Pyrogram</b> ·  <code>{pyrogram.__version__}</code>\n"
        f"💻 <b>System</b>   ·  <code>{platform.system()} {platform.release()}</code>",
    )


async def _enviar_midia(client, chat_id, tipo, origem, legenda):
    """origem aceita file_id ou caminho local — o Pyrogram resolve os dois."""
    envio = {
        "animation": client.send_animation,
        "video":     client.send_video,
        "document":  client.send_document,
    }.get(tipo, client.send_photo)
    return await envio(chat_id, origem, caption=legenda)


@cmd("alive")
async def cmd_alive(client, message):
    """Verifica se o userbot está online e exibe o status."""
    me   = await client.get_me()
    txt  = _texto(me, getattr(client, "tempo_inicio", time.time()),
                  getattr(client, "VERSAO", "?"), prefixo(client))

    midia  = carregar(_ALIVE_KEY, {})
    # "path" cobre configs antigas, de quando a mídia era baixada em disco.
    origem = midia.get("file_id") or midia.get("path")

    if origem:
        try:
            enviado = await _enviar_midia(client, message.chat.id, midia.get("type"), origem, txt)
            await message.delete()
            deletar_depois(enviado, DEL_LONGO)
            return
        except Exception as e:
            logger.warning(f"[alive.py] falha ao enviar a mídia do ,alive: {e}")

    await message.edit_text(txt, disable_web_page_preview=True)
    deletar_depois(message, DEL_LONGO)


@cmd("setalive")
async def cmd_setalive(client, message):
    """Define a mídia do ,alive (responda a uma foto, vídeo ou GIF)."""
    p    = prefixo(client)
    alvo = message.reply_to_message
    if not alvo:
        return await message.edit_text(tr(
            f"⚠️ Responda a uma foto, vídeo ou GIF com `{p}setalive`.",
            f"⚠️ Reply to a photo, video or GIF with `{p}setalive`.",
        ))

    tipo = next((t for t in _TIPOS if getattr(alvo, t, None)), None)
    if not tipo:
        return await message.edit_text(tr(
            "⚠️ Essa mensagem não tem foto, vídeo nem GIF.",
            "⚠️ That message has no photo, video or GIF.",
        ))

    file_id = getattr(alvo, tipo).file_id
    salvar(_ALIVE_KEY, {"file_id": file_id, "type": tipo})
    await message.edit_text(tr(
        f"🖼️ **Mídia do `{p}alive` definida** (`{tipo}`).",
        f"🖼️ **`{p}alive` media set** (`{tipo}`).",
    ))


@cmd("delalive")
async def cmd_delalive(client, message):
    """Remove a mídia do ,alive e volta a mostrar só o texto."""
    p = prefixo(client)
    if not carregar(_ALIVE_KEY, {}):
        return await message.edit_text(tr(
            f"ℹ️ O `{p}alive` já está sem mídia.", f"ℹ️ `{p}alive` has no media set."
        ))
    salvar(_ALIVE_KEY, {})
    await message.edit_text(tr(
        f"🗑️ **Mídia do `{p}alive` removida.**", f"🗑️ **`{p}alive` media removed.**"
    ))
