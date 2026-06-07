"""
utils/i18n.py
Módulo profissional de internacionalização (i18n).
Centraliza o gerenciamento de idioma e as traduções do bot.
"""
import os
import json

_LANG     = "pt"
_LOG_LANG = "pt"   # idioma do canal de logs (pode ser diferente do bot)

COMMAND_ALIASES = {
    # core
    "versao": "version", "atualizar": "update", "processos": "processes",
    "organizar": "organize", "procurar": "search", "apagar": "delete",
    "encurtar": "shorten", "clima": "weather", "voz": "voice",
    "direto": "direct", "resumir": "summarize", "idioma": "lang",
    "zombies": "zombies", "reverter": "revert", "desligar": "stop",
    "instalar": "install", "desinstalar": "uninstall", "perguntar": "ask",
    # chatfilters
    "addfiltro": "addfilter", "delfiltro": "delfilter", "filtros": "filters",
    # notes
    "nota": "note", "delnota": "delnote", "notas": "notes",
    # welcome
    "bemvindo": "welcome", "setbemvindo": "setwelcome", "delbemvindo": "delwelcome",
    # tagall
    "mencionar": "tagall",
}

def _load_lang():
    global _LANG, _LOG_LANG
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                _LANG     = cfg.get("LANGUAGE",     "pt")
                _LOG_LANG = cfg.get("LOG_LANGUAGE", _LANG)
        except Exception:
            pass

_load_lang()


def set_lang(lang: str) -> None:
    """Muda o idioma do bot em tempo de execução."""
    global _LANG
    _LANG = lang.lower().split("-")[0]  # aceita "pt-BR", "en-US", etc.


def set_log_lang(lang: str) -> None:
    """Muda o idioma exclusivo do canal de logs."""
    global _LOG_LANG
    _LOG_LANG = lang.lower().split("-")[0]


def get_lang() -> str:
    return _LANG


def get_log_lang() -> str:
    return _LOG_LANG


def tr(pt: str, en: str) -> str:
    """Tradução para mensagens do bot (responde no chat)."""
    return en if _LANG == "en" else pt


def tr_log(pt: str, en: str) -> str:
    """Tradução exclusiva para o canal de logs (usa LOG_LANGUAGE do config)."""
    return en if _LOG_LANG == "en" else pt