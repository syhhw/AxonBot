"""
plugins/profile.py
  ,setname [nome]  — altera seu nome no Telegram.
  ,setbio [texto]  — altera sua bio.
  ,setpfp          — define foto de perfil (responda a uma foto).
  ,delpfp          — remove a foto de perfil atual.
"""
import os
import tempfile

from pyrogram.raw import functions

from utils.commands import cmd
from utils.helpers import tr


@cmd("setname")
async def cmd_setname(client, message):
    """Altera seu nome no Telegram. Ex: ,setname João Silva"""
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        return await message.edit_text(tr(
            "⚠️ Uso: `,setname [primeiro] [último]`",
            "⚠️ Usage: `,setname [first] [last]`",
        ))

    name_parts = parts[1].strip().split(None, 1)
    first = name_parts[0]
    last  = name_parts[1] if len(name_parts) > 1 else ""

    await client.invoke(functions.account.UpdateProfile(
        first_name=first,
        last_name=last,
    ))
    await message.edit_text(tr(
        f"✅ Nome atualizado para **{first} {last}**",
        f"✅ Name updated to **{first} {last}**",
    ))


@cmd("setbio")
async def cmd_setbio(client, message):
    """Altera sua bio do Telegram. Ex: ,setbio Olá, sou eu!"""
    parts = message.text.split(None, 1)
    bio = parts[1].strip() if len(parts) > 1 else ""

    await client.invoke(functions.account.UpdateProfile(about=bio))
    await message.edit_text(tr(
        "✅ Bio atualizada.",
        "✅ Bio updated.",
    ))


@cmd("setpfp")
async def cmd_setpfp(client, message):
    """Define sua foto de perfil. Responda a uma foto com este comando."""
    reply = message.reply_to_message
    if not reply or not (reply.photo or (reply.document and "image" in (reply.document.mime_type or ""))):
        return await message.edit_text(tr(
            "⚠️ Responda a uma **foto** com este comando.",
            "⚠️ Reply to a **photo** with this command.",
        ))

    await message.edit_text(tr("⏳ Atualizando foto de perfil...", "⏳ Updating profile photo..."))

    tmp = tempfile.mktemp(suffix=".jpg")
    try:
        await client.download_media(reply, file_name=tmp)
        await client.invoke(functions.photos.UploadProfilePhoto(
            file=await client.save_file(tmp),
        ))
        await message.edit_text(tr("✅ Foto de perfil atualizada!", "✅ Profile photo updated!"))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@cmd("delpfp")
async def cmd_delpfp(client, message):
    """Remove a foto de perfil atual."""
    await message.edit_text(tr("⏳ Removendo foto de perfil...", "⏳ Removing profile photo..."))
    try:
        photos = await client.invoke(functions.photos.GetUserPhotos(
            user_id=await client.resolve_peer("me"),
            offset=0,
            max_id=0,
            limit=1,
        ))
        if not photos.photos:
            return await message.edit_text(tr(
                "⚠️ Nenhuma foto de perfil encontrada.",
                "⚠️ No profile photo found.",
            ))
        photo = photos.photos[0]
        await client.invoke(functions.photos.DeletePhotos(
            id=[functions.photos.DeletePhotos.__self__] if False else [
                __import__("pyrogram.raw.types", fromlist=["InputPhoto"]).InputPhoto(
                    id=photo.id,
                    access_hash=photo.access_hash,
                    file_reference=photo.file_reference,
                )
            ]
        ))
        await message.edit_text(tr("✅ Foto de perfil removida!", "✅ Profile photo removed!"))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))
