"""
plugins/system.py
Comandos de sistema: versao, ping, idioma.

Gerenciamento de infraestrutura da VPS (update, restart, sysinfo, speed,
processos, shutdown) foi movido pro painel bot (bot.py, /painel) — ver
utils/sysinfo.py. O userbot foca só em rodar módulos e falar com a API
do Telegram, não em administrar a própria VPS.
"""
import logging
import time
import subprocess
logger = logging.getLogger("AxonBot.system")

from utils.helpers import salvar, deletar_depois, DEL_PADRAO, DEL_RAPIDO
from utils.commands import cmd
from utils.i18n import tr, set_lang, get_lang


def _git(*args, timeout=30):
    """Wrapper seguro para chamadas git. Retorna (codigo, stdout, stderr)."""
    try:
        proc = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def _e_repositorio_git():
    cod, _, _ = _git("rev-parse", "--is-inside-work-tree", timeout=5)
    return cod == 0


@cmd("versao")
async def cmd_versao(client, message):
    """Versão local, remota e último commit do repositório."""
    deletar_depois(message, DEL_PADRAO)
    versao_local = getattr(client, "VERSAO", "?")
    if not _e_repositorio_git():
        return await message.edit_text(tr(
            f"📦 **AxonBot** (`{versao_local}`)\n⚠️ Pasta não é um repositório Git — atualização automática desativada.",
            f"📦 **AxonBot** (`{versao_local}`)\n⚠️ Folder is not a Git repository — auto-update disabled."
        ))
    await message.edit_text(tr("🔍 **Consultando GitHub...**", "🔍 **Querying GitHub...**"))
    _git("fetch", "origin", timeout=20)
    _, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch or "main"
    _, hash_local, _ = _git("rev-parse", "--short", "HEAD")
    _, hash_remoto, _ = _git("rev-parse", "--short", f"origin/{branch}")
    _, msg_local, _ = _git("log", "-1", "--pretty=%s")
    _, autor_local, _ = _git("log", "-1", "--pretty=%an")
    _, atras, _ = _git("rev-list", "--count", f"HEAD..origin/{branch}")
    atras = atras or "0"
    status = tr("✅ atualizado", "✅ up to date") if atras == "0" else tr(f"🔄 {atras} commit(s) atrás", f"🔄 {atras} commit(s) behind")
    await message.edit_text(tr(
        f"📦 **AxonBot**\n\n🌿 Branch: `{branch}`\n🔢 Local:  `{hash_local or 'n/a'}`\n🌐 Remoto: `{hash_remoto or 'n/a'}`\n📈 Status: {status}\n\n💬 Último commit local: `{msg_local or 'n/a'}`\n👤 Autor: `{autor_local or 'n/a'}`\n\n💡 Use o /painel do bot pra atualizar/reiniciar.",
        f"📦 **AxonBot**\n\n🌿 Branch: `{branch}`\n🔢 Local:  `{hash_local or 'n/a'}`\n🌐 Remote: `{hash_remoto or 'n/a'}`\n📈 Status: {status}\n\n💬 Last local commit: `{msg_local or 'n/a'}`\n👤 Author: `{autor_local or 'n/a'}`\n\n💡 Use the bot's /painel to update/restart."
    ))


@cmd("ping")
async def cmd_ping(client, message):
    """Mede a latência do bot."""
    deletar_depois(message, DEL_RAPIDO)
    inicio = time.time()
    await message.edit_text("⏱️")
    delta = (time.time() - inicio) * 1000
    await message.edit_text(tr(f"⚡ **Ping:** `{delta:.0f}ms`", f"⚡ **Latency:** `{delta:.0f}ms`"))


@cmd("idioma")
async def cmd_idioma(client, message):
    """Altera o idioma do bot (pt/en)."""
    p = getattr(client, "PREFIXO", ",")
    partes = message.text.split()
    if len(partes) < 2 or partes[1].lower() not in ["pt", "en"]:
        atual = get_lang().upper()
        msg = tr(f"⚠️ Use: `{p}idioma [pt/en]`\n🌐 Idioma atual: `{atual}`", f"⚠️ Use: `{p}lang [pt/en]`\n🌐 Current lang: `{atual}`")
        return await message.edit_text(msg)

    novo = partes[1].lower()
    client.LANG = novo
    set_lang(novo)
    cfg = getattr(client, "config", {})
    cfg["LANGUAGE"] = novo
    salvar("config.json", cfg)

    resp = tr("✅ **Idioma alterado para Português!**", "✅ **Language changed to English!**")
    await message.edit_text(resp)
