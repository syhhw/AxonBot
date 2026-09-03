"""
plugins/locks.py
  ,travar [tipo]   — bloqueia uma permissão padrão do grupo
  ,destravar [tipo] — desbloqueia uma permissão padrão do grupo
  ,travas          — lista o status de todas as permissões

Créditos: ,lock/,unlock são comandos padrão de moderação em userbots
Telegram (Man-Userbot e forks).
"""
from pyrogram.types import ChatPermissions

from utils.commands import cmd
from utils.helpers import (
    DEL_LONGO,
    DEL_PADRAO,
    deletar_depois,
    prefixo,
    tr,
    verificar_admin,
)

# Mapa tipo → campo em ChatPermissions
_CAMPOS: dict[str, str] = {
    "msg":       "can_send_messages",
    "mensagem":  "can_send_messages",
    "media":     "can_send_media_messages",
    "midia":     "can_send_media_messages",
    "mídia":     "can_send_media_messages",
    "gif":       "can_send_other_messages",
    "sticker":   "can_send_other_messages",
    "figurinha": "can_send_other_messages",
    "outro":     "can_send_other_messages",
    "link":      "can_add_web_page_previews",
    "links":     "can_add_web_page_previews",
    "preview":   "can_add_web_page_previews",
    "poll":      "can_send_polls",
    "enquete":   "can_send_polls",
    "sondagem":  "can_send_polls",
    "info":      "can_change_info",
    "invite":    "can_invite_users",
    "convite":   "can_invite_users",
    "pin":       "can_pin_messages",
}

_EMOJI: dict[str, str] = {
    "can_send_messages":         "💬 Mensagens",
    "can_send_media_messages":   "🖼️ Mídia",
    "can_send_other_messages":   "🎭 GIFs/Stickers",
    "can_add_web_page_previews": "🔗 Links c/ preview",
    "can_send_polls":            "📊 Enquetes",
    "can_change_info":           "ℹ️ Mudar info",
    "can_invite_users":          "👥 Convidar",
    "can_pin_messages":          "📌 Fixar msgs",
}

_TIPOS_DISPONIVEIS = (
    "msg · media · gif · sticker · link · poll · info · invite · pin"
)


def _perms_to_dict(p: ChatPermissions | None) -> dict[str, bool]:
    defaults = {f: True for f in _EMOJI}
    if p is None:
        return defaults
    return {
        "can_send_messages":         bool(p.can_send_messages),
        "can_send_media_messages":   bool(p.can_send_media_messages),
        "can_send_other_messages":   bool(p.can_send_other_messages),
        "can_add_web_page_previews": bool(p.can_add_web_page_previews),
        "can_send_polls":            bool(p.can_send_polls),
        "can_change_info":           bool(p.can_change_info),
        "can_invite_users":          bool(p.can_invite_users),
        "can_pin_messages":          bool(p.can_pin_messages),
    }


async def _aplicar_permissao(client, chat_id: int, campo: str, valor: bool) -> None:
    chat  = await client.get_chat(chat_id)
    atual = _perms_to_dict(chat.permissions)
    atual[campo] = valor
    await client.set_chat_permissions(chat_id, ChatPermissions(**atual))


async def _apenas_grupos(message) -> bool:
    return message.chat.type.name in ("GROUP", "SUPERGROUP")


@cmd("travar")
async def cmd_travar(client, message):
    """Bloqueia uma permissão do grupo. ,travar msg|media|gif|link|poll|info|invite|pin"""
    p = prefixo(client)

    if not await _apenas_grupos(message):
        return await message.edit_text(tr(
            "❌ Este comando só funciona em grupos.",
            "❌ This command only works in groups.",
        ))

    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(
            f"⚠️ Use: `{p}travar [tipo]`\nTipos: `{_TIPOS_DISPONIVEIS}`",
            f"⚠️ Use: `{p}lock [type]`\nTypes: `{_TIPOS_DISPONIVEIS}`",
        ))

    tipo = partes[1].strip().lower()
    if tipo not in _CAMPOS:
        return await message.edit_text(tr(
            f"❌ Tipo `{tipo}` inválido.\nTipos válidos: `{_TIPOS_DISPONIVEIS}`",
            f"❌ Invalid type `{tipo}`.\nValid types: `{_TIPOS_DISPONIVEIS}`",
        ))

    if not await verificar_admin(client, message.chat.id):
        return await message.edit_text(tr(
            "❌ Preciso ser admin para alterar permissões.",
            "❌ I need admin rights to change permissions.",
        ))

    campo  = _CAMPOS[tipo]
    titulo = _EMOJI.get(campo, campo)
    try:
        await _aplicar_permissao(client, message.chat.id, campo, False)
        await message.edit_text(tr(
            f"🔒 **{titulo}** bloqueado para membros.",
            f"🔒 **{titulo}** locked for members.",
        ))
    except Exception as e:
        await message.edit_text(tr(
            f"❌ Erro ao travar: `{e}`",
            f"❌ Error locking: `{e}`",
        ))
    deletar_depois(message, DEL_PADRAO)


@cmd("destravar")
async def cmd_destravar(client, message):
    """Desbloqueia uma permissão do grupo. ,destravar msg|media|gif|link|poll|info|invite|pin"""
    p = prefixo(client)

    if not await _apenas_grupos(message):
        return await message.edit_text(tr(
            "❌ Este comando só funciona em grupos.",
            "❌ This command only works in groups.",
        ))

    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(
            f"⚠️ Use: `{p}destravar [tipo]`\nTipos: `{_TIPOS_DISPONIVEIS}`",
            f"⚠️ Use: `{p}unlock [type]`\nTypes: `{_TIPOS_DISPONIVEIS}`",
        ))

    tipo = partes[1].strip().lower()
    if tipo not in _CAMPOS:
        return await message.edit_text(tr(
            f"❌ Tipo `{tipo}` inválido.\nTipos válidos: `{_TIPOS_DISPONIVEIS}`",
            f"❌ Invalid type `{tipo}`.\nValid types: `{_TIPOS_DISPONIVEIS}`",
        ))

    if not await verificar_admin(client, message.chat.id):
        return await message.edit_text(tr(
            "❌ Preciso ser admin para alterar permissões.",
            "❌ I need admin rights to change permissions.",
        ))

    campo  = _CAMPOS[tipo]
    titulo = _EMOJI.get(campo, campo)
    try:
        await _aplicar_permissao(client, message.chat.id, campo, True)
        await message.edit_text(tr(
            f"🔓 **{titulo}** liberado para membros.",
            f"🔓 **{titulo}** unlocked for members.",
        ))
    except Exception as e:
        await message.edit_text(tr(
            f"❌ Erro ao destravar: `{e}`",
            f"❌ Error unlocking: `{e}`",
        ))
    deletar_depois(message, DEL_PADRAO)


@cmd("travas")
async def cmd_travas(client, message):
    """Lista o status atual de todas as permissões padrão do grupo."""
    if not await _apenas_grupos(message):
        return await message.edit_text(tr(
            "❌ Este comando só funciona em grupos.",
            "❌ This command only works in groups.",
        ))

    try:
        chat  = await client.get_chat(message.chat.id)
        atual = _perms_to_dict(chat.permissions)
    except Exception as e:
        return await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))

    linhas = []
    for campo, nome in _EMOJI.items():
        icone = "🔓" if atual.get(campo, True) else "🔒"
        status = tr("livre", "open") if atual.get(campo, True) else tr("bloqueado", "locked")
        linhas.append(f"{icone} **{nome}** — `{status}`")

    titulo = getattr(chat, "title", "Grupo")
    await message.edit_text(tr(
        f"📋 **Permissões de {titulo}**\n\n" + "\n".join(linhas),
        f"📋 **Permissions in {titulo}**\n\n" + "\n".join(linhas),
    ))
    deletar_depois(message, DEL_LONGO)
