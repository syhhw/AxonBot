"""
plugins/downloader.py
Baixador universal usando yt-dlp + instaloader (fallback para Instagram).
  ,dlinfo [link] — mostra título, duração, canal e tamanho estimado
  ,dl [link]     — baixa e envia o arquivo (vídeo, imagem ou áudio)
"""
import os
import re
import glob
import tempfile
import asyncio
from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, tr

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

try:
    import instaloader
    HAS_INSTALOADER = True
except ImportError:
    HAS_INSTALOADER = False

_IG_RE = re.compile(r'instagram\.com/(?:p|reel|tv|reels)/([A-Za-z0-9_-]+)', re.I)


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
    for fmt in reversed(info.get("formats", [])):
        if fmt.get("ext") == "mp4" and fmt.get("filesize"):
            return fmt["filesize"]
    return info.get("filesize_approx", 0) or 0


def _baixar_instaloader(url: str, tmp_dir: str):
    """Fallback para Instagram usando instaloader (fotos, reels, carrosséis)."""
    m = _IG_RE.search(url)
    if not m:
        raise ValueError("Shortcode do Instagram não encontrado na URL.")
    shortcode = m.group(1)
    post_dir  = os.path.join(tmp_dir, f"ig_{shortcode}")
    os.makedirs(post_dir, exist_ok=True)

    L = instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="",
        dirname_pattern=post_dir,
        filename_pattern="{shortcode}",
    )
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    L.download_post(post, target=post_dir)

    titulo = (post.caption or shortcode)[:100].strip().splitlines()[0] if post.caption else shortcode

    # Busca recursiva — instaloader pode criar subpastas
    _MEDIA = ('.mp4', '.jpg', '.jpeg', '.png', '.webp')
    for root, _, files in os.walk(post_dir):
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in _MEDIA:
                return os.path.join(root, f), titulo

    # Debug: mostra o que foi criado para facilitar diagnóstico
    todos = []
    for root, _, files in os.walk(post_dir):
        todos.extend(files)
    raise FileNotFoundError(
        f"Sem mídia após instaloader. Arquivos criados: {todos[:8] or 'nenhum'}"
    )


def _baixar_ytdlp(url: str, tmp_dir: str):
    """Download via yt-dlp com múltiplos formatos de fallback."""
    base_opts = {
        # best[ext=mp4] seleciona arquivo único (não precisa de FFmpeg para merge)
        'format':        'best[ext=mp4]/best[ext=webm]/best',
        'outtmpl':       os.path.join(tmp_dir, 'dl_%(id)s.%(ext)s'),
        'quiet':         True,
        'no_warnings':   True,
        'max_filesize':  1500 * 1024 * 1024,
        'http_headers':  {
            'User-Agent': (
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) '
                'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
            ),
        },
    }

    # Tentativa 1: vídeo/imagem com formato único (sem merge FFmpeg)
    # Tentativa 2: sem restrição de formato (pega qualquer coisa, inclusive imagens)
    tentativas = [
        base_opts,
        {**base_opts, 'format': None},
    ]
    _ERROS_FORMATO = (
        'no video', 'no formats', 'requested format not available',
        'there is no video', 'no media', 'unable to extract',
    )

    info = None
    ultimo_erro = None
    for opts in tentativas:
        _opts = {k: v for k, v in opts.items() if v is not None}
        try:
            with yt_dlp.YoutubeDL(_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            break
        except Exception as e:
            ultimo_erro = e
            if any(k in str(e).lower() for k in _ERROS_FORMATO):
                continue
            raise

    if info is None:
        raise ultimo_erro or ValueError("Nenhum formato disponível.")

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


@Client.on_message(cmd_filter("dlinfo") & filters.me)
async def cmd_dlinfo(client, message):
    """Mostra informações do vídeo (título, duração, canal, tamanho) sem baixar."""
    if not HAS_YTDLP:
        return await message.edit_text(tr("❌ `yt-dlp` não instalado.", "❌ `yt-dlp` not installed."))

    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}dlinfo [link]`", f"⚠️ Use: `{p}dlinfo [link]`"))

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
    """Baixa mídia de redes sociais (Instagram, TikTok, YouTube, etc.)."""
    if not HAS_YTDLP and not HAS_INSTALOADER:
        return await message.edit_text(tr("❌ `yt-dlp` não instalado.", "❌ `yt-dlp` not installed."))

    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}dl [link]`", f"⚠️ Use: `{p}dl [link]`"))

    url = partes[1].strip()
    msg = await message.edit_text(tr(
        "📥 **Baixando...**\nIsso pode demorar dependendo do tamanho.",
        "📥 **Downloading...**\nThis might take a while depending on size."
    ))

    tmp_dir = tempfile.gettempdir()
    arquivo = None
    is_instagram = bool(_IG_RE.search(url))

    def baixar():
        # Para Instagram: tenta yt-dlp primeiro; se falhar, usa instaloader
        # Para demais plataformas: só yt-dlp
        if HAS_YTDLP:
            try:
                return _baixar_ytdlp(url, tmp_dir)
            except Exception as e:
                if is_instagram and HAS_INSTALOADER:
                    return _baixar_instaloader(url, tmp_dir)
                raise
        if is_instagram and HAS_INSTALOADER:
            return _baixar_instaloader(url, tmp_dir)
        raise RuntimeError("Nenhum downloader disponível.")

    try:
        arquivo, titulo = await asyncio.to_thread(baixar)
        if not arquivo or not os.path.exists(arquivo):
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
