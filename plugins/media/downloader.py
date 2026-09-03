"""
plugins/downloader.py
Baixador universal: tikwm API (TikTok), yt-dlp, instaloader (Instagram).
  ,dlinfo [link] — mostra título, duração, canal e tamanho estimado
  ,dl [link]     — baixa e envia o arquivo (vídeo, imagem ou áudio)
"""
import asyncio
import logging
import os
import re
import shutil
import tempfile

import aiofiles
import aiohttp

from utils.commands import cmd
from utils.helpers import prefixo, tr

logger = logging.getLogger("AxonBot.downloader")

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

_IG_RE = re.compile(r'instagram\.com/(?:p|reel|tv|reels)/([A-Za-z0-9_-]+)', re.IGNORECASE)


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


_IS_TIKTOK = re.compile(r'tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com', re.IGNORECASE)
_IS_FACEBOOK = re.compile(r'facebook\.com|fb\.watch|fb\.com', re.IGNORECASE)
_TIKWM_API = "https://www.tikwm.com/api/"

_DL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
)
_DL_HDRS = {
    'User-Agent':      _DL_UA,
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-GPC':         '1',
}


async def _baixar_saveinsta(url: str, tmp_dir: str):
    """
    Download Instagram via saveinsta.to (proxies Instagram CDN, no auth needed).
    Flow: GET page → extract k_exp/k_token → get JWT cftoken → POST ajaxSearch → parse dl link.
    """
    m = _IG_RE.search(url)
    if not m:
        raise ValueError("Instagram shortcode not found")
    shortcode = m.group(1)

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        # Step 1: extract k_exp and k_token from homepage JS
        async with sess.get('https://saveinsta.to/en/highlights', headers=_DL_HDRS) as r:
            if r.status != 200:
                raise ValueError(f"saveinsta.to GET {r.status}")
            page = await r.text()

        mo = re.search(r'<script[^>]*>var\s+k_url_search="[^"]+"(.*?)</script>', page, re.DOTALL)
        if not mo:
            raise ValueError("saveinsta.to: JS token block not found")
        script = mo.group(1)
        k_exp   = re.search(r'k_exp\s*=\s*"([^"]+)"', script)
        k_token = re.search(r'k_token\s*=\s*"([^"]+)"', script)
        if not k_exp or not k_token:
            raise ValueError("saveinsta.to: k_exp/k_token not found")
        k_exp, k_token = k_exp.group(1), k_token.group(1)

        # Step 2: get JWT cftoken
        post_hdrs = {**_DL_HDRS, 'X-Requested-With': 'XMLHttpRequest',
                     'Content-Type': 'application/x-www-form-urlencoded',
                     'Origin': 'https://saveinsta.to'}
        async with sess.post('https://saveinsta.to/api/userverify',
                             headers=post_hdrs, data={'url': url}) as r:
            data2 = await r.json(content_type=None)
        cftoken = data2.get('token', '')
        if not cftoken:
            raise ValueError("saveinsta.to: cftoken not returned")

        # Step 3: get download HTML
        async with sess.post('https://saveinsta.to/api/ajaxSearch',
                             headers={**post_hdrs, 'Referer': 'https://saveinsta.to/en/highlights'},
                             data={'k_exp': k_exp, 'k_token': k_token, 'q': url,
                                   't': 'media', 'lang': 'en', 'v': 'v2', 'cftoken': cftoken}) as r:
            data3 = await r.json(content_type=None)

    if data3.get('status') != 'ok':
        raise ValueError(f"saveinsta.to: bad status {data3.get('status')}")

    media_html = data3.get('data', '')

    # Find video download URLs: <div class="download-items__btn"> (not dl-thumb)
    video_url = None
    for btn in re.findall(r'<div class="download-items__btn">(.*?)</div>', media_html, re.DOTALL):
        href = re.search(r'href="(https://dl\.snapcdn\.app[^"]+)"', btn)
        if href:
            video_url = href.group(1)
            break

    if not video_url:
        # Fallback: any snapcdn URL that isn't labeled as thumbnail
        snap_urls = re.findall(r'href="(https://dl\.snapcdn\.app[^"]+)"', media_html)
        for u in snap_urls:
            idx = media_html.find(u)
            context = media_html[max(0, idx-300):idx]
            if 'Thumbnail' not in context and 'thumbnail' not in context:
                video_url = u
                break

    if not video_url:
        raise ValueError("saveinsta.to: no video download URL found")

    path = os.path.join(tmp_dir, f"ig_{shortcode}.mp4")
    dl_timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=dl_timeout) as sess:
        async with sess.get(video_url, headers={**_DL_HDRS, 'Referer': 'https://saveinsta.to/'}) as r:
            r.raise_for_status()
            async with aiofiles.open(path, 'wb') as f:
                async for chunk in r.content.iter_chunked(65536):
                    await f.write(chunk)

    return path, shortcode




async def _baixar_tiktok_api(url: str, tmp_dir: str):
    """Baixa TikTok via tikwm.com (não precisa de cookies nem de yt-dlp)."""
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        async with sess.post(
            _TIKWM_API,
            data={"url": url, "hd": "1"},
            headers={"User-Agent": "Mozilla/5.0"},
        ) as resp:
            data = await resp.json(content_type=None)

    if data.get("code") != 0:
        raise ValueError(f"tikwm: {data.get('msg', 'erro desconhecido')}")

    info      = data["data"]
    video_url = info.get("hdplay") or info.get("play")
    titulo    = (info.get("title") or "TikTok Video")[:100]

    if not video_url:
        raise ValueError("tikwm: sem URL de vídeo na resposta.")

    path = os.path.join(tmp_dir, f"tiktok_{info.get('id', 'video')}.mp4")
    dl_timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=dl_timeout) as sess:
        async with sess.get(
            video_url,
            headers={"Referer": "https://www.tiktok.com/"},
        ) as resp:
            resp.raise_for_status()
            async with aiofiles.open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(65536):
                    await f.write(chunk)

    return path, titulo


def _baixar_ytdlp(url: str, tmp_dir: str):
    """Download via yt-dlp com múltiplos formatos de fallback."""
    base_opts = {
        'format':       'best[ext=mp4]/best[ext=webm]/best',
        'outtmpl':      os.path.join(tmp_dir, 'dl_%(id)s.%(ext)s'),
        'quiet':        True,
        'no_warnings':  True,
        'max_filesize': 1500 * 1024 * 1024,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) '
                'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
            ),
        },
    }

    # Opções extras para TikTok — contorna bloqueios de API
    if _IS_TIKTOK.search(url):
        base_opts['http_headers']['User-Agent'] = (
            'com.zhiliaoapp.musically/2022600030 '
            '(Linux; U; Android 9; en_US; Pixel 4; Build/PI;tt-ok/3.12.13.1)'
        )
        base_opts['extractor_args'] = {
            'tiktok': {'api_hostname': 'api22-normal-c-useast2a.tiktok.com'},
        }

    tentativas = [
        base_opts,
        {**base_opts, 'format': None},   # sem restrição — pega imagens também
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

    rds  = [r for r in (info.get('requested_downloads') or []) if r]
    path = rds[0].get('filepath') if rds else None

    if not path or not os.path.exists(path):
        base = os.path.join(tmp_dir, f"dl_{info.get('id', '')}")
        for _ext in ('.mp4', '.webm', '.mkv', '.jpg', '.jpeg', '.png', '.webp', '.mp3', '.m4a'):
            candidate = base + _ext
            if os.path.exists(candidate):
                path = candidate
                break

    return path, info.get('title', 'Video')


@cmd("dlinfo")
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


@cmd("dl")
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

    tmp_dir      = tempfile.mkdtemp(prefix="ubdl_")
    arquivo      = None
    is_instagram = bool(_IG_RE.search(url))
    is_tiktok    = bool(_IS_TIKTOK.search(url))

    async def resolver():
        # ── TikTok: tikwm API ────────────────────────────────────────────────
        if is_tiktok:
            try:
                return await _baixar_tiktok_api(url, tmp_dir)
            except Exception as e:
                logger.debug(f"[downloader.py] ignorado: {e}")  # fallback to yt-dlp

        # ── Instagram: saveinsta.to → yt-dlp → instaloader (no auth) ─────────
        if is_instagram:
            ig_errors = []

            try:
                return await _baixar_saveinsta(url, tmp_dir)
            except Exception as _e:
                ig_errors.append(f"saveinsta: {_e}")

            if HAS_YTDLP:
                try:
                    return await asyncio.to_thread(_baixar_ytdlp, url, tmp_dir)
                except Exception as _e:
                    ig_errors.append(f"yt-dlp: {_e}")

            if HAS_INSTALOADER:
                try:
                    return await asyncio.to_thread(_baixar_instaloader, url, tmp_dir)
                except Exception as _e:
                    ig_errors.append(f"instaloader: {_e}")

            raise ValueError(
                "All Instagram download methods failed:\n" +
                "\n".join(f"• {e}" for e in ig_errors)
            )

        # ── yt-dlp (YouTube, Facebook, Twitter, and other platforms) ─────────
        if HAS_YTDLP:
            return await asyncio.to_thread(_baixar_ytdlp, url, tmp_dir)

        raise RuntimeError("No downloader available for this link.")

    try:
        arquivo, titulo = await resolver()
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
        shutil.rmtree(tmp_dir, ignore_errors=True)
