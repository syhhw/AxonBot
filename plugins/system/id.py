"""
plugins/id.py
  ,id — retorna o ID do chat, usuário ou mensagem respondida.
"""
from utils.commands import cmd
from utils.helpers import tr


@cmd("id")
async def cmd_id(client, message):
    """Retorna o ID do chat atual, usuário ou mensagem respondida."""
    reply = message.reply_to_message
    lines = []

    if reply:
        lines.append(tr(f"💬 **ID da mensagem:** `{reply.id}`", f"💬 **Message ID:** `{reply.id}`"))

        sender = reply.from_user or reply.sender_chat
        if sender:
            name = getattr(sender, "first_name", None) or getattr(sender, "title", "?")
            lines.append(tr(
                f"👤 **ID do remetente:** `{sender.id}` — {name}",
                f"👤 **Sender ID:** `{sender.id}` — {name}",
            ))

        if reply.media:
            media = (
                reply.photo or reply.video or reply.audio or reply.document
                or reply.sticker or reply.animation or reply.voice or reply.video_note
            )
            if media and hasattr(media, "file_id"):
                lines.append(tr(
                    f"📎 **File ID:** `{media.file_id}`",
                    f"📎 **File ID:** `{media.file_id}`",
                ))

    chat = message.chat
    chat_name = chat.title or chat.first_name or "?"
    lines.append(tr(
        f"👥 **ID do chat:** `{chat.id}` — {chat_name}",
        f"👥 **Chat ID:** `{chat.id}` — {chat_name}",
    ))

    await message.edit_text("\n".join(lines))
