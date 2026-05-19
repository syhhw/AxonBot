"""
utils/i18n.py
Módulo profissional de internacionalização (i18n).
Centraliza o gerenciamento de idioma e as traduções do bot.
"""
import os
import json

_LANG = "pt"

COMMAND_ALIASES = {
    "versao": "version", "atualizar": "update", "processos": "processes",
    "organizar": "organize", "procurar": "search", "apagar": "delete",
    "encurtar": "shorten", "clima": "weather", "voz": "voice",
    "direto": "direct", "resumir": "summarize", "idioma": "lang",
    "zombies": "zombies", "reverter": "revert", "desligar": "stop",
    "instalar": "install", "desinstalar": "uninstall"
}

def _load_lang():
    global _LANG
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                _LANG = json.load(f).get("LANGUAGE", "pt")
        except Exception:
            pass

_load_lang()

def set_lang(lang: str):
    """Muda o idioma globalmente em tempo de execução."""
    global _LANG
    _LANG = lang

def get_lang() -> str:
    return _LANG

def tr(pt: str, en: str) -> str:
    """Retorna o texto traduzido baseado no idioma atual do sistema."""
    return en if _LANG == "en" else pt