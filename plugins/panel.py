"""
plugins/panel.py
IPC plugin: escreve heartbeat de status a cada 30s e processa comandos do painel bot.

Protocolo de arquivos:
  _panel_status.json  — userbot escreve (lido pelo bot)
  _panel_cmd.json     — bot escreve (lido pelo userbot)
  _panel_result.json  — userbot escreve (lido pelo bot)
"""
import os
import json
import asyncio
import time

from pyrogram import Client
from utils.helpers import reiniciar_processo

_CMD_FILE    = "_panel_cmd.json"
_RESULT_FILE = "_panel_result.json"
_STATUS_FILE = "_panel_status.json"

_HEARTBEAT_INTERVAL = 30   # segundos entre escritas de status
_POLL_INTERVAL      = 3    # segundos entre checagens de comando


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
    asyncio.create_task(_panel_loop(client))


async def _panel_loop(client: Client) -> None:
    last_heartbeat = 0.0

    while True:
        now = time.time()

        # ── Heartbeat de status ───────────────────────────────────────────────
        if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
            try:
                from plugins import account as _acc
                afk_ativo = getattr(_acc, "AFK_ATIVO", False)
            except Exception:
                afk_ativo = False

            _write_json(_STATUS_FILE, {
                "online":   True,
                "versao":   getattr(client, "VERSAO", "?"),
                "uptime_s": now - getattr(client, "tempo_inicio", now),
                "afk":      afk_ativo,
                "prefixo":  getattr(client, "PREFIXO", ","),
                "lang":     getattr(client, "LANG", "pt"),
                "ts":       int(now),
            })
            last_heartbeat = now

        # ── Leitura de comandos ───────────────────────────────────────────────
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
                import subprocess
                _write_result(ts, "ok", "Atualizando e reiniciando...")
                await asyncio.sleep(1)
                subprocess.run(
                    ["git", "reset", "--hard", "origin/main"],
                    capture_output=True,
                )
                reiniciar_processo()
                return

            else:
                _write_result(ts, "error", f"Ação desconhecida: {action}")

        await asyncio.sleep(_POLL_INTERVAL)
