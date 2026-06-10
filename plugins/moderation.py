"""
plugins/moderation.py
Comandos de moderação: ban, unban, mute, unmute, del, purge, admins, zombies, gban, fban, addfed, delfed, feds
"""
import asyncio
from datetime import datetime

from pyrogram import filters, enums, Client
from pyrogram.types import ChatPermissions
from pyrogram.errors import FloodWait
from utils.helpers import cmd_filter, prefixo, resolver_alvo, auditoria, verificar_admin, carregar, salvar, deletar_depois, tr
from utils.i18n import tr_log


@Client.on_message(cmd_filter("ban") & filters.me)
async def cmd_ban(client, message):
    """Bane um usuário do grupo."""
    deletar_depois(message, 20)
    user, motivo, msg_orig = await resolver_alvo(client, message)
    if not user:
        return await message.edit_text(tr(
            f"⚠️ Use: responda à mensagem, ou `{prefixo(client)}ban @user`",
            f"⚠️ Use: reply to a message, or `{prefixo(client)}ban @user`"
        ))
    try:
        await client.ban_chat_member(message.chat.id, user.id)
        txt = tr(f"🔨 **Banido:** {user.first_name} (`{user.id}`)", f"🔨 **Banned:** {user.first_name} (`{user.id}`)")
        if motivo:
            txt += tr(f"\n📝 Motivo: `{motivo}`", f"\n📝 Reason: `{motivo}`")
        await message.edit_text(txt)
        await auditoria(client, "BAN", user, message.chat, motivo=motivo, msg_orig=msg_orig)
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@Client.on_message(cmd_filter("unban") & filters.me)
async def cmd_unban(client, message):
    """Desbane um usuário do grupo."""
    deletar_depois(message, 20)
    user, _, _ = await resolver_alvo(client, message)
    if not user:
        return await message.edit_text(tr(
            f"⚠️ Use: responda à mensagem, ou `{prefixo(client)}unban @user`",
            f"⚠️ Use: reply to a message, or `{prefixo(client)}unban @user`"
        ))
    try:
        await client.unban_chat_member(message.chat.id, user.id)
        await message.edit_text(tr(f"✅ **Desbanido:** {user.first_name} (`{user.id}`)", f"✅ **Unbanned:** {user.first_name} (`{user.id}`)"))
        await auditoria(client, "UNBAN", user, message.chat)
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@Client.on_message(cmd_filter("mute") & filters.me)
async def cmd_mute(client, message):
    """Silencia um usuário no grupo."""
    deletar_depois(message, 20)
    user, motivo, msg_orig = await resolver_alvo(client, message)
    if not user:
        return await message.edit_text(tr(
            f"⚠️ Use: responda à mensagem, ou `{prefixo(client)}mute @user`",
            f"⚠️ Use: reply to a message, or `{prefixo(client)}mute @user`"
        ))
    try:
        await client.restrict_chat_member(
            message.chat.id, user.id,
            ChatPermissions(can_send_messages=False)
        )
        txt = tr(f"🔇 **Silenciado:** {user.first_name} (`{user.id}`)", f"🔇 **Muted:** {user.first_name} (`{user.id}`)")
        if motivo:
            txt += tr(f"\n📝 Motivo: `{motivo}`", f"\n📝 Reason: `{motivo}`")
        await message.edit_text(txt)
        await auditoria(client, "MUTE", user, message.chat, motivo=motivo, msg_orig=msg_orig)
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@Client.on_message(cmd_filter("unmute") & filters.me)
async def cmd_unmute(client, message):
    """Remove o silêncio de um usuário."""
    deletar_depois(message, 20)
    user, _, _ = await resolver_alvo(client, message)
    if not user:
        return await message.edit_text(tr(
            f"⚠️ Use: responda à mensagem, ou `{prefixo(client)}unmute @user`",
            f"⚠️ Use: reply to a message, or `{prefixo(client)}unmute @user`"
        ))
    try:
        await client.restrict_chat_member(
            message.chat.id, user.id,
            ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True
            )
        )
        await message.edit_text(tr(f"🔊 **Desmutado:** {user.first_name} (`{user.id}`)", f"🔊 **Unmuted:** {user.first_name} (`{user.id}`)"))
        await auditoria(client, "UNMUTE", user, message.chat)
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@Client.on_message(cmd_filter("del") & filters.me)
async def cmd_del(client, message):
    """Apaga a mensagem respondida (e o comando)."""
    if not message.reply_to_message:
        return await message.delete()
    try:
        await message.reply_to_message.delete()
        await message.delete()
    except Exception:
        pass


@Client.on_message(cmd_filter("purge") & filters.me)
async def cmd_purge(client, message):
    """Apaga todas as mensagens desde a mensagem respondida até o comando."""
    if not message.reply_to_message:
        return await message.edit_text(tr("⚠️ Responda à mensagem inicial para apagar a partir dela.", "⚠️ Reply to the starting message to purge from it."))
    chat_id       = message.chat.id
    msg_id_inicio = message.reply_to_message.id
    msg_id_fim    = message.id
    try:
        # Coleta IDs reais via get_messages (não assume sequencialidade)
        ids: list[int] = []
        async for msg in client.get_chat_history(chat_id, limit=msg_id_fim - msg_id_inicio + 200):
            if msg_id_inicio <= msg.id <= msg_id_fim:
                ids.append(msg.id)
            if msg.id < msg_id_inicio:
                break
        if not ids:
            return await message.edit_text(tr("⚠️ Nenhuma mensagem encontrada no intervalo.", "⚠️ No messages found in range."))
        for i in range(0, len(ids), 100):
            await client.delete_messages(chat_id, ids[i:i + 100])
        aviso = await client.send_message(chat_id, tr(f"🧹 **Purge:** {len(ids)} mensagens apagadas.", f"🧹 **Purge:** {len(ids)} messages deleted."))
        await asyncio.sleep(3)
        await aviso.delete()
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@Client.on_message(cmd_filter("admins") & filters.me)
async def cmd_admins(client, message):
    """Lista todos os administradores do grupo."""
    deletar_depois(message, 45)
    await message.edit_text(tr("👮 **Listando administradores...**", "👮 **Listing administrators...**"))
    try:
        admins = []
        async for m in client.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            cargo    = "👑" if m.status == enums.ChatMemberStatus.OWNER else "🛡️"
            nome     = m.user.first_name or "?"
            uid      = m.user.id
            username = f" @{m.user.username}" if m.user.username else ""
            admins.append(f"{cargo} **{nome}**{username} (`{uid}`)")
        header = tr(
            f"👮 **Admins de {message.chat.title}** ({len(admins)}):\n\n",
            f"👮 **Admins of {message.chat.title}** ({len(admins)}):\n\n",
        )
        await message.edit_text(header + "\n".join(admins))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@Client.on_message(cmd_filter("zombies") & filters.me)
async def cmd_zombies(client, message):
    """Detecta e remove contas deletadas do grupo (pede confirmação)."""
    p   = prefixo(client)
    msg = await message.edit_text(tr(
        "🔍 **Varrendo membros do grupo...**",
        "🔍 **Scanning group members...**",
    ))
    if not await verificar_admin(client, message.chat.id):
        return await msg.edit_text(tr(
            "⚠️ Você não é admin neste grupo.",
            "⚠️ You are not an admin in this group.",
        ))

    zumbis: list[int] = []
    total = 0
    try:
        async for m in client.get_chat_members(message.chat.id):
            total += 1
            if m.user.is_deleted:
                zumbis.append(m.user.id)
    except Exception as e:
        return await msg.edit_text(tr(f"❌ Erro na varredura: `{e}`", f"❌ Scan error: `{e}`"))

    if not zumbis:
        await msg.edit_text(tr(
            f"✅ **Nenhuma conta deletada encontrada.**\n└ 👥 Membros verificados: `{total}`",
            f"✅ **No deleted accounts found.**\n└ 👥 Members scanned: `{total}`",
        ))
        return deletar_depois(msg, 20)

    await msg.edit_text(tr(
        f"🧟 **{len(zumbis)} conta(s) deletada(s) encontrada(s)**\n"
        f"└ 👥 Membros verificados: `{total}`\n\n"
        f"Responda **sim** para remover ou **não** para cancelar.",
        f"🧟 **{len(zumbis)} deleted account(s) found**\n"
        f"└ 👥 Members scanned: `{total}`\n\n"
        f"Reply **yes** to remove or **no** to cancel.",
    ))

    from utils.helpers import listen
    try:
        resp = await listen(client, message.chat.id, timeout=30)
        confirmado = resp.text.strip().lower() in ("sim", "yes", "s", "y")
    except asyncio.TimeoutError:
        await msg.edit_text(tr(
            "⏰ **Tempo esgotado.** Operação cancelada.",
            "⏰ **Timed out.** Operation cancelled.",
        ))
        return deletar_depois(msg, 15)

    try:
        await resp.delete()
    except Exception:
        pass

    if not confirmado:
        await msg.edit_text(tr("🚫 **Operação cancelada.**", "🚫 **Operation cancelled.**"))
        return deletar_depois(msg, 10)

    await msg.edit_text(tr(
        f"🧟 **Removendo {len(zumbis)} zumbi(s)...**",
        f"🧟 **Removing {len(zumbis)} zombie(s)...**",
    ))

    removidos = 0
    for uid in zumbis:
        try:
            await client.ban_chat_member(message.chat.id, uid)
            await asyncio.sleep(0.3)
            await client.unban_chat_member(message.chat.id, uid)
            removidos += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass

    await msg.edit_text(tr(
        f"🧟 **Limpeza concluída!**\n\n"
        f"├ 👥 Membros verificados: `{total}`\n"
        f"└ 🗑️ Zumbis removidos: `{removidos}`",
        f"🧟 **Cleanup complete!**\n\n"
        f"├ 👥 Members scanned: `{total}`\n"
        f"└ 🗑️ Zombies removed: `{removidos}`",
    ))
    deletar_depois(msg, 30)


@Client.on_message(cmd_filter("gban") & filters.me)
async def cmd_gban(client, message):
    """Bane um usuário em todos os grupos onde o bot é admin."""
    user, motivo, msg_orig = await resolver_alvo(client, message)
    if not user:
        return await message.edit_text(tr(
            f"⚠️ Use: responda à mensagem, ou `{prefixo(client)}gban @user`",
            f"⚠️ Use: reply to a message, or `{prefixo(client)}gban @user`"
        ))
    aviso = await message.edit_text(tr(f"🌍 **GBAN em andamento:** {user.first_name} (`{user.id}`)", f"🌍 **GBAN in progress:** {user.first_name} (`{user.id}`)"))
    sucesso = 0
    async for d in client.get_dialogs():
        if d.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            if await verificar_admin(client, d.chat.id):
                try:
                    await client.ban_chat_member(d.chat.id, user.id)
                    sucesso += 1
                    if sucesso % 5 == 0:
                        await asyncio.sleep(1)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception:
                    pass
    await auditoria(client, "GBAN", user, message.chat, motivo or "Banimento Global", msg_orig)
    await aviso.edit_text(tr(
        f"☢️ **GBAN concluído!**\n👤 Alvo: {user.first_name} (`{user.id}`)\n🔨 Banido em `{sucesso}` grupos.",
        f"☢️ **GBAN completed!**\n👤 Target: {user.first_name} (`{user.id}`)\n🔨 Banned in `{sucesso}` groups."
    ))
    deletar_depois(aviso, 30)


@Client.on_message(cmd_filter("fban") & filters.me)
async def cmd_fban(client, message):
    """Bane um usuário em todos os grupos da federação."""
    user_obj, motivo, msg_orig = await resolver_alvo(client, message)
    if not user_obj:
        return await message.edit_text(tr(
            f"⚠️ Use: responda à mensagem, ou `{prefixo(client)}fban @user [motivo]`",
            f"⚠️ Use: reply to a message, or `{prefixo(client)}fban @user [reason]`"
        ))
    user_id = user_obj.id
    if not motivo:
        motivo = "Spam / Violação de regras"
    feds = carregar("feds.json", [])
    if not feds:
        return await message.edit_text(tr("⚠️ Nenhuma federação cadastrada. Use `,addfed` em grupos administrativos.", "⚠️ No federations registered. Use `,addfed` in admin groups."))
    await message.edit_text(tr(f"📡 **Executando FBAN em `{user_id}`...**", f"📡 **Executing FBAN on `{user_id}`...**"))
    sucesso = 0
    for fid in feds:
        try:
            await client.send_message(fid, f"/fban {user_id} {motivo}")
            sucesso += 1
            await asyncio.sleep(0.5)
        except:
            pass
    await message.edit_text(tr(
        f"☢️ **FBAN concluído.**\n👤 Alvo: `{user_id}`\n📝 Motivo: `{motivo}`\n📡 Federações: `{sucesso}`",
        f"☢️ **FBAN completed.**\n👤 Target: `{user_id}`\n📝 Reason: `{motivo}`\n📡 Federations: `{sucesso}`"
    ))
    if user_obj:
        await auditoria(client, "FBAN", user_obj, message.chat, motivo, msg_orig)
    deletar_depois(message, 30)


@Client.on_message(cmd_filter("addfed") & filters.me)
async def cmd_addfed(client, message):
    """Adiciona o grupo atual à federação."""
    deletar_depois(message, 20)
    feds = carregar("feds.json", [])
    if message.chat.id in feds:
        return await message.edit_text(tr("⚠️ Este grupo já está cadastrado.", "⚠️ This group is already registered."))
    feds.append(message.chat.id)
    salvar("feds.json", feds)
    await message.edit_text(tr(f"✅ **Grupo adicionado à federação.**\n📍 ID: `{message.chat.id}`", f"✅ **Group added to federation.**\n📍 ID: `{message.chat.id}`"))


@Client.on_message(cmd_filter("delfed") & filters.me)
async def cmd_delfed(client, message):
    """Remove o grupo atual da federação."""
    deletar_depois(message, 20)
    feds = carregar("feds.json", [])
    if message.chat.id not in feds:
        return await message.edit_text(tr("⚠️ Este grupo não está cadastrado.", "⚠️ This group is not registered."))
    feds.remove(message.chat.id)
    salvar("feds.json", feds)
    await message.edit_text(tr("✅ **Grupo removido da federação.**", "✅ **Group removed from federation.**"))


@Client.on_message(cmd_filter("feds") & filters.me)
async def cmd_feds(client, message):
    """Lista todos os grupos da federação."""
    deletar_depois(message, 45)
    feds = carregar("feds.json", [])
    if not feds:
        return await message.edit_text(tr("⚠️ Nenhuma federação cadastrada.", "⚠️ No federations registered."))
    txt = tr(f"📡 **Federações ({len(feds)}):**\n\n", f"📡 **Federations ({len(feds)}):**\n\n")
    for fid in feds:
        try:
            chat = await client.get_chat(fid)
            txt += f"• **{chat.title}** (`{fid}`)\n"
        except Exception:
            txt += tr(f"• `{fid}` (inacessível)\n", f"• `{fid}` (inaccessible)\n")
    await message.edit_text(txt)


@Client.on_message(cmd_filter("fixar") & filters.me)
async def cmd_fixar(client, message):
    """Fixa a mensagem respondida no chat e registra no canal de logs."""
    if not message.reply_to_message:
        return await message.edit_text(tr(
            "⚠️ Responda à mensagem que deseja fixar.",
            "⚠️ Reply to the message you want to pin."
        ))

    alvo = message.reply_to_message
    chat_id = message.chat.id

    try:
        await client.pin_chat_message(chat_id, alvo.id, disable_notification=False)
    except Exception as e:
        return await message.edit_text(tr(f"❌ Não foi possível fixar:\n`{e}`", f"❌ Could not pin:\n`{e}`"))

    nome_chat = getattr(message.chat, "title", None) or tr("Conversa Privada", "Private Chat")
    autor = alvo.from_user
    autor_str = f"[{autor.first_name}](tg://user?id={autor.id})" if autor else tr("Desconhecido", "Unknown")

    confirmacao = tr(
        f"📌 **Mensagem fixada!**\n"
        f"├ 💬 Chat: `{nome_chat}`\n"
        f"└ 👤 Autor: {autor_str}",
        f"📌 **Message pinned!**\n"
        f"├ 💬 Chat: `{nome_chat}`\n"
        f"└ 👤 Author: {autor_str}"
    )
    await message.edit_text(confirmacao)

    ts = datetime.now().strftime("%d/%m/%Y %H:%M")

    cfg = getattr(client, "config", {})
    log_id = cfg.get("ID_CANAL_LOGS")
    if log_id:
        try:
            await client.send_message(log_id, tr_log(
                f"📌 **MENSAGEM FIXADA**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"├ 💬 **Chat:** {nome_chat} (`{chat_id}`)\n"
                f"├ 👤 **Autor:** {autor_str}\n"
                f"└ 🕐 `{ts}`",
                f"📌 **MESSAGE PINNED**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"├ 💬 **Chat:** {nome_chat} (`{chat_id}`)\n"
                f"├ 👤 **Author:** {autor_str}\n"
                f"└ 🕐 `{ts}`",
            ))
            await alvo.forward(log_id)
        except Exception:
            pass

    deletar_depois(message, 10)


@Client.on_message(cmd_filter("desafixar") & filters.me)
async def cmd_desafixar(client, message):
    """Desafixa a mensagem respondida (ou a última fixada) no chat."""
    chat_id = message.chat.id

    msg_id = message.reply_to_message.id if message.reply_to_message else None

    try:
        if msg_id:
            await client.unpin_chat_message(chat_id, msg_id)
        else:
            await client.unpin_chat_message(chat_id)
    except Exception as e:
        return await message.edit_text(tr(f"❌ Não foi possível desafixar:\n`{e}`", f"❌ Could not unpin:\n`{e}`"))

    await message.edit_text(tr("📌 **Mensagem desafixada.**", "📌 **Message unpinned.**"))
    deletar_depois(message, 8)
