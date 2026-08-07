"""
plugins/menu.py
  ,menu          — índice compacto de categorias (nome + quantidade de comandos).
  ,menu [módulo] — detalhes de um módulo específico (lista com descrições).

Lê os comandos direto do utils.commands.REGISTRY (preenchido quando cada
plugin carrega, via o decorator @cmd) em vez de reabrir e reparsear cada
arquivo .py a cada chamada.

Nota: teclado inline (reply_markup) não é usado aqui de propósito — no
Telegram, reply_markup só é aceito em mensagens enviadas por conta de
bot; numa conta de usuário (userbot) o servidor aceita a edição do texto
e descarta o teclado silenciosamente. Testado ao vivo em PV e grupo.
"""
import logging
logger = logging.getLogger("AxonBot.menu")

from utils.helpers import prefixo, deletar_depois, tr, DEL_LONGO
from utils.commands import cmd, REGISTRY
from utils.i18n import COMMAND_ALIASES


_MODULO_ORDER = [
    "system.py", "alive.py", "moderation.py", "purge.py", "locks.py", "tools.py",
    "kang.py", "account.py", "profile.py", "downloader.py", "ai.py", "info.py",
    "paste.py", "carbon.py", "stats.py", "id.py", "dev.py",
    "notes.py", "welcome.py", "chatfilters.py", "triggers.py",
    "antiflood.py", "sed.py", "tagall.py", "drive.py",
]

_NOMES_PT = {
    "system.py":      "🖥️ Sistema",
    "alive.py":       "⚡ Status",
    "moderation.py":  "👮 Moderação",
    "purge.py":       "🗑️ Limpeza de Chat",
    "locks.py":       "🔒 Travas do Grupo",
    "info.py":        "🔎 Info & Pesquisa",
    "drive.py":       "📂 Google Drive",
    "tools.py":       "🛠️ Ferramentas",
    "account.py":     "👤 Conta & AFK",
    "profile.py":     "🪪 Perfil",
    "kang.py":        "🎭 Figurinhas",
    "ai.py":          "🧠 Inteligência Artificial",
    "dev.py":         "⚙️ Desenvolvedor",
    "downloader.py":  "⬇️ Downloader",
    "paste.py":       "📋 Paste",
    "carbon.py":      "🎨 Carbon",
    "stats.py":       "📊 Estatísticas",
    "id.py":          "🆔 IDs",
    "triggers.py":    "⚡ Gatilhos",
    "chatfilters.py": "🔍 Filtros do Chat",
    "notes.py":       "📋 Notas",
    "welcome.py":     "👋 Boas-vindas",
    "antiflood.py":   "🚨 Antiflood",
    "sed.py":         "✏️ Substituição",
    "tagall.py":      "📢 Mencionar Todos",
}
_NOMES_EN = {
    "system.py":      "🖥️ System",
    "alive.py":       "⚡ Status",
    "moderation.py":  "👮 Moderation",
    "purge.py":       "🗑️ Chat Cleanup",
    "locks.py":       "🔒 Group Locks",
    "info.py":        "🔎 Info & Search",
    "drive.py":       "📂 Google Drive",
    "tools.py":       "🛠️ Tools",
    "account.py":     "👤 Account & AFK",
    "profile.py":     "🪪 Profile",
    "kang.py":        "🎭 Stickers",
    "ai.py":          "🧠 Artificial Intelligence",
    "dev.py":         "⚙️ Developer",
    "downloader.py":  "⬇️ Downloader",
    "paste.py":       "📋 Paste",
    "carbon.py":      "🎨 Carbon",
    "stats.py":       "📊 Stats",
    "id.py":          "🆔 IDs",
    "triggers.py":    "⚡ Triggers",
    "chatfilters.py": "🔍 Chat Filters",
    "notes.py":       "📋 Notes",
    "welcome.py":     "👋 Welcome",
    "antiflood.py":   "🚨 Antiflood",
    "sed.py":         "✏️ Sed",
    "tagall.py":      "📢 Tag All",
}

# Palavras-chave → arquivo do módulo (para `,menu <termo>`)
_ALIAS = {
    "sistema": "system.py",    "system": "system.py",
    "atualizar": "system.py",  "update": "system.py",
    "mod": "moderation.py",    "moderação": "moderation.py",   "moderation": "moderation.py",
    "moderacao": "moderation.py",
    "ferramentas": "tools.py", "tools": "tools.py",
    "figurinhas": "kang.py",   "stickers": "kang.py",          "kang": "kang.py",
    "conta": "account.py",     "account": "account.py",        "afk": "account.py",
    "dl": "downloader.py",     "downloader": "downloader.py",
    "ia": "ai.py",             "ai": "ai.py",                  "gemini": "ai.py",
    "dev": "dev.py",           "desenvolvedor": "dev.py",      "developer": "dev.py",
    "drive": "drive.py",       "gdrive": "drive.py",
    "notas": "notes.py",       "notes": "notes.py",
    "welcome": "welcome.py",   "boas-vindas": "welcome.py",
    "filtros": "chatfilters.py", "chatfilters": "chatfilters.py",
    "gatilhos": "triggers.py", "triggers": "triggers.py",
    "antiflood": "antiflood.py",
    "sed": "sed.py",
    "tagall": "tagall.py",     "mencionar": "tagall.py",
    "alive": "alive.py",       "status": "alive.py",
    "setalivephoto": "alive.py", "delalivephoto": "alive.py",
    "travas": "locks.py",      "locks": "locks.py",            "travar": "locks.py",
    "info": "info.py",         "github": "info.py",            "filme": "info.py",
    "purge": "purge.py",       "del": "purge.py",              "purgeme": "purge.py",
    "perfil": "profile.py",    "profile": "profile.py",        "setname": "profile.py",
    "setbio": "profile.py",    "setpfp": "profile.py",         "delpfp": "profile.py",
    "paste": "paste.py",
    "carbon": "carbon.py",
    "stats": "stats.py",       "estatísticas": "stats.py",
    "id": "id.py",
}


def _limpar_desc(desc: str, max_len: int = 42) -> str:
    if not desc:
        return ""
    desc = desc.split("\n")[0].rstrip(".").strip()
    if len(desc) > max_len:
        desc = desc[:max_len].rstrip() + "…"
    return desc


def _nome_modulo(filename: str, lang: str) -> str:
    nomes = _NOMES_EN if lang == "en" else _NOMES_PT
    base  = filename.replace(".py", "").capitalize()
    return nomes.get(filename, f"🔌 {base}")


def _resolver_modulo(query: str) -> str | None:
    q = query.strip().lower()
    if q in _ALIAS:
        return _ALIAS[q]
    for key, fn in _ALIAS.items():
        if q in key:
            return fn
    candidate = q if q.endswith(".py") else f"{q}.py"
    if candidate in REGISTRY:
        return candidate
    return None


def _build_modulo_section(filename: str, comandos, p: str, lang: str,
                           desc_len: int = 42) -> str:
    titulo = _nome_modulo(filename, lang)
    n      = len(comandos)
    linhas = []
    for c in comandos:
        nome_cmd = COMMAND_ALIASES.get(c.nome, c.nome) if lang == "en" else c.nome
        desc     = _limpar_desc(c.desc, max_len=desc_len)
        entry    = f"  `{p}{nome_cmd}`"
        if desc:
            entry += f" — {desc}"
        linhas.append(entry)
    return f"**{titulo}** ({n})\n" + "\n".join(linhas)


def _arquivos_ordenados() -> list[str]:
    return sorted(
        (f for f in REGISTRY if f != "menu.py"),
        key=lambda f: (_MODULO_ORDER.index(f) if f in _MODULO_ORDER else len(_MODULO_ORDER), f),
    )


@cmd("menu")
async def cmd_menu(client, message):
    """Índice de categorias. ,menu [módulo] mostra os comandos de uma delas."""
    p      = prefixo(client)
    lang   = getattr(client, "LANG", "pt")
    partes = message.text.split(None, 1)

    # ── Detalhe de um módulo específico ──────────────────────────────────────
    if len(partes) > 1:
        query    = partes[1].strip()
        filename = _resolver_modulo(query)
        comandos = REGISTRY.get(filename) if filename else None
        if not filename or not comandos:
            return await message.edit_text(tr(
                f"❌ Módulo `{query}` não encontrado.\nUse `{p}menu` para ver todos.",
                f"❌ Module `{query}` not found.\nUse `{p}menu` to see all.",
            ))
        text = _build_modulo_section(filename, comandos, p, lang, desc_len=50)
        await message.edit_text(text, disable_web_page_preview=True)
        deletar_depois(message, DEL_LONGO)
        return

    # ── Padrão: índice compacto — uma linha por categoria ─────────────────────
    arquivos   = [f for f in _arquivos_ordenados() if REGISTRY.get(f)]
    total_cmds = sum(len(REGISTRY[f]) for f in arquivos)

    if not arquivos:
        return await message.edit_text(tr("⚠️ Nenhum comando encontrado.", "⚠️ No commands found."))

    # Estilo plain-ub (thedragonsinn/plain-ub): cabeçalho por categoria +
    # lista de comandos num bloco tipo array, sem botão — inline keyboard
    # não é enviável por conta de usuário (só por bot), testado ao vivo.
    blocos = []
    for fn in arquivos:
        nomes = [
            (COMMAND_ALIASES.get(c.nome, c.nome) if lang == "en" else c.nome)
            for c in REGISTRY[fn]
        ]
        lista = "[" + ", ".join(nomes) + "]"
        blocos.append(f"**{_nome_modulo(fn, lang)}**\n`{lista}`")

    texto = tr(
        f"⚡ **AXONBOT** — {total_cmds} comandos · {len(arquivos)} módulos · prefixo `{p}`\n\n"
        + "\n\n".join(blocos) +
        f"\n\n💡 `{p}menu [módulo]` — detalhes\n"
        f"   Ex: `{p}menu mod`  `{p}menu dl`  `{p}menu ia`",

        f"⚡ **AXONBOT** — {total_cmds} commands · {len(arquivos)} modules · prefix `{p}`\n\n"
        + "\n\n".join(blocos) +
        f"\n\n💡 `{p}menu [module]` — full details\n"
        f"   Ex: `{p}menu mod`  `{p}menu dl`  `{p}menu ai`",
    )
    await message.edit_text(texto, disable_web_page_preview=True)
    deletar_depois(message, DEL_LONGO)
