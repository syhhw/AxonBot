"""
debug.py — Userbot Pro Admin Launcher
Sobe o main.py e exibe os logs em tempo real com cores e monitoramento de plugins.

Uso:
  python debug.py              → tudo
  python debug.py cmds         → só comandos usados
  python debug.py errors       → só erros e warnings
  python debug.py plugins      → só mudanças nos plugins
"""
import os
import sys
import time
import threading
import subprocess

# Force UTF-8 on Windows terminal so emojis don't crash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
from datetime import datetime
from pathlib import Path

# ── Cores ─────────────────────────────────────────────────────────────────────
V   = "\033[92m"
R   = "\033[91m"
AM  = "\033[93m"
AZ  = "\033[94m"
CI  = "\033[96m"
MA  = "\033[95m"
NE  = "\033[1m"
DIM = "\033[2m"
RS  = "\033[0m"

PLUGIN_DIR = "plugins"

_filter          = None
_proc            = None
_plugin_mtimes: dict = {}

# Loggers internos do Pyrogram — suprimidos por padrão (muito verbosos)
_SUPPRESSED_NAMES = {"pyrogram", "pyrogram.session", "pyrogram.connection", "root"}


def _colorize(line: str):
    line = line.rstrip("\n").rstrip("\r")
    if not line.strip():
        return

    # Formato: "HH:MM:SS | LEVEL | LoggerName | mensagem"
    parts = line.split(" | ", 3)

    if len(parts) == 4:
        ts_raw, level, name, msg = [p.strip() for p in parts]
    elif len(parts) == 3:
        ts_raw, level, msg = [p.strip() for p in parts]
        name = ""
    else:
        # Linha sem formato de log (output colorido do startup, separadores, etc.)
        print(line, flush=True)
        return

    # Suprime loggers internos do Python/Pyrogram exceto em modo errors
    if name in _SUPPRESSED_NAMES and _filter != "errors":
        return

    is_cmd    = "CMD:" in msg
    is_error  = level == "ERROR"   or "❌" in msg
    is_warn   = level == "WARNING" or "⚠"  in msg
    is_plugin = "Plugin carregado" in msg or "Falha ao carregar plugin" in msg
    is_online = any(x in msg for x in (
        "ONLINE", "INICIANDO", "✅ Google Drive", "✅ USERBOT", "USERBOT PRO",
        "Userbot encerrado", "Stop signal"
    ))

    # Filtros ativos
    if _filter == "cmds"    and not is_cmd:               return
    if _filter == "errors"  and not (is_error or is_warn): return
    if _filter == "plugins" and not is_plugin:             return

    ts       = f"{DIM}{ts_raw}{RS} "
    name_tag = f"{DIM}[{name}]{RS} " if name else ""

    if is_cmd:
        print(f"{ts}{name_tag}{CI}{NE}⌨  {RS}{CI}{msg}{RS}", flush=True)
    elif is_error:
        print(f"{ts}{name_tag}{R}{NE}✗  {RS}{R}{msg}{RS}", flush=True)
    elif is_warn:
        print(f"{ts}{name_tag}{AM}{NE}⚠  {RS}{AM}{msg}{RS}", flush=True)
    elif is_plugin:
        print(f"{ts}{name_tag}{MA}{NE}🔌 {RS}{MA}{msg}{RS}", flush=True)
    elif is_online:
        print(f"{ts}{name_tag}{V}{NE}●  {RS}{V}{msg}{RS}", flush=True)
    else:
        print(f"{ts}{name_tag}{msg}", flush=True)


def _stream(stream):
    """Lê stdout+stderr do subprocesso linha a linha e colore."""
    for raw in iter(stream.readline, b""):
        line = raw.decode("utf-8", errors="replace")
        _colorize(line)
    stream.close()


def _watch_plugins():
    """Detecta mudanças nos arquivos de plugin em tempo real."""
    global _plugin_mtimes
    for f in Path(PLUGIN_DIR).glob("*.py"):
        _plugin_mtimes[f.name] = f.stat().st_mtime

    while True:
        time.sleep(1.5)
        current = {}
        try:
            current = {f.name: f.stat().st_mtime for f in Path(PLUGIN_DIR).glob("*.py")}
        except Exception:
            continue

        for name, mtime in current.items():
            prev = _plugin_mtimes.get(name)
            if prev is None:
                if _filter in (None, "plugins"):
                    ts = f"{DIM}{datetime.now().strftime('%H:%M:%S')}{RS} "
                    print(f"{ts}{MA}{NE}🔌 {RS}{MA}[PLUGIN] New: {name}{RS}", flush=True)
            elif mtime != prev:
                if _filter in (None, "plugins"):
                    ts = f"{DIM}{datetime.now().strftime('%H:%M:%S')}{RS} "
                    print(f"{ts}{MA}{NE}🔌 {RS}{MA}[PLUGIN] Modified: {name}{RS}", flush=True)
            _plugin_mtimes[name] = mtime

        for name in list(_plugin_mtimes):
            if name not in current:
                if _filter in (None, "plugins"):
                    ts = f"{DIM}{datetime.now().strftime('%H:%M:%S')}{RS} "
                    print(f"{ts}{MA}{NE}🔌 {RS}{MA}[PLUGIN] Removed: {name}{RS}", flush=True)
                del _plugin_mtimes[name]


def main():
    global _proc, _filter

    _filter = sys.argv[1].lower() if len(sys.argv) > 1 else None
    valid   = ("cmds", "errors", "plugins")
    if _filter and _filter not in valid:
        print(f"{R}Filtro inválido '{_filter}'. Use: {', '.join(valid)}{RS}")
        sys.exit(1)

    filter_label = (
        f"  Filtro → {AM}{NE}{_filter.upper()}{RS}"
        if _filter
        else f"  {DIM}Sem filtro — exibindo tudo (loggers pyrogram suprimidos){RS}"
    )

    print(f"\n{AZ}{NE}╔══════════════════════════════════════════════════╗{RS}")
    print(f"{AZ}{NE}║    🖥️  USERBOT PRO v2.3 — ADMIN DEBUG PANEL        ║{RS}")
    print(f"{AZ}{NE}╚══════════════════════════════════════════════════╝{RS}")
    print(filter_label)
    print(f"  {DIM}Ctrl+C para encerrar o bot e o painel{RS}\n")
    print(f"  {CI}⌨ {RS} comando      {R}✗ {RS} erro      {AM}⚠ {RS} warning")
    print(f"  {V}● {RS} status bot   {MA}🔌{RS} plugin     {DIM}[Nome]{RS} módulo\n")
    print(f"  {DIM}{'─' * 50}{RS}\n")

    # Watcher de plugins em background
    if os.path.isdir(PLUGIN_DIR):
        threading.Thread(target=_watch_plugins, daemon=True).start()

    # Sobe o main.py com --debug (pula prompt de segundo plano)
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    _proc = subprocess.Popen(
        [sys.executable, "-u", "main.py", "--debug"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=sys.stdin,
        env=env,
        bufsize=0,
    )

    threading.Thread(target=_stream, args=(_proc.stdout,), daemon=True).start()

    try:
        _proc.wait()
    except KeyboardInterrupt:
        print(f"\n{AM}⏹  Encerrando o bot...{RS}")
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _proc.kill()
        print(f"{AM}👋 Bot encerrado.{RS}\n")


if __name__ == "__main__":
    main()
