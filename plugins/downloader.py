"""
plugins/downloader.py
Baixador universal de vídeos usando yt-dlp (YouTube, Instagram, TikTok, etc.)
"""
import os
import tempfile
import asyncio
from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, tr

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

@Client.on_message(cmd_filter("dl") & filters.me)
async def cmd_dl(client, message):
    """Baixa um vídeo de quase qualquer rede social (Instagram, TikTok, YouTube)."""
    if not HAS_YTDLP:
        return await message.edit_text(tr("❌ Biblioteca `yt-dlp` não instalada.", "❌ `yt-dlp` library not installed."))

    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}dl [link do vídeo]`", f"⚠️ Use: `{p}dl [video link]`"))

    url = partes[1].strip()
    msg = await message.edit_text(tr(
        "📥 **Analisando link e baixando...**\nIsso pode demorar dependendo do tamanho.",
        "📥 **Analyzing link and downloading...**\nThis might take a while depending on size."
    ))

    tmp_dir = tempfile.gettempdir()
    arquivo = None

    def baixar_video():
        opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(tmp_dir, 'vid_%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 1500 * 1024 * 1024,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'requested_downloads' in info:
                path = info['requested_downloads'][0]['filepath']
            else:
                path = ydl.prepare_filename(info)
            return path, info.get('title', 'Video')

    try:
        arquivo, titulo = await asyncio.to_thread(baixar_video)
        await msg.edit_text(tr("☁️ **Enviando para o Telegram...**", "☁️ **Uploading to Telegram...**"))
        await client.send_video(
            message.chat.id, arquivo,
            caption=tr(f"🎥 **{titulo}**\n🔗 Link original", f"🎥 **{titulo}**\n🔗 Original link")
        )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(tr(f"❌ Erro ao baixar:\n`{str(e)[:300]}`", f"❌ Download error:\n`{str(e)[:300]}`"))
    finally:
        if arquivo and os.path.exists(arquivo):
            try:
                os.remove(arquivo)
            except Exception:
                pass
