"""
plugins/alive.py
  ,alive — exibe status completo do userbot (uptime, versões, usuário).

Configuração da mídia exibida (foto/vídeo/gif) é feita só pelo painel
bot agora (/painel → 🖼️ Alive) — escreve na mesma chave via utils.db,
então aplica na hora, sem precisar reiniciar o userbot.
"""
import logging
import os
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
        f"[AxonBot]({_REPO_URL})\n\n"
        f"Usuário   :  {nome}\n"
        f"Uptime    :  {ut}\n"
        f"Build     :  {versao}\n"
        f"Prefixo   :  {p}\n"
        f"Python    :  {py}\n"
        f"Pyrogram  :  {pyro}\n"
        f"SO        :  {so}",

        f"[AxonBot]({_REPO_URL})\n\n"
        f"User      :  {nome}\n"
        f"Uptime    :  {ut}\n"
        f"Build     :  {versao}\n"
        f"Prefix    :  {p}\n"
        f"Python    :  {py}\n"
        f"Pyrogram  :  {pyro}\n"
        f"OS        :  {so}",
    )


async def _enviar_midia(client, chat_id, tipo, source, caption):
    if tipo == "animation":
        return await client.send_animation(chat_id, source, caption=caption)
    if tipo == "video":
        return await client.send_video(chat_id, source, caption=caption)
    if tipo == "document":
        return await client.send_document(chat_id, source, caption=caption)
    return await client.send_photo(chat_id, source, caption=caption)


def _extrair_file_id(sent, tipo):
    midia = getattr(sent, tipo, None) or getattr(sent, "photo", None)
    return getattr(midia, "file_id", None)


@cmd("alive")
async def cmd_alive(client, message):
    """Verifica se o userbot está online e exibe informações de status."""
    inicio = getattr(client, "tempo_inicio", time.time())
    versao = getattr(client, "VERSAO", "?")
    p      = prefixo(client)
    me     = await client.get_me()
    txt    = _build_text(me, inicio, versao, p)

    media_cfg  = carregar(_ALIVE_KEY, {})
    path       = media_cfg.get("path")
    file_id    = media_cfg.get("file_id")  # formato legado (antes do reenvio via arquivo local)
    native_id  = media_cfg.get("native_file_id")
    media_type = media_cfg.get("type")  # "photo", "animation", "video" ou "document"

    if path or file_id:
        await message.delete()
        sent = None

        # 1) file_id da própria sessão do userbot, cacheado de um envio anterior — mais
        #    rápido, sem reenviar o arquivo inteiro de novo.
        if native_id:
            try:
                sent = await _enviar_midia(client, message.chat.id, media_type, native_id, txt)
            except Exception as e:
                logger.debug(f"[alive.py] file_id nativo expirou, reenviando do arquivo local: {e}")

        # 2) reenvia a partir do arquivo baixado localmente pelo painel — não depende de
        #    reusar o file_id emitido pela API de Bot na sessão MTProto do userbot (isso
        #    falha silenciosamente pra alguns tipos), então é o método garantido.
        if sent is None and path and os.path.exists(path):
            try:
                sent = await _enviar_midia(client, message.chat.id, media_type, path, txt)
                novo_id = _extrair_file_id(sent, media_type)
                if novo_id:
                    media_cfg["native_file_id"] = novo_id
                    salvar(_ALIVE_KEY, media_cfg)
            except Exception as e:
                logger.warning(f"[alive.py] falha ao reenviar arquivo local do ,alive: {e}")

        # 3) último recurso, só existe em configs antigas sem arquivo local salvo ainda.
        if sent is None and file_id:
            try:
                sent = await _enviar_midia(client, message.chat.id, media_type, file_id, txt)
            except Exception as e:
                logger.warning(f"[alive.py] falha ao reenviar file_id legado do ,alive: {e}")

        if sent is not None:
            deletar_depois(sent, DEL_LONGO)
            return

        # nenhuma via de mídia funcionou — manda só o texto mesmo
        sent = await client.send_message(message.chat.id, txt, disable_web_page_preview=True)
        deletar_depois(sent, DEL_LONGO)
        return

    await message.edit_text(txt, disable_web_page_preview=True)
    deletar_depois(message, DEL_LONGO)
