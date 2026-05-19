"""
utils/helpers.py
Funções auxiliares compartilhadas por todos os plugins.
"""
import os
import json
import time
import asyncio
import sqlite3
import sys
import subprocess
from pyrogram import filters, enums
from utils.i18n import tr, get_lang, COMMAND_ALIASES


DB_PATH = "userbot.db"

def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)")

_init_db()

def salvar(arquivo, dados):
    """Salva dados. Se for config/update, mantém como arquivo físico. Senão, usa SQLite."""
    if arquivo in ["config.json", ".update_pending.json", ".deps_updated.json"]:
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
            (arquivo, json.dumps(dados, ensure_ascii=False))
        )


def carregar(arquivo, padrao):
    """Carrega dados. Tenta SQLite primeiro. Auto-migra arquivos JSON legados."""
    if arquivo in ["config.json", ".update_pending.json", ".deps_updated.json"]:
        if os.path.exists(arquivo):
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return padrao

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT value FROM kv_store WHERE key = ?", (arquivo,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except:
                pass

    # Migração automática de JSON para SQLite (v2.1 -> v2.2)
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            salvar(arquivo, dados)
            os.remove(arquivo)  # Apaga o JSON velho após migrar
            return dados
        except:
            pass

    return padrao


def deletar_depois(message, tempo=30):
    """Deleta uma mensagem automaticamente após X segundos sem travar o bot."""
    async def _tarefa():
        await asyncio.sleep(tempo)
        try:
            await message.delete()
        except:
            pass
    asyncio.create_task(_tarefa())


def prefixo(client):
    return getattr(client, "PREFIXO", ",")


def cmd_filter(nome):
    """Cria um filtro dinâmico que valida o prefixo do cliente em tempo real."""
    async def func(flt, client, message):
        if not message.text:
            return False
        p = prefixo(client)
        lang = get_lang()
        alias = COMMAND_ALIASES.get(nome, nome)
        validos = [nome]
        if lang == "en" and alias != nome:
            validos.append(alias)
        for cmd in validos:
            if message.text == f"{p}{cmd}" or message.text.startswith(f"{p}{cmd} "):
                return True
        return False
    return filters.create(func)


async def verificar_admin(client, chat_id):
    """Verifica se o userbot é admin no chat. Cache de 15 dias."""
    agora = time.time()
    cid = str(chat_id)
    cache = carregar("admin_cache.json", {})
    if cid in cache and agora - cache[cid].get("checado_em", 0) < 1296000:
        return cache[cid].get("is_admin", False)
    try:
        m = await client.get_chat_member(chat_id, "me")
        is_admin = m.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
        cache[cid] = {"is_admin": is_admin, "checado_em": agora, "era_admin": is_admin}
        salvar("admin_cache.json", cache)
        return is_admin
    except:
        return False


async def auditoria(client, acao, user, chat, motivo=None, msg_orig=None):
    """Envia log detalhado de moderação para o canal de logs."""
    cfg = getattr(client, "config", {})
    log_id = cfg.get("ID_CANAL_LOGS")
    if not log_id:
        return
    nome = getattr(user, "first_name", "Desconhecido") if user else "Desconhecido"
    uid = getattr(user, "id", "?") if user else "?"
    chat_titulo = getattr(chat, "title", "Chat Privado")
    txt = tr(
        f"🛡️ **AUDITORIA DE MODERAÇÃO**\n\n⚙️ **Ação:** `{acao}`\n👤 **Alvo:** {nome} (`{uid}`)\n📍 **Chat:** {chat_titulo}\n",
        f"🛡️ **MODERATION AUDIT**\n\n⚙️ **Action:** `{acao}`\n👤 **Target:** {nome} (`{uid}`)\n📍 **Chat:** {chat_titulo}\n"
    )
    if motivo:
        txt += tr(f"📝 **Motivo:** `{motivo}`\n", f"📝 **Reason:** `{motivo}`\n")
    if msg_orig:
        conteudo = msg_orig.text or msg_orig.caption or tr("[Mídia]", "[Media]")
        txt += tr(f"\n💬 **Mensagem original:**\n`{conteudo[:400]}`", f"\n💬 **Original message:**\n`{conteudo[:400]}`")
    try:
        await client.send_message(log_id, txt)
    except:
        pass


async def resolver_alvo(client, message):
    """
    Resolve o alvo de um comando de moderação aceitando 3 formatos:
      1. Resposta a uma mensagem (reply)
      2. @username como argumento
      3. ID numérico como argumento
    Retorna (user_obj, motivo, msg_origem) ou (None, None, None) se não encontrar.
    """
    partes = message.text.split(None, 2)
    user_obj = None
    motivo = None
    msg_origem = None

    if message.reply_to_message and message.reply_to_message.from_user:
        user_obj = message.reply_to_message.from_user
        msg_origem = message.reply_to_message
        if len(partes) > 1:
            motivo = " ".join(partes[1:])
    elif len(partes) > 1:
        alvo = partes[1].strip()
        if len(partes) > 2:
            motivo = partes[2]
        try:
            if alvo.startswith("@"):
                user_obj = await client.get_users(alvo)
            else:
                user_obj = await client.get_users(int(alvo))
        except (ValueError, Exception):
            return None, None, None
    return user_obj, motivo, msg_origem


def reiniciar_processo():
    """Reinicia o bot de forma limpa usando subprocess (Graceful Restart)."""
    python = sys.executable
    args   = sys.argv[:]

    if "--no-screen" not in args:
        args.append("--no-screen")
    if "--background" not in args and "--background" in sys.argv:
        args.append("--background")

    kwargs = {}
    if os.name == "nt" and "--background" in args:
        python = python.replace("python.exe", "pythonw.exe")
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    subprocess.Popen([python] + args, **kwargs)
    os._exit(0)
