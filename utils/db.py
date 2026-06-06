"""
utils/db.py
Camada de persistência: SQLite KV-store com cache em memória (TTL 30s).
Exportado por utils/helpers.py — plugins não precisam mudar os imports.
"""
import os
import json
import time
import sqlite3
import logging
from typing import Any

logger = logging.getLogger("UserbotDB")

DB_PATH = "userbot.db"
_FILE_KEYS = frozenset({"config.json", ".update_pending.json", ".deps_updated.json"})

# Cache em memória — evita queries SQLite repetidas nos handlers passivos
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL: float = 30.0


def _cache_hit(key: str) -> tuple[bool, Any]:
    entry = _CACHE.get(key)
    if entry and time.time() - entry[0] < _CACHE_TTL:
        return True, entry[1]
    _CACHE.pop(key, None)
    return False, None


def _cache_put(key: str, value: Any) -> None:
    _CACHE[key] = (time.time(), value)


def cache_bust(key: str) -> None:
    """Invalida manualmente uma entrada do cache (útil em testes ou reloads forçados)."""
    _CACHE.pop(key, None)


def _init_db() -> None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)"
            )
    except sqlite3.DatabaseError:
        logger.warning(f"⚠️  Banco corrompido. Recriando {DB_PATH} — dados anteriores serão perdidos.")
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)"
            )


_init_db()


def salvar(arquivo: str, dados: Any) -> None:
    """Persiste dados. Arquivos de controle usam JSON físico; todo o resto vai pro SQLite + cache."""
    if arquivo in _FILE_KEYS:
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        _cache_put(arquivo, dados)
        return

    serializado = json.dumps(dados, ensure_ascii=False)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
                (arquivo, serializado),
            )
        _cache_put(arquivo, dados)
    except sqlite3.DatabaseError:
        logger.warning(f"⚠️  Falha ao salvar '{arquivo}'. Banco corrompido — recriando.")
        _init_db()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
                    (arquivo, serializado),
                )
            _cache_put(arquivo, dados)
        except Exception:
            pass


def carregar(arquivo: str, padrao: Any) -> Any:
    """Carrega dados. Verifica cache antes de tocar no disco ou no SQLite."""
    if arquivo in _FILE_KEYS:
        if os.path.exists(arquivo):
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return padrao

    hit, val = _cache_hit(arquivo)
    if hit:
        return val

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT value FROM kv_store WHERE key = ?", (arquivo,)
            )
            row = cursor.fetchone()
            if row:
                try:
                    val = json.loads(row[0])
                    _cache_put(arquivo, val)
                    return val
                except Exception:
                    pass
    except sqlite3.DatabaseError:
        logger.warning(f"⚠️  Falha ao carregar '{arquivo}'. Banco corrompido — recriando.")
        _init_db()

    # Migração automática JSON → SQLite (v2.1 → v2.2)
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            salvar(arquivo, dados)
            os.remove(arquivo)
            return dados
        except Exception:
            pass

    return padrao
