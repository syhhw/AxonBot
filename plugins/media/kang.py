"""
plugins/kang.py
Comando ,kang — Rouba figurinhas e adiciona ao pacote via raw MTProto API.
Não depende do @Stickers bot. Detecta packs existentes via getAllStickers
para funcionar mesmo após troca de username.

Créditos: ,kang é um padrão consagrado do ecossistema de userbots Telegram
(Man-Userbot e forks). Implementação via raw MTProto é própria.
"""
import logging
import os
import math
import asyncio
import tempfile
logger = logging.getLogger("AxonBot.kang")

from PIL import Image
from pyrogram import filters, Client, raw
from pyrogram.raw.types import InputStickerSetShortName
from pyrogram.errors import StickersetInvalid
from utils.helpers import prefixo
from utils.commands import cmd
from utils.i18n import tr

TMP_DIR  = tempfile.gettempdir()
TMP_WEBP = os.path.join(TMP_DIR, "kang_in.webp")
TMP_OUT  = os.path.join(TMP_DIR, "kang_out.webp")

# Limites de figurinhas por pacote
_MAX_STATIC = 120
_MAX_OTHER  = 50


# ─── Utilitários ──────────────────────────────────────────────────────────────

async def pack_exists(client, packname: str) -> bool:
    try:
        await client.invoke(
            raw.functions.messages.GetStickerSet(
                stickerset=InputStickerSetShortName(short_name=packname),
                hash=0,
            )
        )
        return True
    except Exception:
        return False


def _resize_sync(src: str, dst: str) -> str:
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    if w >= h:
        new_w, new_h = 512, max(1, math.floor(h * 512 / w))
    else:
        new_w, new_h = max(1, math.floor(w * 512 / h)), 512
    img = img.resize((new_w, new_h), Image.LANCZOS)
    img.save(dst, "WEBP")
    return dst


def limpar_tmp():
    for p in [TMP_WEBP, TMP_OUT]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception as e:
            logger.debug(f"[kang.py] ignorado: {e}")


async def _get_input_doc(client, reply) -> raw.types.InputDocument:
    """Retorna InputDocument para a figurinha/foto respondida."""
    if reply.sticker:
        from pyrogram.file_id import FileId
        fid = FileId.decode(reply.sticker.file_id)
        return raw.types.InputDocument(
            id=fid.media_id,
            access_hash=fid.access_hash,
            file_reference=fid.file_reference,
        )

    # Foto ou documento — baixa, redimensiona e faz upload
    await client.download_media(reply, file_name=TMP_WEBP)
    await asyncio.to_thread(_resize_sync, TMP_WEBP, TMP_OUT)

    me_peer    = await client.resolve_peer("me")
    input_file = await client.save_file(TMP_OUT)
    result     = await client.invoke(
        raw.functions.messages.UploadMedia(
            peer=me_peer,
            media=raw.types.InputMediaUploadedDocument(
                file=input_file,
                mime_type="image/webp",
                attributes=[
                    raw.types.DocumentAttributeFilename(file_name="sticker.webp")
                ],
            ),
        )
    )
    doc = result.document
    return raw.types.InputDocument(
        id=doc.id,
        access_hash=doc.access_hash,
        file_reference=doc.file_reference,
    )


async def _find_available_pack(client, me_id: int, is_anim: bool, is_video: bool) -> str | None:
    """
    Busca via getAllStickers um pack do usuário com espaço disponível.
    Funciona independente do username atual — identifica packs pelo ID do usuário.
    """
    try:
        result = await client.invoke(raw.functions.messages.GetAllStickers(hash=0))
    except Exception:
        return None

    prefix  = f"a{me_id}_by_"
    max_cap = _MAX_OTHER if (is_anim or is_video) else _MAX_STATIC

    for sset in getattr(result, "sets", []):
        name = sset.short_name
        if not name.startswith(prefix):
            continue
        # Filtra pelo tipo correto
        if is_anim  and not getattr(sset, "animated", False):
            continue
        if is_video and not getattr(sset, "videos", False):
            continue
        if not is_anim and not is_video:
            if getattr(sset, "animated", False) or getattr(sset, "videos", False):
                continue
        # Tem espaço?
        if getattr(sset, "count", 0) < max_cap:
            return name

    return None


async def _next_pack_name(client, me_id: int, username: str, is_anim: bool, is_video: bool) -> tuple[str, str]:
    """Encontra o próximo nome de pack disponível para criação."""
    num = 1
    while True:
        if is_anim:
            name = f"a{me_id}_by_{username}_{num}_anim"
            nick = f"@{username} animated pack {num}"
        elif is_video:
            name = f"a{me_id}_by_{username}_{num}_vid"
            nick = f"@{username} video pack {num}"
        else:
            name = f"a{me_id}_by_{username}_{num}"
            nick = f"@{username} userbot pack {num}"

        if not await pack_exists(client, name):
            return name, nick
        num += 1


# ─── Comando ,kang ────────────────────────────────────────────────────────────

@cmd("kang")
async def cmd_kang(client, message):
    """
    Rouba figurinha/foto e adiciona ao seu pacote via API direta.
    Uso: ,kang [emoji]
    """
    p     = prefixo(client)
    reply = message.reply_to_message

    if not reply or not (reply.sticker or reply.photo or reply.document):
        return await message.edit_text(tr(
            f"⚠️ Responda a uma **figurinha** ou **foto** com `{p}kang [emoji]`",
            f"⚠️ Reply to a **sticker** or **photo** with `{p}kang [emoji]`",
        ))

    await message.edit_text(tr("🔄 **Kanging...**", "🔄 **Kanging...**"))

    me       = await client.get_me()
    me_peer  = await client.resolve_peer("me")
    username = me.username or str(me.id)

    # ── Tipo e emoji ───────────────────────────────────────────────────────────
    is_anim = is_video = False
    emoji   = "⭐"

    partes = message.text.split(None, 1)
    user_emoji = partes[1].strip() if len(partes) > 1 else None

    if reply.sticker:
        is_anim  = reply.sticker.is_animated
        is_video = reply.sticker.is_video
        emoji    = user_emoji or reply.sticker.emoji or "⭐"
    else:
        emoji = user_emoji or "⭐"

    # ── InputDocument ──────────────────────────────────────────────────────────
    try:
        input_doc = await _get_input_doc(client, reply)
    except Exception as e:
        limpar_tmp()
        return await message.edit_text(tr(
            f"❌ Erro ao processar mídia:\n`{e}`",
            f"❌ Error processing media:\n`{e}`",
        ))

    sticker_item = raw.types.InputStickerSetItem(document=input_doc, emoji=emoji)

    kwargs_create = {}
    if is_anim:  kwargs_create["animated"] = True
    if is_video: kwargs_create["videos"]   = True

    # ── Tenta encontrar pack existente com espaço ──────────────────────────────
    packname = await _find_available_pack(client, me.id, is_anim, is_video)

    created_new = False

    if packname:
        # Adiciona ao pack encontrado
        try:
            await client.invoke(
                raw.functions.stickers.AddStickerToSet(
                    stickerset=InputStickerSetShortName(short_name=packname),
                    sticker=sticker_item,
                )
            )
            # Garante que o pack está instalado na conta (AddStickerToSet não instala)
            await client.invoke(
                raw.functions.messages.InstallStickerSet(
                    stickerset=InputStickerSetShortName(short_name=packname),
                    archived=False,
                )
            )
        except Exception as e:
            err = str(e)
            if "STICKERS_TOO_MUCH" in err or "TOO_MUCH" in err:
                packname = None  # pack ficou cheio no último momento
            else:
                limpar_tmp()
                return await message.edit_text(tr(
                    f"❌ Erro ao adicionar:\n`{err}`",
                    f"❌ Error adding sticker:\n`{err}`",
                ))

    if not packname:
        # Cria um novo pack
        packname, packnick = await _next_pack_name(client, me.id, username, is_anim, is_video)
        await message.edit_text(tr(
            "📦 **Criando novo pack...**",
            "📦 **Creating new pack...**",
        ))
        try:
            await client.invoke(
                raw.functions.stickers.CreateStickerSet(
                    user_id=me_peer,
                    title=packnick,
                    short_name=packname,
                    stickers=[sticker_item],
                    **kwargs_create,
                )
            )
            # CreateStickerSet já instala, mas chamamos explicitamente para garantir
            await client.invoke(
                raw.functions.messages.InstallStickerSet(
                    stickerset=InputStickerSetShortName(short_name=packname),
                    archived=False,
                )
            )
            created_new = True
        except Exception as e:
            limpar_tmp()
            return await message.edit_text(tr(
                f"❌ Erro ao criar pack:\n`{str(e)}`",
                f"❌ Error creating pack:\n`{str(e)}`",
            ))

    # ── Sucesso ────────────────────────────────────────────────────────────────
    limpar_tmp()
    pack_url = f"https://t.me/addstickers/{packname}"
    tipo = (
        tr("Animada 🎞️", "Animated 🎞️") if is_anim else
        tr("Vídeo 🎬",   "Video 🎬")     if is_video else
        tr("Estática 🖼️", "Static 🖼️")
    )
    novo_label = tr(" ✨ novo pack criado!", " ✨ new pack created!") if created_new else ""

    # Link no texto — userbots não suportam InlineKeyboardMarkup nas próprias msgs
    await message.edit_text(
        tr(
            f"✅ **Figurinha roubada!**{novo_label}\n\n"
            f"🎭 Tipo: `{tipo}`\n"
            f"😀 Emoji: `{emoji}`\n"
            f"📦 Pack: `{packname}`\n"
            f"🔗 [Adicionar ao Telegram]({pack_url})",
            f"✅ **Sticker kanged!**{novo_label}\n\n"
            f"🎭 Type: `{tipo}`\n"
            f"😀 Emoji: `{emoji}`\n"
            f"📦 Pack: `{packname}`\n"
            f"🔗 [Add to Telegram]({pack_url})",
        ),
        disable_web_page_preview=True,
    )


# ─── Comando ,packinfo ────────────────────────────────────────────────────────

@cmd("packinfo")
async def cmd_packinfo(client, message):
    """Lista todos os seus pacotes de figurinhas (qualquer username)."""
    me = await client.get_me()
    p  = prefixo(client)

    await message.edit_text(tr("🔍 **Buscando seus pacotes...**", "🔍 **Fetching your packs...**"))

    try:
        result = await client.invoke(raw.functions.messages.GetAllStickers(hash=0))
    except Exception as e:
        return await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))

    prefix = f"a{me.id}_by_"
    linhas = []

    for sset in getattr(result, "sets", []):
        name = sset.short_name
        if not name.startswith(prefix):
            continue
        url   = f"https://t.me/addstickers/{name}"
        count = getattr(sset, "count", "?")
        if getattr(sset, "animated", False):
            tipo = tr("Animado", "Animated")
        elif getattr(sset, "videos", False):
            tipo = tr("Vídeo", "Video")
        else:
            tipo = tr("Estático", "Static")
        linhas.append(f"• **[{name}]({url})** — {tipo}, `{count}` stickers")

    if not linhas:
        return await message.edit_text(tr(
            f"⚠️ Nenhum pacote encontrado.\nUse `{p}kang` respondendo a uma figurinha!",
            f"⚠️ No packs found.\nUse `{p}kang` replying to a sticker!",
        ))

    await message.edit_text(
        tr(f"📦 **Seus pacotes ({len(linhas)}):**\n\n", f"📦 **Your packs ({len(linhas)}):**\n\n")
        + "\n".join(linhas),
        disable_web_page_preview=True,
    )
