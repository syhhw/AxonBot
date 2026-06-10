"""
plugins/system.py
Comandos de sistema: versao, atualizar, restart, ping, speed, sysinfo, processos
"""
import os
import sys
import time
import signal
import asyncio
import psutil
import humanize
import speedtest
import subprocess
import platform
import pyrogram
from datetime import datetime

from pyrogram import filters, Client
from utils.helpers import cmd_filter, salvar, deletar_depois, reiniciar_processo
from utils.i18n import tr, tr_log, set_lang, get_lang

_IS_ANDROID = os.path.exists("/system/build.prop") or "TERMUX_VERSION" in os.environ
_IS_WINDOWS = platform.system() == "Windows"
_IS_LINUX   = platform.system() == "Linux" and not _IS_ANDROID


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



@Client.on_message(cmd_filter("versao") & filters.me)
async def cmd_versao(client, message):
    """Versão local, remota e último commit do repositório."""
    deletar_depois(message, 30)
    versao_local = getattr(client, "VERSAO", "?")
    if not _e_repositorio_git():
        return await message.edit_text(tr(
            f"📦 **Userbot Pro v{versao_local}**\n⚠️ Pasta não é um repositório Git — atualização automática desativada.",
            f"📦 **Userbot Pro v{versao_local}**\n⚠️ Folder is not a Git repository — auto-update disabled."
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
        f"📦 **Userbot Pro v{versao_local}**\n\n🌿 Branch: `{branch}`\n🔢 Local:  `{hash_local or 'n/a'}`\n🌐 Remoto: `{hash_remoto or 'n/a'}`\n📈 Status: {status}\n\n💬 Último commit local: `{msg_local or 'n/a'}`\n👤 Autor: `{autor_local or 'n/a'}`",
        f"📦 **Userbot Pro v{versao_local}**\n\n🌿 Branch: `{branch}`\n🔢 Local:  `{hash_local or 'n/a'}`\n🌐 Remote: `{hash_remoto or 'n/a'}`\n📈 Status: {status}\n\n💬 Last local commit: `{msg_local or 'n/a'}`\n👤 Author: `{autor_local or 'n/a'}`"
    ))


@Client.on_message(cmd_filter("atualizar") & filters.me)
async def cmd_atualizar(client, message):
    """
    Auto-update via GitHub.
      ,atualizar           → atualiza a branch atual detectada automaticamente
      ,atualizar [branch]  → troca para a branch informada e atualiza
    """
    versao_local = getattr(client, "VERSAO", "?")
    update_flag  = getattr(client, "UPDATE_FLAG", ".update_pending.json")

    if not _e_repositorio_git():
        return await message.edit_text(tr(
            "❌ **Pasta não é um repositório Git.**",
            "❌ **Folder is not a Git repository.**"
        ))

    partes = message.text.split()
    # ignora "forcar" (compatibilidade), trata qualquer outro arg como nome de branch
    branch_alvo = partes[1] if len(partes) > 1 and partes[1] != "forcar" else None

    msg = await message.edit_text(tr("🔄 **Buscando atualizações no GitHub...**", "🔄 **Checking for updates on GitHub...**"))

    # Fetch de todas as refs remotas
    cod, _, err = _git("fetch", "--all", timeout=30)
    if cod != 0:
        return await msg.edit_text(tr(
            f"❌ **Falha no `git fetch`:**\n```\n{err[:300]}\n```",
            f"❌ **Failed `git fetch`:**\n```\n{err[:300]}\n```"
        ))

    # Branch atual
    _, branch_atual, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch_atual = branch_atual or "main"

    branch = branch_alvo or branch_atual

    # Verifica se a branch remota existe
    cod_rem, _, _ = _git("rev-parse", "--verify", f"origin/{branch}", timeout=5)
    if cod_rem != 0:
        return await msg.edit_text(tr(
            f"❌ Branch `{branch}` não encontrada no remote.",
            f"❌ Branch `{branch}` not found on remote."
        ))

    # Troca de branch se necessário
    if branch != branch_atual:
        await msg.edit_text(tr(
            f"🔀 **Trocando para branch `{branch}`...**",
            f"🔀 **Switching to branch `{branch}`...**"
        ))
        # Tenta checkout local; se não existir cria rastreando origin
        cod_co, _, err_co = _git("checkout", branch)
        if cod_co != 0:
            cod_co, _, err_co = _git("checkout", "-b", branch, f"origin/{branch}")
        if cod_co != 0:
            return await msg.edit_text(tr(
                f"❌ **Falha ao trocar de branch:**\n```\n{err_co[:300]}\n```",
                f"❌ **Failed to switch branch:**\n```\n{err_co[:300]}\n```"
            ))

    # Verifica quantos commits atrás
    _, atras, _ = _git("rev-list", "--count", f"HEAD..origin/{branch}")
    atras = atras or "0"
    if atras == "0" and branch == branch_atual:
        return await msg.edit_text(tr(
            f"✅ **Userbot já está na versão mais recente!**\n📦 v{versao_local} | branch `{branch}`",
            f"✅ **Userbot is already up to date!**\n📦 v{versao_local} | branch `{branch}`"
        ))

    _, diff_arquivos, _ = _git("diff", "--name-only", f"HEAD..origin/{branch}")
    arquivos = [a for a in diff_arquivos.splitlines() if a.strip()]
    requirements_mudou = any("requirements.txt" in a for a in arquivos)

    await msg.edit_text(tr(
        f"⬇️ **Aplicando atualização** ({len(arquivos)} arquivo(s))...\n🔀 `RESET HARD → origin/{branch}`",
        f"⬇️ **Applying update** ({len(arquivos)} file(s))...\n🔀 `RESET HARD → origin/{branch}`"
    ))

    cod, _, err = _git("reset", "--hard", f"origin/{branch}")
    if cod != 0:
        return await msg.edit_text(tr(
            f"❌ **Falha ao aplicar atualização:**\n```\n{err[:400]}\n```",
            f"❌ **Update failed:**\n```\n{err[:400]}\n```"
        ))

    _, commit_hash, _ = _git("rev-parse", "--short", "HEAD")
    _, commit_msg, _  = _git("log", "-1", "--pretty=%s")
    _, commit_autor, _ = _git("log", "-1", "--pretty=%an")

    if requirements_mudou:
        await msg.edit_text(tr("📦 **Atualizando dependências...**", "📦 **Updating dependencies...**"))
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
                capture_output=True, text=True, timeout=180
            )
        except Exception as e:
            await msg.edit_text(tr(
                f"⚠️ Update aplicado, mas falhou ao atualizar libs: `{e}`",
                f"⚠️ Update applied, but failed to update libs: `{e}`"
            ))
            await asyncio.sleep(2)

    try:
        salvar(update_flag, {
            "commit":    commit_hash,
            "mensagem":  commit_msg,
            "autor":     commit_autor,
            "arquivos":  arquivos,
            "timestamp": int(time.time()),
        })
    except Exception:
        pass

    await msg.edit_text(tr("✅ **Atualização concluída! Reiniciando...**", "✅ **Update complete! Restarting...**"))
    await asyncio.sleep(2)
    reiniciar_processo()


@Client.on_message(cmd_filter("restart") & filters.me)
async def cmd_restart(client, message):
    """Reinicia o bot."""
    await message.edit_text(tr("🔄 **Reiniciando...**", "🔄 **Restarting...**"))
    cfg    = getattr(client, "config", {})
    log_id = cfg.get("ID_CANAL_LOGS")
    if log_id:
        try:
            ts = datetime.now().strftime("%d/%m/%Y %H:%M")
            await client.send_message(log_id, tr_log(
                f"🔄 **USERBOT REINICIANDO**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"├ ⚙️ Reiniciado via comando\n"
                f"└ 🕐 `{ts}`",
                f"🔄 **USERBOT RESTARTING**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"├ ⚙️ Restarted via command\n"
                f"└ 🕐 `{ts}`",
            ))
        except Exception:
            pass
    reiniciar_processo()


@Client.on_message(cmd_filter("ping") & filters.me)
async def cmd_ping(client, message):
    """Mede a latência do bot."""
    deletar_depois(message, 15)
    inicio = time.time()
    await message.edit_text("⏱️")
    delta = (time.time() - inicio) * 1000
    await message.edit_text(tr(f"⚡ **Ping:** `{delta:.0f}ms`", f"⚡ **Latency:** `{delta:.0f}ms`"))


@Client.on_message(cmd_filter("idioma") & filters.me)
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


@Client.on_message(cmd_filter("speed") & filters.me)
async def cmd_speed(client, message):
    """Testa a velocidade da internet da VM."""
    await message.edit_text(tr("🚀 **Testando velocidade...**", "🚀 **Testing speed...**"))
    try:
        def run_speedtest():
            st = speedtest.Speedtest()
            st.get_best_server()
            st.download()
            st.upload()
            return st.results.dict()
            
        r = await asyncio.to_thread(run_speedtest)
        await message.edit_text(tr(
            f"🌐 **Network Speedtest**\n"
            f"├ ⬇️ **Download:** `{r['download']/10**6:.2f} Mbps`\n"
            f"├ ⬆️ **Upload:** `{r['upload']/10**6:.2f} Mbps`\n"
            f"├ 📶 **Ping:** `{r['ping']:.1f} ms`\n"
            f"└ 🏢 **Servidor:** `{r['server']['name']}`",
            f"🌐 **Network Speedtest**\n"
            f"├ ⬇️ **Download:** `{r['download']/10**6:.2f} Mbps`\n"
            f"├ ⬆️ **Upload:** `{r['upload']/10**6:.2f} Mbps`\n"
            f"├ 📶 **Ping:** `{r['ping']:.1f} ms`\n"
            f"└ 🏢 **Server:** `{r['server']['name']}`"
        ))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))
    deletar_depois(message, 30)


def _get_cpu_name() -> str:
    try:
        if _IS_WINDOWS:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return name.strip()
    except Exception:
        pass
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line or "Hardware" in line:
                    return line.split(":")[1].strip()
    except Exception:
        pass
    return platform.processor() or "Unknown"


def _get_gpu_info() -> str:
    try:
        if _IS_WINDOWS:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name + '||' + $_.DriverVersion }"],
                capture_output=True, text=True, timeout=8
            )
            gpus = []
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                if "||" in line:
                    name, driver = line.split("||", 1)
                    name, driver = name.strip(), driver.strip()
                    gpus.append(f"{name} (driver {driver})" if driver else name)
                else:
                    gpus.append(line)
            return " | ".join(gpus) if gpus else "N/A"

        if _IS_ANDROID:
            # Adreno (Qualcomm)
            kgsl = "/sys/class/kgsl/kgsl-3d0/gpu_model"
            if os.path.exists(kgsl):
                with open(kgsl) as f:
                    return f.read().strip()
            # Fallback: getprop
            r = subprocess.run(["getprop", "ro.hardware.egl"], capture_output=True, text=True, timeout=3)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
            r2 = subprocess.run(["getprop", "ro.board.platform"], capture_output=True, text=True, timeout=3)
            if r2.returncode == 0 and r2.stdout.strip():
                return r2.stdout.strip()
            return "N/A"

        # Linux desktop
        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
        gpus = [l.split(":")[-1].strip() for l in result.stdout.splitlines() if "VGA" in l or "3D" in l]
        return " | ".join(gpus) if gpus else "N/A"
    except Exception:
        return "N/A"


def _get_disk_info() -> list[str]:
    ssd_drives: set[str] = set()
    try:
        if _IS_WINDOWS:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-PhysicalDisk | ForEach-Object { $_.DeviceId + '||' + $_.MediaType }"],
                capture_output=True, text=True, timeout=8
            )
            for line in result.stdout.strip().splitlines():
                if "||" in line:
                    dev_id, media = line.split("||", 1)
                    if "SSD" in media or "Solid" in media:
                        ssd_drives.add(dev_id.strip())
    except Exception:
        pass

    lines = []
    try:
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                tipo = _disk_type(part.device, ssd_drives)
                lines.append(
                    f"{part.device} [{tipo}] {humanize.naturalsize(usage.used)} / "
                    f"{humanize.naturalsize(usage.total)} ({usage.percent}%)"
                )
            except Exception:
                continue
    except Exception:
        pass
    return lines or ["N/A"]


def _disk_type(device: str, ssd_set: set) -> str:
    if _IS_ANDROID:
        return "Flash"
    try:
        if _IS_LINUX:
            name = os.path.basename(device).rstrip("0123456789")
            rota_path = f"/sys/block/{name}/queue/rotational"
            if os.path.exists(rota_path):
                with open(rota_path) as f:
                    return "SSD" if f.read().strip() == "0" else "HDD"
        elif _IS_WINDOWS:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-Partition | Where-Object {{ $_.DriveLetter -eq '{device[0]}' }} | "
                 f"Get-Disk | Select-Object -ExpandProperty Number"],
                capture_output=True, text=True, timeout=6
            )
            disk_num = result.stdout.strip()
            if disk_num in ssd_set:
                return "SSD"
    except Exception:
        pass
    return "HDD"


@Client.on_message(cmd_filter("sysinfo") & filters.me)
async def cmd_sysinfo(client, message):
    """Informações completas do sistema (estilo neofetch)."""
    deletar_depois(message, 90)
    await message.edit_text(tr("💻 **Coletando informações do sistema...**", "💻 **Collecting system info...**"))

    def coletar():
        cpu_nome    = _get_cpu_name()
        cpu_cores   = psutil.cpu_count(logical=False)
        cpu_threads = psutil.cpu_count(logical=True)
        cpu_freq    = psutil.cpu_freq()
        cpu_uso     = psutil.cpu_percent(interval=0.5)
        gpu_info    = _get_gpu_info()
        ram         = psutil.virtual_memory()
        discos      = _get_disk_info()
        net         = psutil.net_io_counters()
        kernel      = platform.release()
        return cpu_nome, cpu_cores, cpu_threads, cpu_freq, cpu_uso, gpu_info, ram, discos, net, kernel

    (cpu_nome, cpu_cores, cpu_threads, cpu_freq, cpu_uso,
     gpu_info, ram, discos, net, kernel) = await asyncio.to_thread(coletar)

    inicio     = getattr(client, "tempo_inicio", time.time())
    uptime_bot = humanize.precisedelta(time.time() - inicio, minimum_unit="seconds")
    uptime_os  = humanize.precisedelta(time.time() - psutil.boot_time(), minimum_unit="minutes")

    os_info  = f"{platform.system()} {platform.release()} ({platform.machine()})"
    py_ver   = platform.python_version()
    pyro_ver = pyrogram.__version__
    versao   = getattr(client, "VERSAO", "1.0")

    freq_str  = f" @ {cpu_freq.current/1000:.1f} GHz" if cpu_freq else ""
    disco_str = "\n             ".join(discos)

    swap     = psutil.swap_memory()
    swap_str = (
        f"{humanize.naturalsize(swap.used)} / {humanize.naturalsize(swap.total)} ({swap.percent}%)"
        if swap.total > 0 else "N/A"
    )

    texto = (
        tr("💻 **Neofetch — Userbot Pro**\n\n", "💻 **Neofetch — Userbot Pro**\n\n") +
        f"```text\n"
        f"OS       : {os_info}\n"
        f"Kernel   : {kernel}\n"
        f"Uptime   : {uptime_os}\n"
        f"Bot Up   : {uptime_bot}\n"
        f"─────────────────────────────\n"
        f"CPU      : {cpu_nome}\n"
        f"Cores    : {cpu_cores}C / {cpu_threads}T{freq_str} @ {cpu_uso}%\n"
        f"GPU      : {gpu_info}\n"
        f"RAM      : {humanize.naturalsize(ram.used)} / {humanize.naturalsize(ram.total)} ({ram.percent}%)\n"
        f"Swap     : {swap_str}\n"
        f"─────────────────────────────\n"
        f"Disk     : {disco_str}\n"
        f"Net ↑    : {humanize.naturalsize(net.bytes_sent)}\n"
        f"Net ↓    : {humanize.naturalsize(net.bytes_recv)}\n"
        f"─────────────────────────────\n"
        f"Python   : {py_ver}\n"
        f"Pyrogram : {pyro_ver}\n"
        f"Userbot  : v{versao}\n"
        f"```"
    )
    await message.edit_text(texto)


@Client.on_message(cmd_filter("processos") & filters.me)
async def cmd_processos(client, message):
    """Lista os 5 processos que mais consomem CPU."""
    deletar_depois(message, 45)
    procs = sorted(
        psutil.process_iter(['pid', 'name', 'cpu_percent']),
        key=lambda x: x.info['cpu_percent'] or 0,
        reverse=True
    )[:5]
    txt = tr("🔍 **Top 5 Processos (CPU)**\n\n", "🔍 **Top 5 Processes (CPU)**\n\n")
    for p in procs:
        txt += f"• `{p.info['name']}` | PID `{p.info['pid']}` | CPU `{p.info['cpu_percent']}%`\n"
    await message.edit_text(txt)

@Client.on_message(cmd_filter("desligar") & filters.me)
async def cmd_desligar(client, message):
    """Encerra o bot remotamente."""
    await message.edit_text(tr("🛑 **Desligando o bot com segurança...**", "🛑 **Shutting down gracefully...**"))
    await asyncio.sleep(0.5)
    
    # Envia a mensagem de log manualmente antes de forçar a saída na raiz
    cfg = getattr(client, "config", {})
    log_id = cfg.get("ID_CANAL_LOGS")
    if log_id:
        try:
            ts = datetime.now().strftime("%d/%m/%Y %H:%M")
            await client.send_message(log_id, tr_log(
                f"🛑 **USERBOT OFFLINE**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"├ ⚙️ Encerrado remotamente via comando\n"
                f"└ 🕐 `{ts}`",
                f"🛑 **USERBOT OFFLINE**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"├ ⚙️ Terminated remotely via command\n"
                f"└ 🕐 `{ts}`",
            ))
        except Exception:
            pass

    os._exit(0)
