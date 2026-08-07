"""
utils/sysinfo.py
Coleta de informações de infraestrutura (CPU, GPU, disco, rede, speedtest,
processos). Não depende de pyrogram/telegram — usado pelo painel bot
(bot.py), que é o dono da gestão de VPS/infraestrutura do AxonBot.
"""
import os
import platform
import subprocess

import psutil

_IS_ANDROID = os.path.exists("/system/build.prop") or "TERMUX_VERSION" in os.environ
_IS_WINDOWS = platform.system() == "Windows"
_IS_LINUX   = platform.system() == "Linux" and not _IS_ANDROID


def get_cpu_name() -> str:
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


def get_gpu_info() -> str:
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
            kgsl = "/sys/class/kgsl/kgsl-3d0/gpu_model"
            if os.path.exists(kgsl):
                with open(kgsl) as f:
                    return f.read().strip()
            r = subprocess.run(["getprop", "ro.hardware.egl"], capture_output=True, text=True, timeout=3)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
            r2 = subprocess.run(["getprop", "ro.board.platform"], capture_output=True, text=True, timeout=3)
            if r2.returncode == 0 and r2.stdout.strip():
                return r2.stdout.strip()
            return "N/A"

        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5)
        gpus = [l.split(":")[-1].strip() for l in result.stdout.splitlines() if "VGA" in l or "3D" in l]
        return " | ".join(gpus) if gpus else "N/A"
    except Exception:
        return "N/A"


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


def get_disk_info() -> list[str]:
    import humanize

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


def collect() -> dict:
    """Snapshot completo (estilo neofetch): CPU, GPU, RAM, disco, rede, SO."""
    return {
        "cpu_nome":    get_cpu_name(),
        "cpu_cores":   psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "cpu_freq":    psutil.cpu_freq(),
        "cpu_uso":     psutil.cpu_percent(interval=0.5),
        "gpu_info":    get_gpu_info(),
        "ram":         psutil.virtual_memory(),
        "swap":        psutil.swap_memory(),
        "discos":      get_disk_info(),
        "net":         psutil.net_io_counters(),
        "kernel":      platform.release(),
        "os_info":     f"{platform.system()} {platform.release()} ({platform.machine()})",
        "boot_time":   psutil.boot_time(),
    }


def run_speedtest() -> dict:
    """Bloqueante — rodar via asyncio.to_thread()."""
    import speedtest
    st = speedtest.Speedtest()
    st.get_best_server()
    st.download()
    st.upload()
    return st.results.dict()


def top_processes(n: int = 5) -> list[dict]:
    coletados = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            coletados.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    coletados.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    return coletados[:n]
