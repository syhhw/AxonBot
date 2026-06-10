"""
plugins/panel.py
IPC bridge: heartbeat de status (com métricas de sistema) + despacho de comandos do painel bot.
"""
import os
import json
import asyncio
import time
import subprocess

import psutil
from pyrogram import Client
from utils.helpers import reiniciar_processo

_CMD_FILE    = "_panel_cmd.json"
_RESULT_FILE = "_panel_result.json"
_STATUS_FILE = "_panel_status.json"

_HEARTBEAT_INTERVAL = 15
_POLL_INTERVAL      = 2


def _write_json(path: str, data: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _write_result(ts: int, status: str, data: str) -> None:
    _write_json(_RESULT_FILE, {"ts": ts, "status": status, "data": data})


async def _on_start(client: Client) -> None:
    """Hook chamado por main.py após carregar todos os plugins."""
    asyncio.create_task(_heartbeat_loop(client))
    asyncio.create_task(_command_loop(client))


async def _heartbeat_loop(client: Client) -> None:
    while True:
        try:
            from plugins import account as _acc
            afk_ativo = getattr(_acc, "AFK_ATIVO", False)
        except Exception:
            afk_ativo = False

        try:
            vm   = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu  = psutil.cpu_percent(interval=None)
            ram_used_mb  = vm.used  // 1024 // 1024
            ram_total_mb = vm.total // 1024 // 1024
        except Exception:
            cpu = ram_used_mb = ram_total_mb = 0
            vm = disk = None

        _write_json(_STATUS_FILE, {
            "ts":           int(time.time()),
            "online":       True,
            "versao":       getattr(client, "VERSAO", "?"),
            "uptime_s":     time.time() - getattr(client, "tempo_inicio", time.time()),
            "afk":          afk_ativo,
            "prefixo":      getattr(client, "PREFIXO", ","),
            "lang":         getattr(client, "LANG", "pt"),
            "cpu_pct":      round(cpu, 1),
            "ram_pct":      round(vm.percent, 1) if vm else 0,
            "ram_used_mb":  ram_used_mb,
            "ram_total_mb": ram_total_mb,
            "disk_pct":     round(disk.percent, 1) if disk else 0,
        })
        await asyncio.sleep(_HEARTBEAT_INTERVAL)


async def _command_loop(client: Client) -> None:
    while True:
        if os.path.exists(_CMD_FILE):
            try:
                with open(_CMD_FILE, encoding="utf-8") as f:
                    cmd = json.load(f)
                os.remove(_CMD_FILE)
            except Exception:
                await asyncio.sleep(_POLL_INTERVAL)
                continue

            action = cmd.get("action", "")
            ts     = cmd.get("ts", 0)

            if action == "restart":
                _write_result(ts, "ok", "Reiniciando...")
                await asyncio.sleep(1)
                reiniciar_processo()
                return

            elif action == "shutdown":
                _write_result(ts, "ok", "Desligando...")
                await asyncio.sleep(1)
                os._exit(0)
                return

            elif action == "update":
                _write_result(ts, "ok", "Atualizando e reiniciando...")
                await asyncio.sleep(1)
                subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True)
                reiniciar_processo()
                return

            else:
                _write_result(ts, "error", f"Ação desconhecida: {action}")

        await asyncio.sleep(_POLL_INTERVAL)
