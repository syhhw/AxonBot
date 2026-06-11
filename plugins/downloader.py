"""
plugins/downloader.py
Baixador universal de vídeos usando yt-dlp (YouTube, Instagram, TikTok, etc.)
Comandos:
  ,dlinfo [link] — mostra título, duração, canal e tamanho estimado
  ,dl [link]     — baixa e envia o vídeo
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


def _formatar_duracao(segundos: int) -> str:
    if not segundos:
        return "?"
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _formatar_tamanho(bytes_: int) -> str:
    if not bytes_:
        return "?"
    for unidade in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unidade}"
        bytes_ /= 1024
    return f"{bytes_:.1f} GB"


def _obter_tamanho_estimado(info: dict) -> int:
    """Tenta estimar o tamanho do melhor formato mp4 disponível."""
    for fmt in reversed(info.get("formats", [])):
        if fmt.get("ext") == "mp4" and fmt.get("filesize"):
            return fmt["filesize"]
    return info.get("filesize_approx", 0) or 0

@Client.on_message(cmd_filter("dlinfo") & filters.me)
async def cmd_dlinfo(client, message):
    """Mostra informações do vídeo (título, duração, canal, tamanho) sem baixar."""
    if not HAS_YTDLP:
        return await message.edit_text(tr("❌ `yt-dlp` não instalado.", "❌ `yt-dlp` not installed."))

    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(
            f"⚠️ Use: `{p}dlinfo [link]`",
            f"⚠️ Use: `{p}dlinfo [link]`"
        ))

    url = partes[1].strip()
    await message.edit_text(tr("🔍 **Analisando link...**", "🔍 **Analyzing link...**"))

    def extrair_info():
        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await asyncio.to_thread(extrair_info)
    except Exception as e:
        return await message.edit_text(tr(
            f"❌ Não foi possível analisar o link:\n`{str(e)[:300]}`",
            f"❌ Could not analyze the link:\n`{str(e)[:300]}`"
        ))

    titulo    = info.get("title", "?")
    duracao   = _formatar_duracao(info.get("duration", 0))
    canal     = info.get("uploader") or info.get("channel") or "?"
    views     = info.get("view_count")
    tamanho   = _formatar_tamanho(_obter_tamanho_estimado(info))
    thumb     = info.get("thumbnail")
    plataform = info.get("extractor_key", "?")

    views_str = f"{views:,}" if views else "?"

    caption = tr(
        f"📹 **{titulo}**\n\n"
        f"├ 📺 Canal: `{canal}`\n"
        f"├ ⏱️ Duração: `{duracao}`\n"
        f"├ 👁️ Views: `{views_str}`\n"
        f"├ 💾 Tamanho aprox.: `{tamanho}`\n"
        f"└ 🌐 Plataforma: `{plataform}`\n\n"
        f"💡 Use `{p}dl {url}` para baixar.",
        f"📹 **{titulo}**\n\n"
        f"├ 📺 Channel: `{canal}`\n"
        f"├ ⏱️ Duration: `{duracao}`\n"
        f"├ 👁️ Views: `{views_str}`\n"
        f"├ 💾 Approx. size: `{tamanho}`\n"
        f"└ 🌐 Platform: `{plataform}`\n\n"
        f"💡 Use `{p}dl {url}` to download."
    )

    try:
        if thumb:
            await message.delete()
            await client.send_photo(message.chat.id, thumb, caption=caption)
        else:
            await message.edit_text(caption)
    except Exception:
        await message.edit_text(caption)


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

    def baixar():
        base_opts = {
            'outtmpl': os.path.join(tmp_dir, 'dl_%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 1500 * 1024 * 1024,
        }
        # Tenta primeiro com seletor de vídeo mp4; se falhar por "sem vídeo"
        # (posts de imagem no Instagram, etc.), retenta sem restrição de formato.
        tentativas = [
            {**base_opts, 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
            base_opts,
        ]
        _SEM_VIDEO = ('no video', 'no formats', 'requested format not available',
                      'there is no video')

        info = None
        for opts in tentativas:
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                break
            except Exception as e:
                if any(k in str(e).lower() for k in _SEM_VIDEO):
                    continue
                raise

        if info is None:
            raise ValueError("Nenhum formato disponível para este link.")

        rds  = info.get('requested_downloads') or []
        path = rds[0]['filepath'] if rds else None

        if not path or not os.path.exists(path):
            base = os.path.join(tmp_dir, f"dl_{info.get('id', '')}")
            for _ext in ('.mp4', '.webm', '.mkv', '.jpg', '.jpeg', '.png', '.webp', '.mp3', '.m4a'):
                candidate = base + _ext
                if os.path.exists(candidate):
                    path = candidate
                    break

        return path, info.get('title', 'Video')

    try:
        arquivo, titulo = await asyncio.to_thread(baixar)
        if not os.path.exists(arquivo):
            raise FileNotFoundError("Arquivo não encontrado após download.")

        await msg.edit_text(tr("☁️ **Enviando para o Telegram...**", "☁️ **Uploading to Telegram...**"))

        ext     = os.path.splitext(arquivo)[1].lower()
        caption = tr(f"📥 **{titulo}**", f"📥 **{titulo}**")

        if ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            await client.send_photo(message.chat.id, arquivo, caption=caption)
        elif ext in ('.mp3', '.m4a', '.ogg', '.opus', '.flac', '.wav'):
            await client.send_audio(message.chat.id, arquivo, caption=caption)
        else:
            await client.send_video(message.chat.id, arquivo, caption=caption)

        await msg.delete()
    except Exception as e:
        await msg.edit_text(tr(f"❌ Erro ao baixar:\n`{str(e)[:300]}`", f"❌ Download error:\n`{str(e)[:300]}`"))
    finally:
        if arquivo and os.path.exists(arquivo):
            try:
                os.remove(arquivo)
            except Exception:
                pass
