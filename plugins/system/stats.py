"""
plugins/stats.py
  ,stats — exibe estatísticas da sua conta Telegram (grupos, canais, contatos, bots).
"""
import logging
import time

logger = logging.getLogger("AxonBot.stats")

from pyrogram.enums import ChatType

from utils.commands import cmd
from utils.helpers import tr


@cmd("stats")
async def cmd_stats(client, message):
    """Exibe estatísticas completas da sua conta Telegram."""
    await message.edit_text(tr("📊 **Coletando estatísticas...**", "📊 **Collecting stats...**"))

    start = time.time()
    privados = bots = grupos = supergrupos = canais = 0
    admin_grupos = admin_canais = criador = 0

    async for dialog in client.get_dialogs():
        t = dialog.chat.type
        if t == ChatType.PRIVATE:
            if dialog.chat.is_bot:
                bots += 1
            else:
                privados += 1
        elif t == ChatType.GROUP:
            grupos += 1
        elif t == ChatType.SUPERGROUP:
            supergrupos += 1
            me_member = None
            try:
                me_member = await client.get_chat_member(dialog.chat.id, "me")
            except Exception as e:
                logger.debug(f"[stats.py] ignorado: {e}")
            if me_member:
                from pyrogram.enums import ChatMemberStatus
                if me_member.status == ChatMemberStatus.OWNER:
                    criador += 1
                    admin_grupos += 1
                elif me_member.status == ChatMemberStatus.ADMINISTRATOR:
                    admin_grupos += 1
        elif t == ChatType.CHANNEL:
            canais += 1
            try:
                me_member = await client.get_chat_member(dialog.chat.id, "me")
                from pyrogram.enums import ChatMemberStatus
                if me_member.status == ChatMemberStatus.OWNER or me_member.status == ChatMemberStatus.ADMINISTRATOR:
                    admin_canais += 1
            except Exception as e:
                logger.debug(f"[stats.py] ignorado: {e}")

    elapsed = time.time() - start
    total = privados + bots + grupos + supergrupos + canais

    await message.edit_text(tr(
        f"📊 **Estatísticas da Conta**\n\n"
        f"├ 💬 **Privados:** `{privados}`\n"
        f"├ 🤖 **Bots:** `{bots}`\n"
        f"├ 👥 **Grupos:** `{grupos + supergrupos}`\n"
        f"│   ├ Admin: `{admin_grupos}`\n"
        f"│   └ Criador: `{criador}`\n"
        f"├ 📢 **Canais:** `{canais}`\n"
        f"│   └ Admin: `{admin_canais}`\n"
        f"├ 📁 **Total de diálogos:** `{total}`\n"
        f"└ ⏱️ **Tempo:** `{elapsed:.1f}s`",

        f"📊 **Account Stats**\n\n"
        f"├ 💬 **Private:** `{privados}`\n"
        f"├ 🤖 **Bots:** `{bots}`\n"
        f"├ 👥 **Groups:** `{grupos + supergrupos}`\n"
        f"│   ├ Admin: `{admin_grupos}`\n"
        f"│   └ Creator: `{criador}`\n"
        f"├ 📢 **Channels:** `{canais}`\n"
        f"│   └ Admin: `{admin_canais}`\n"
        f"├ 📁 **Total dialogs:** `{total}`\n"
        f"└ ⏱️ **Time:** `{elapsed:.1f}s`",
    ), disable_web_page_preview=True)
