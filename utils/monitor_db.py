"""
utils/monitor_db.py
Banco dedicado às mensagens capturadas pelo monitor (PV/menção) —
tabela SQL própria em vez do kv_store genérico de utils/db.py, porque
isso cresce muito e precisa de consulta por data (GROUP BY, WHERE data
= X). Framework-agnostic (só sqlite3) — usado pelo userbot (grava) e
pelo painel bot (lê os relatórios). Compartilha o mesmo userbot.db.
"""
import sqlite3
import time
import logging
from datetime import datetime

logger = logging.getLogger("AxonBot.monitor_db")

DB_PATH = "userbot.db"


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, timeout=10)


def _init() -> None:
    try:
        with _conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS monitor_mensagens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    chat_id INTEGER NOT NULL,
                    chat_nome TEXT,
                    sender_id INTEGER,
                    sender_nome TEXT,
                    sender_username TEXT,
                    texto TEXT,
                    tem_midia INTEGER DEFAULT 0
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_monitor_data ON monitor_mensagens(data)")
    except Exception as e:
        logger.warning(f"Falha ao inicializar monitor_mensagens: {e}")


_init()


def registrar(
    tipo: str, chat_id: int, chat_nome: str,
    sender_id: int, sender_nome: str, sender_username: str,
    texto: str, tem_midia: bool = False,
) -> None:
    """tipo: 'pm' ou 'mencao'. Trunca texto em 1000 chars pra não inchar o banco à toa."""
    agora = time.time()
    data  = datetime.fromtimestamp(agora).strftime("%Y-%m-%d")
    if texto and len(texto) > 1000:
        texto = texto[:1000] + "…"
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO monitor_mensagens "
                "(ts, data, tipo, chat_id, chat_nome, sender_id, sender_nome, sender_username, texto, tem_midia) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (int(agora), data, tipo, chat_id, chat_nome, sender_id, sender_nome, sender_username,
                 texto, int(tem_midia)),
            )
    except Exception as e:
        logger.debug(f"Falha ao registrar mensagem monitorada: {e}")


def contagem_por_dia(limite_dias: int = 30) -> list[tuple[str, int]]:
    """[(data, total), ...] mais recente primeiro."""
    try:
        with _conn() as c:
            cur = c.execute(
                "SELECT data, COUNT(*) FROM monitor_mensagens GROUP BY data ORDER BY data DESC LIMIT ?",
                (limite_dias,),
            )
            return cur.fetchall()
    except Exception as e:
        logger.debug(f"Falha ao contar por dia: {e}")
        return []


def mensagens_do_dia(data: str, offset: int = 0, limite: int = 15) -> list[dict]:
    """Mensagens de um dia (YYYY-MM-DD), paginado, mais recente primeiro."""
    try:
        with _conn() as c:
            cur = c.execute(
                "SELECT ts, tipo, chat_nome, sender_nome, sender_username, sender_id, texto, tem_midia "
                "FROM monitor_mensagens WHERE data = ? ORDER BY ts DESC LIMIT ? OFFSET ?",
                (data, limite, offset),
            )
            cols = ["ts", "tipo", "chat_nome", "sender_nome", "sender_username", "sender_id", "texto", "tem_midia"]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        logger.debug(f"Falha ao buscar mensagens do dia: {e}")
        return []


def total_do_dia(data: str) -> int:
    try:
        with _conn() as c:
            cur = c.execute("SELECT COUNT(*) FROM monitor_mensagens WHERE data = ?", (data,))
            return cur.fetchone()[0]
    except Exception:
        return 0


def total_geral() -> int:
    try:
        with _conn() as c:
            cur = c.execute("SELECT COUNT(*) FROM monitor_mensagens")
            return cur.fetchone()[0]
    except Exception:
        return 0


def limpar_dia(data: str) -> int:
    """Apaga as mensagens de um dia específico. Retorna quantas foram removidas."""
    try:
        with _conn() as c:
            cur = c.execute("DELETE FROM monitor_mensagens WHERE data = ?", (data,))
            return cur.rowcount
    except Exception as e:
        logger.debug(f"Falha ao limpar dia: {e}")
        return 0
