"""
plugins/system/system.py
Sistema e manutenção: versao, atualizar, reiniciar, desligar, logs,
sysinfo, ping, idioma.

Tudo roda dentro do próprio userbot — não existe processo separado nem
bot de painel. git, psutil e leitura de arquivo bloqueiam, então vão
todos pra thread via asyncio.to_thread.
"""
import asyncio
import logging
import os
import subprocess
import time

logger = logging.getLogger("AxonBot.system")

from utils.commands import cmd
from utils.helpers import (
    DEL_LONGO,
    DEL_PADRAO,
    DEL_RAPIDO,
    deletar_depois,
    reiniciar_processo,
    salvar,
)
from utils.i18n import get_lang, set_lang, tr

_LOG = "userbot.log"


def _git_sync(*args, timeout: int = 30) -> tuple[int, str, str]:
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


async def _git(*args, timeout: int = 30) -> tuple[int, str, str]:
    """Wrapper de git fora do event loop. Retorna (codigo, stdout, stderr)."""
    return await asyncio.to_thread(_git_sync, *args, timeout=timeout)


async def _e_repositorio_git() -> bool:
    cod, _, _ = await _git("rev-parse", "--is-inside-work-tree", timeout=5)
    return cod == 0


async def _branch(client) -> str:
    """Branch de atualização: a definida no boot, ou a atual do repositório."""
    if branch := getattr(client, "UPDATE_BRANCH", None):
        return branch
    _, atual, _ = await _git("rev-parse", "--abbrev-ref", "HEAD", timeout=5)
    return atual or "main"


@cmd("versao")
async def cmd_versao(client, message):
    """Versão local, remota e último commit do repositório."""
    deletar_depois(message, DEL_PADRAO)
    p = getattr(client, "PREFIXO", ",")
    versao_local = getattr(client, "VERSAO", "?")

    if not await _e_repositorio_git():
        return await message.edit_text(tr(
            f"📦 **AxonBot** (`{versao_local}`)\n"
            f"⚠️ Esta pasta não é um repositório Git — atualização automática desativada.",
            f"📦 **AxonBot** (`{versao_local}`)\n"
            f"⚠️ This folder is not a Git repository — auto-update disabled.",
        ))

    await message.edit_text(tr("🔍 **Consultando o GitHub...**", "🔍 **Querying GitHub...**"))
    branch = await _branch(client)
    await _git("fetch", "origin", branch, timeout=20)

    _, hash_local, _  = await _git("rev-parse", "--short", "HEAD")
    _, hash_remoto, _ = await _git("rev-parse", "--short", f"origin/{branch}")
    _, msg_local, _   = await _git("log", "-1", "--pretty=%s")
    _, autor_local, _ = await _git("log", "-1", "--pretty=%an")
    _, atras, _       = await _git("rev-list", "--count", f"HEAD..origin/{branch}")
    atras = atras or "0"

    if atras == "0":
        status = tr("✅ atualizado", "✅ up to date")
        dica   = ""
    else:
        status = tr(f"🔄 {atras} commit(s) atrás", f"🔄 {atras} commit(s) behind")
        dica   = tr(f"\n\n💡 Use `{p}atualizar` para atualizar.", f"\n\n💡 Use `{p}update` to update.")

    await message.edit_text(tr(
        f"📦 **AxonBot**\n\n"
        f"🌿 Branch: `{branch}`\n"
        f"🔢 Local:  `{hash_local or 'n/a'}`\n"
        f"🌐 Remoto: `{hash_remoto or 'n/a'}`\n"
        f"📈 Status: {status}\n\n"
        f"💬 Último commit: `{msg_local or 'n/a'}`\n"
        f"👤 Autor: `{autor_local or 'n/a'}`{dica}",

        f"📦 **AxonBot**\n\n"
        f"🌿 Branch: `{branch}`\n"
        f"🔢 Local:  `{hash_local or 'n/a'}`\n"
        f"🌐 Remote: `{hash_remoto or 'n/a'}`\n"
        f"📈 Status: {status}\n\n"
        f"💬 Last commit: `{msg_local or 'n/a'}`\n"
        f"👤 Author: `{autor_local or 'n/a'}`{dica}",
    ))


@cmd("atualizar")
async def cmd_atualizar(client, message):
    """Baixa a última versão do GitHub e reinicia."""
    if not await _e_repositorio_git():
        return await message.edit_text(tr(
            "⚠️ Esta pasta não é um repositório Git — não dá pra atualizar sozinho.",
            "⚠️ This folder is not a Git repository — cannot self-update.",
        ))

    await message.edit_text(tr("🔍 **Procurando atualizações...**", "🔍 **Checking for updates...**"))
    branch = await _branch(client)

    cod, _, err = await _git("fetch", "origin", branch, timeout=60)
    if cod != 0:
        return await message.edit_text(tr(
            f"❌ **Falha ao consultar o GitHub**\n`{err[:300]}`",
            f"❌ **Failed to reach GitHub**\n`{err[:300]}`",
        ))

    _, atras, _ = await _git("rev-list", "--count", f"HEAD..origin/{branch}")
    if (atras or "0") == "0":
        return await message.edit_text(tr(
            "✅ **Já está na última versão.**", "✅ **Already up to date.**"
        ))

    _, novo_hash, _ = await _git("rev-parse", "--short", f"origin/{branch}")
    _, novo_msg, _  = await _git("log", "-1", "--pretty=%s", f"origin/{branch}")

    await message.edit_text(tr(
        f"⬇️ **Baixando {atras} commit(s)...**", f"⬇️ **Pulling {atras} commit(s)...**"
    ))

    # reset --hard descarta modificações locais: é o preço de ter update por
    # um comando só. Quem edita o próprio fork deve usar git pull na mão.
    cod, _, err = await _git("reset", "--hard", f"origin/{branch}", timeout=60)
    if cod != 0:
        return await message.edit_text(tr(
            f"❌ **Falha ao aplicar a atualização**\n`{err[:300]}`",
            f"❌ **Failed to apply the update**\n`{err[:300]}`",
        ))

    salvar(getattr(client, "UPDATE_FLAG", ".update_pending.json"),
           {"commit": novo_hash, "mensagem": novo_msg})

    await message.edit_text(tr(
        f"✅ **Atualizado para `{novo_hash}`**\n└ {novo_msg}\n\n🔄 Reiniciando...",
        f"✅ **Updated to `{novo_hash}`**\n└ {novo_msg}\n\n🔄 Restarting...",
    ))
    await asyncio.sleep(1)
    reiniciar_processo()


@cmd("reiniciar")
async def cmd_reiniciar(client, message):
    """Reinicia o userbot."""
    await message.edit_text(tr("🔄 **Reiniciando...**", "🔄 **Restarting...**"))
    await asyncio.sleep(1)
    reiniciar_processo()


@cmd("desligar")
async def cmd_desligar(client, message):
    """Desliga o userbot (só volta rodando main.py de novo)."""
    await message.edit_text(tr(
        "🛑 **Desligando.** Rode `python main.py` pra voltar.",
        "🛑 **Shutting down.** Run `python main.py` to come back.",
    ))
    await asyncio.sleep(1)
    os._exit(0)


def _ler_log(n: int) -> str:
    try:
        with open(_LOG, "r", encoding="utf-8", errors="replace") as f:
            linhas = f.readlines()
    except FileNotFoundError:
        return ""
    return "".join(linhas[-n:]).strip()


@cmd("logs")
async def cmd_logs(client, message):
    """Mostra o fim do userbot.log. ,logs [n] escolhe quantas linhas."""
    p      = getattr(client, "PREFIXO", ",")
    partes = message.text.split()
    try:
        n = max(1, min(int(partes[1]), 500)) if len(partes) > 1 else 30
    except ValueError:
        return await message.edit_text(f"⚠️ `{p}logs [n]`")

    texto = await asyncio.to_thread(_ler_log, n)
    if not texto:
        return await message.edit_text(tr(
            f"📄 `{_LOG}` está vazio ou não existe ainda.",
            f"📄 `{_LOG}` is empty or does not exist yet.",
        ))

    # Mensagem do Telegram estoura em 4096 caracteres — acima disso vai como arquivo.
    if len(texto) > 3800:
        await message.delete()
        caminho = "logs_recentes.txt"
        try:
            await asyncio.to_thread(
                lambda: open(caminho, "w", encoding="utf-8").write(texto)
            )
            await client.send_document(
                message.chat.id, caminho,
                caption=tr(f"📄 Últimas {n} linhas", f"📄 Last {n} lines"),
            )
        finally:
            if os.path.exists(caminho):
                os.remove(caminho)
        return

    await message.edit_text(tr(
        f"📄 **Últimas {n} linhas**\n```\n{texto}\n```",
        f"📄 **Last {n} lines**\n```\n{texto}\n```",
    ))
    deletar_depois(message, DEL_LONGO)


def _formatar_sysinfo() -> str:
    import humanize

    from utils.sysinfo import collect

    i    = collect()
    ram  = i["ram"]
    swap = i["swap"]
    net  = i["net"]
    freq = i["cpu_freq"]

    up = int(time.time() - i["boot_time"])
    d, r = divmod(up, 86400)
    h, r = divmod(r, 3600)
    m, _ = divmod(r, 60)
    uptime = f"{d}d {h}h {m}min" if d else (f"{h}h {m}min" if h else f"{m}min")

    ghz    = f" @ {freq.current / 1000:.2f}GHz" if freq and freq.current else ""
    discos = "\n".join(f"     {linha}" for linha in i["discos"])

    return (
        f"💻 **{i['os_info']}**\n"
        f"├ 🧠 CPU:    `{i['cpu_nome']}`\n"
        f"│         {i['cpu_cores']}C/{i['cpu_threads']}T{ghz} · {i['cpu_uso']}% em uso\n"
        f"├ 🎮 GPU:    `{i['gpu_info']}`\n"
        f"├ 🧬 Kernel: `{i['kernel']}`\n"
        f"├ 💾 RAM:    {humanize.naturalsize(ram.used)} / {humanize.naturalsize(ram.total)} ({ram.percent}%)\n"
        f"├ 🔀 Swap:   {humanize.naturalsize(swap.used)} / {humanize.naturalsize(swap.total)}\n"
        f"├ 📀 Disco:\n{discos}\n"
        f"├ 🌐 Rede:   ↓ {humanize.naturalsize(net.bytes_recv)} · ↑ {humanize.naturalsize(net.bytes_sent)}\n"
        f"└ ⏱️ Ligado há `{uptime}`"
    )


@cmd("sysinfo")
async def cmd_sysinfo(client, message):
    """Informações da máquina: CPU, GPU, RAM, disco e rede."""
    await message.edit_text(tr("🔍 **Lendo o sistema...**", "🔍 **Reading system...**"))
    try:
        texto = await asyncio.to_thread(_formatar_sysinfo)
    except Exception as e:
        logger.warning(f"[system.py] falha no sysinfo: {e}")
        return await message.edit_text(tr(
            f"❌ Não consegui ler as informações do sistema: `{e}`",
            f"❌ Could not read system information: `{e}`",
        ))
    await message.edit_text(texto)
    deletar_depois(message, DEL_LONGO)


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
    if len(partes) < 2 or partes[1].lower() not in ("pt", "en"):
        atual = get_lang().upper()
        return await message.edit_text(tr(
            f"⚠️ Use: `{p}idioma [pt/en]`\n🌐 Idioma atual: `{atual}`",
            f"⚠️ Use: `{p}lang [pt/en]`\n🌐 Current language: `{atual}`",
        ))

    novo = partes[1].lower()
    client.LANG = novo
    set_lang(novo)
    cfg = getattr(client, "config", {})
    cfg["LANGUAGE"] = novo
    salvar("config.json", cfg)

    await message.edit_text(tr(
        "✅ **Idioma alterado para Português!**", "✅ **Language changed to English!**"
    ))
