"""
plugins/drive.py
Comandos do Google Drive: status, organizar, get, direto, procurar, apagar
"""
import os
import time
import asyncio
import aiohttp
import humanize
import tempfile

from googleapiclient.http import MediaFileUpload
from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, salvar, carregar, deletar_depois
from utils.i18n import tr

# Throttle de edições de progresso (msg.id → último timestamp)
_DL_THROTTLE: dict[int, float] = {}


def _barra(pct: int) -> str:
    filled = max(0, min(10, pct // 10))
    return "█" * filled + "░" * (10 - filled)


async def _dl_progress_cb(current: int, total: int, msg) -> None:
    """Callback de progresso do download do Telegram (throttled a 2s)."""
    if not total:
        return
    now = time.monotonic()
    if now - _DL_THROTTLE.get(msg.id, 0.0) < 2.0:
        return
    _DL_THROTTLE[msg.id] = now
    pct = int(current * 100 / total)
    bar = _barra(pct)
    mb  = f"{current/1_048_576:.1f}/{total/1_048_576:.1f} MB"
    try:
        await msg.edit_text(tr(
            f"📥 **Baixando do Telegram...**\n`[{bar}]` `{pct}%` — `{mb}`",
            f"📥 **Downloading from Telegram...**\n`[{bar}]` `{pct}%` — `{mb}`",
        ))
    except Exception:
        pass


async def _upload_com_progresso(service, local: str, nome: str, id_pasta: str, msg) -> dict:
    """Upload chunked via Drive API v2 com barra de progresso em tempo real."""
    file_size = os.path.getsize(local)
    media     = MediaFileUpload(local, resumable=True, chunksize=1 * 1024 * 1024)
    body      = {"title": nome, "parents": [{"id": id_pasta}]}
    req       = service.files().insert(body=body, media_body=media, fields="id,alternateLink")

    response  = None
    last_edit = 0.0

    while response is None:
        status, response = await asyncio.to_thread(req.next_chunk)
        if status is not None:
            pct     = int(status.progress() * 100)
            now     = time.monotonic()
            if now - last_edit >= 2.0:
                last_edit = now
                bar      = _barra(pct)
                done_mb  = status.resumable_progress / 1_048_576
                total_mb = (status.total_size or file_size) / 1_048_576
                try:
                    await msg.edit_text(tr(
                        f"☁️ **Enviando para o Drive...**\n`[{bar}]` `{pct}%` — `{done_mb:.1f}/{total_mb:.1f} MB`",
                        f"☁️ **Uploading to Drive...**\n`[{bar}]` `{pct}%` — `{done_mb:.1f}/{total_mb:.1f} MB`",
                    ))
                except Exception:
                    pass

    return response

CATEGORIAS = {
    '.apk': 'Apps', '.zip': 'Zips', '.rar': 'Zips', '.7z': 'Zips',
    '.exe': 'Windows', '.msi': 'Windows',
    '.mp4': 'Videos', '.mkv': 'Videos', '.avi': 'Videos',
    '.mp3': 'Audios', '.ogg': 'Audios', '.wav': 'Audios',
    '.pdf': 'Docs', '.docx': 'Docs', '.txt': 'Docs',
    '.jpg': 'Fotos', '.jpeg': 'Fotos', '.png': 'Fotos', '.gif': 'Fotos'
}

CACHE_PASTAS = {}
ULTIMA_BUSCA = {}


def obter_pasta(client, nome):
    """Retorna ID da pasta no Drive, criando se não existir. Usa cache."""
    if nome in CACHE_PASTAS:
        return CACHE_PASTAS[nome]
    drive = getattr(client, "drive", None)
    cfg = getattr(client, "config", {})
    raiz = cfg.get("ID_PASTA_RAIZ_DRIVE")
    if not drive:
        return raiz
    query = f"'{raiz}' in parents and title = '{nome}' and trashed = false"
    pastas = drive.ListFile({'q': query}).GetList()
    if pastas:
        CACHE_PASTAS[nome] = pastas[0]['id']
        return pastas[0]['id']
    nova = drive.CreateFile({
        'title': nome,
        'parents': [{'id': raiz}],
        'mimeType': 'application/vnd.google-apps.folder'
    })
    nova.Upload()
    CACHE_PASTAS[nome] = nova['id']
    return nova['id']


@Client.on_message(cmd_filter("status") & filters.me)
async def drive_status(client, message):
    """Mostra espaço usado e disponível no Drive."""
    deletar_depois(message, 30)
    drive = getattr(client, "drive", None)
    if not drive:
        return await message.edit_text(tr("❌ Drive não conectado.", "❌ Drive not connected."))
    try:
        def fetch_status():
            return drive.GetAbout()
            
        sobre = await asyncio.to_thread(fetch_status)
        total = int(sobre.get('quotaBytesTotal', 1))
        usado = int(sobre.get('quotaBytesUsedAggregate', 0))
        pct = (usado / total) * 100 if total > 0 else 0
        barras = "".join(["🟥" if i < int(pct // 10) else "🟩" for i in range(10)])
        await message.edit_text(
            f"📊 **Google Drive**\n\n"
            f"`[{barras}]` {pct:.1f}%\n"
            f"☁️ `{humanize.naturalsize(usado)}` / `{humanize.naturalsize(total)}`"
        )
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@Client.on_message(cmd_filter("organizar") & filters.me)
async def drive_organizar(client, message):
    """Organiza arquivos da raiz em subpastas por tipo."""
    drive = getattr(client, "drive", None)
    if not drive:
        return await message.edit_text(tr("❌ Drive não conectado.", "❌ Drive not connected."))
    msg = await message.edit_text(tr("🗂️ **Organizando arquivos...**", "🗂️ **Organizing files...**"))
    try:
        def do_organize():
            cfg = getattr(client, "config", {})
            raiz = cfg.get("ID_PASTA_RAIZ_DRIVE")
            if not raiz:
                raise ValueError("ID da pasta raiz não configurado.")
            
            query = f"'{raiz}' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'"
            arquivos = drive.ListFile({'q': query}).GetList()
            movidos = 0
            for arq in arquivos:
                ext = os.path.splitext(arq['title'])[1].lower()
                categoria = CATEGORIAS.get(ext, 'Outros')
                id_destino = obter_pasta(client, categoria)
                
                # Move o arquivo removendo as pastas pai anteriores (PyDrive API wrapper)
                old_parents = ",".join([p['id'] for p in arq.get('parents', [])])
                drive.auth.service.files().update(
                    fileId=arq['id'],
                    addParents=id_destino,
                    removeParents=old_parents,
                    fields='id, parents'
                ).execute()
                movidos += 1
            return movidos
            
        movidos = await asyncio.to_thread(do_organize)
        await msg.edit_text(tr(f"✅ **Organização concluída!**\n📦 `{movidos}` arquivos movidos da raiz para subpastas.", f"✅ **Organization complete!**\n📦 `{movidos}` files moved from root to subfolders."))
    except Exception as e:
        await msg.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))
    deletar_depois(msg, 30)


@Client.on_message(cmd_filter("get") & filters.me)
async def drive_get(client, message):
    """Baixa arquivo de uma URL direto para o Drive."""
    drive = getattr(client, "drive", None)
    if not drive:
        return await message.edit_text(tr("❌ Drive não conectado.", "❌ Drive not connected."))
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{prefixo(client)}get [URL]`", f"⚠️ Use: `{prefixo(client)}get [URL]`"))
    url = partes[1].strip()
    msg = await message.edit_text(tr("📥 **Baixando arquivo da URL...**", "📥 **Downloading file from URL...**"))
    try:
        nome = url.split("/")[-1].split("?")[0] or "arquivo"
        local = os.path.join(tempfile.gettempdir(), nome)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                r.raise_for_status()
                with open(local, "wb") as f:
                    async for chunk in r.content.iter_chunked(1024 * 1024):
                        f.write(chunk)
                        
        await msg.edit_text(tr("☁️ **Enviando para o Google Drive...**", "☁️ **Uploading to Google Drive...**"))
        
        def do_upload():
            ext = os.path.splitext(nome)[1].lower()
            categoria = CATEGORIAS.get(ext, 'Outros')
            id_pasta = obter_pasta(client, categoria)
            f_drive = drive.CreateFile({'title': nome, 'parents': [{'id': id_pasta}]})
            f_drive.SetContentFile(local)
            f_drive.Upload()
            f_drive.InsertPermission({'type': 'anyone', 'value': 'anyone', 'role': 'reader'})
            return f_drive, categoria
            
        f_drive, categoria = await asyncio.to_thread(do_upload)
        os.remove(local)
        await msg.edit_text(tr(
            f"✅ **Transferência Concluída!**\n"
            f"├ 📁 **Arquivo:** `{nome}`\n"
            f"├ 🗂️ **Categoria:** `{categoria}`\n"
            f"└ 🔗 [Acessar no Google Drive]({f_drive['alternateLink']})",
            f"✅ **Transfer Complete!**\n"
            f"├ 📁 **File:** `{nome}`\n"
            f"├ 🗂️ **Category:** `{categoria}`\n"
            f"└ 🔗 [Access on Google Drive]({f_drive['alternateLink']})"
        ))
    except Exception as e:
        await msg.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))
    deletar_depois(msg, 30)


@Client.on_message(cmd_filter("direto") & filters.me)
async def drive_direto(client, message):
    """Envia arquivo do Telegram para o Drive com progresso."""
    drive = getattr(client, "drive", None)
    if not drive:
        return await message.edit_text(tr("❌ Drive não conectado.", "❌ Drive not connected."))

    reply = message.reply_to_message
    if not reply:
        p = prefixo(client)
        return await message.edit_text(tr(
            f"⚠️ Responda a um arquivo com `{p}direto` para enviá-lo ao Drive.",
            f"⚠️ Reply to a file with `{p}direct` to upload it to Drive.",
        ))

    media = reply.document or reply.video or reply.audio or reply.photo or reply.voice or reply.video_note
    if not media:
        return await message.edit_text(tr(
            "⚠️ A mensagem não contém nenhum arquivo.",
            "⚠️ The message does not contain any file.",
        ))

    if reply.document:
        nome = reply.document.file_name or f"arquivo_{reply.document.file_unique_id[:8]}"
    elif reply.video:
        nome = reply.video.file_name or f"video_{reply.video.file_unique_id[:8]}.mp4"
    elif reply.audio:
        nome = reply.audio.file_name or f"audio_{reply.audio.file_unique_id[:8]}.mp3"
    elif reply.photo:
        nome = f"foto_{reply.photo.file_unique_id[:8]}.jpg"
    elif reply.voice:
        nome = f"voice_{reply.voice.file_unique_id[:8]}.ogg"
    else:
        nome = f"video_{reply.video_note.file_unique_id[:8]}.mp4"

    msg   = await message.edit_text(tr("📥 **Baixando do Telegram...**", "📥 **Downloading from Telegram...**"))
    local = None
    try:
        local = await client.download_media(
            reply,
            file_name=os.path.join(tempfile.gettempdir(), nome),
            progress=_dl_progress_cb,
            progress_args=(msg,),
        )

        ext       = os.path.splitext(nome)[1].lower()
        categoria = CATEGORIAS.get(ext, "Outros")
        id_pasta  = await asyncio.to_thread(obter_pasta, client, categoria)

        service  = drive.auth.service
        response = await _upload_com_progresso(service, local, nome, id_pasta, msg)

        await asyncio.to_thread(
            lambda: service.permissions().insert(
                fileId=response["id"],
                body={"type": "anyone", "role": "reader"},
            ).execute()
        )

        link_direto = f"https://drive.google.com/uc?export=download&id={response['id']}"
        await msg.edit_text(tr(
            f"✅ **Upload Concluído!**\n"
            f"├ 📁 **Arquivo:** `{nome}`\n"
            f"├ 🗂️ **Categoria:** `{categoria}`\n"
            f"├ 🔗 [Abrir no Drive]({response['alternateLink']})\n"
            f"└ 📎 **Link direto:** `{link_direto}`",
            f"✅ **Upload Complete!**\n"
            f"├ 📁 **File:** `{nome}`\n"
            f"├ 🗂️ **Category:** `{categoria}`\n"
            f"├ 🔗 [Open in Drive]({response['alternateLink']})\n"
            f"└ 📎 **Direct link:** `{link_direto}`",
        ))
    except Exception as e:
        await msg.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))
    finally:
        if local and os.path.exists(local):
            try:
                os.remove(local)
            except Exception:
                pass
    deletar_depois(msg, 60)


@Client.on_message(cmd_filter("procurar") & filters.me)
async def drive_procurar(client, message):
    """Busca arquivos no Drive pelo nome e lista resultados."""
    deletar_depois(message, 60)
    drive = getattr(client, "drive", None)
    if not drive:
        return await message.edit_text(tr("❌ Drive não conectado.", "❌ Drive not connected."))
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}procurar [termo]`", f"⚠️ Use: `{p}search [term]`"))
    termo = partes[1].strip()
    await message.edit_text(tr(f"🔎 **Procurando:** `{termo}`...", f"🔎 **Searching:** `{termo}`..."))
    try:
        def do_search():
            termo_safe = termo.replace("'", "\\'")
            return drive.ListFile({'q': f"title contains '{termo_safe}' and trashed=false"}).GetList()
            
        arquivos = await asyncio.to_thread(do_search)
        if not arquivos:
            return await message.edit_text(tr("❌ Nenhum arquivo encontrado.", "❌ No files found."))
        global ULTIMA_BUSCA
        ULTIMA_BUSCA = {}
        txt = tr(f"🔎 **Resultados para '{termo}':**\n\n", f"🔎 **Results for '{termo}':**\n\n")
        for i, arq in enumerate(arquivos[:10], 1):
            ULTIMA_BUSCA[str(i)] = {'id': arq['id'], 'title': arq['title']}
            tam = humanize.naturalsize(int(arq.get('fileSize', 0))) if arq.get('fileSize') else tr("Pasta", "Folder")
            txt += f"**[{i}]** `{arq['title']}` ({tam})\n"
        txt += tr(f"\n💡 Use `{p}apagar [N]` para excluir.", f"\n💡 Use `{p}delete [N]` to delete.")
        await message.edit_text(txt)
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@Client.on_message(cmd_filter("apagar") & filters.me)
async def drive_apagar(client, message):
    """Move arquivo da última busca para a lixeira do Drive."""
    deletar_depois(message, 20)
    drive = getattr(client, "drive", None)
    if not drive:
        return await message.edit_text(tr("❌ Drive não conectado.", "❌ Drive not connected."))
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}apagar [N]` (após `{p}procurar`)", f"⚠️ Use: `{p}delete [N]` (after `{p}search`)"))
    num = partes[1].strip()
    global ULTIMA_BUSCA
    if num not in ULTIMA_BUSCA:
        return await message.edit_text(tr("❌ Número inválido. Faça uma busca primeiro.", "❌ Invalid number. Do a search first."))
    item = ULTIMA_BUSCA[num]
    try:
        def do_trash():
            f = drive.CreateFile({'id': item['id']})
            f.Trash()
        await asyncio.to_thread(do_trash)
        await message.edit_text(tr(f"🗑️ **Movido para a lixeira:**\n📁 `{item['title']}`", f"🗑️ **Moved to trash:**\n📁 `{item['title']}`"))
        del ULTIMA_BUSCA[num]
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))
