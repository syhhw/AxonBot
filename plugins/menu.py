"""
plugins/menu.py
  ,menu          — lista todos os módulos com seus comandos e descrições.
  ,menu [módulo] — detalhes de um módulo específico (descrições completas).
"""
import os
import re
import ast

from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, deletar_depois, tr
from utils.i18n import COMMAND_ALIASES


_MODULO_ORDER = [
    "system.py", "moderation.py", "tools.py", "kang.py",
    "account.py", "downloader.py", "ai.py", "dev.py",
    "notes.py", "welcome.py", "chatfilters.py", "triggers.py",
    "antiflood.py", "sed.py", "tagall.py", "drive.py",
]

_NOMES_PT = {
    "system.py":      "🖥️ Sistema",
    "moderation.py":  "👮 Moderação",
    "drive.py":       "📂 Google Drive",
    "tools.py":       "🛠️ Ferramentas",
    "account.py":     "👤 Conta & AFK",
    "kang.py":        "🎭 Figurinhas",
    "ai.py":          "🧠 Inteligência Artificial",
    "dev.py":         "⚙️ Desenvolvedor",
    "downloader.py":  "⬇️ Downloader",
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
    "moderation.py":  "👮 Moderation",
    "drive.py":       "📂 Google Drive",
    "tools.py":       "🛠️ Tools",
    "account.py":     "👤 Account & AFK",
    "kang.py":        "🎭 Stickers",
    "ai.py":          "🧠 Artificial Intelligence",
    "dev.py":         "⚙️ Developer",
    "downloader.py":  "⬇️ Downloader",
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


def extrair_comandos_do_arquivo(filepath: str) -> list[dict]:
    comandos = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        docstrings: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                doc = ast.get_docstring(node)
                if doc:
                    docstrings[node.name] = doc.splitlines()[0].strip()

        pattern = re.compile(
            r'cmd_filter\(["\'](\w+)["\']\).*?\n(?:.*?\n)*?async def (\w+)',
            re.MULTILINE,
        )
        for match in pattern.finditer(source):
            cmd_name, func_name = match.group(1), match.group(2)
            if cmd_name == "menu":
                continue
            comandos.append({"cmd": cmd_name, "desc": docstrings.get(func_name, "")})
    except Exception:
        pass
    return comandos


def _resolver_modulo(query: str, plugins_dir: str) -> str | None:
    q = query.strip().lower()
    if q in _ALIAS:
        return _ALIAS[q]
    for key, fn in _ALIAS.items():
        if q in key:
            return fn
    candidate = q if q.endswith(".py") else f"{q}.py"
    if os.path.exists(os.path.join(plugins_dir, candidate)):
        return candidate
    return None


def _build_modulo_section(filename: str, comandos: list[dict], p: str, lang: str,
                           desc_len: int = 42) -> str:
    titulo = _nome_modulo(filename, lang)
    n      = len(comandos)
    linhas = []
    for c in comandos:
        nome_cmd = COMMAND_ALIASES.get(c["cmd"], c["cmd"]) if lang == "en" else c["cmd"]
        desc     = _limpar_desc(c["desc"], max_len=desc_len)
        entry    = f"  `{p}{nome_cmd}`"
        if desc:
            entry += f" — {desc}"
        linhas.append(entry)
    return f"**{titulo}** ({n})\n" + "\n".join(linhas)


@Client.on_message(cmd_filter("menu") & filters.me)
async def cmd_menu(client, message):
    """Exibe módulos com comandos. ,menu [módulo] para detalhe."""
    p      = prefixo(client)
    lang   = getattr(client, "LANG", "pt")
    partes = message.text.split(None, 1)

    plugins_dir = os.path.dirname(os.path.abspath(__file__))

    # ── Detalhe de um módulo específico ──────────────────────────────────────
    if len(partes) > 1:
        query    = partes[1].strip()
        filename = _resolver_modulo(query, plugins_dir)
        if not filename:
            return await message.edit_text(tr(
                f"❌ Módulo `{query}` não encontrado.\nUse `{p}menu` para ver todos.",
                f"❌ Module `{query}` not found.\nUse `{p}menu` to see all.",
            ))
        filepath = os.path.join(plugins_dir, filename)
        comandos = extrair_comandos_do_arquivo(filepath)
        if not comandos:
            return await message.edit_text(tr(
                f"⚠️ Nenhum comando registrado em `{filename}`.",
                f"⚠️ No commands registered in `{filename}`.",
            ))
        text = _build_modulo_section(filename, comandos, p, lang, desc_len=50)
        await message.edit_text(text, disable_web_page_preview=True)
        deletar_depois(message, 60)
        return

    # ── Visão completa: todos os módulos com descrições ───────────────────────
    todos_arqs = [
        f for f in os.listdir(plugins_dir)
        if f.endswith(".py") and f != "menu.py" and not f.startswith("_")
    ]
    arquivos = sorted(
        todos_arqs,
        key=lambda f: (_MODULO_ORDER.index(f) if f in _MODULO_ORDER else len(_MODULO_ORDER), f),
    )

    modulos: list[tuple[str, list[dict]]] = []
    total_cmds = 0
    for filename in arquivos:
        filepath = os.path.join(plugins_dir, filename)
        comandos = extrair_comandos_do_arquivo(filepath)
        if not comandos:
            continue
        modulos.append((filename, comandos))
        total_cmds += len(comandos)

    if not modulos:
        return await message.edit_text(tr("⚠️ Nenhum comando encontrado.", "⚠️ No commands found."))

    versao = getattr(client, "VERSAO", "1.0")
    n_mods = len(modulos)

    header = tr(
        f"⚡ **USERBOT PRO v{versao}**\n"
        f"├ 🔧 Prefixo: `{p}`\n"
        f"├ 📦 {total_cmds} comandos  ·  {n_mods} módulos\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n",
        f"⚡ **USERBOT PRO v{versao}**\n"
        f"├ 🔧 Prefix: `{p}`\n"
        f"├ 📦 {total_cmds} commands  ·  {n_mods} modules\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n",
    )
    footer = tr(
        f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 `{p}menu [módulo]` — detalhes completos\n"
        f"   Ex: `{p}menu mod`  `{p}menu dl`  `{p}menu ia`",
        f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 `{p}menu [module]` — full details\n"
        f"   Ex: `{p}menu mod`  `{p}menu dl`  `{p}menu ai`",
    )

    # Tenta a versão detalhada (com descrições curtas)
    secoes_det = [_build_modulo_section(fn, cmds, p, lang, desc_len=42) for fn, cmds in modulos]
    full_text  = header + "\n\n".join(secoes_det) + footer

    if len(full_text) <= 4000:
        await message.edit_text(full_text, disable_web_page_preview=True)
        deletar_depois(message, 60)
        return

    # Fallback: tabela de conteúdo com chips (até 6 comandos por módulo)
    _SHOW = 6
    secoes_toc = []
    for filename, comandos in modulos:
        titulo = _nome_modulo(filename, lang)
        n      = len(comandos)
        chips  = []
        for c in comandos[:_SHOW]:
            nome_cmd = COMMAND_ALIASES.get(c["cmd"], c["cmd"]) if lang == "en" else c["cmd"]
            chips.append(f"`{p}{nome_cmd}`")
        resto  = n - _SHOW
        linha_cmds = "  " + "  ".join(chips)
        if resto > 0:
            linha_cmds += tr(f"  _+{resto} mais_", f"  _+{resto} more_")
        secoes_toc.append(f"**{titulo}** ({n})\n{linha_cmds}")

    await message.edit_text(
        header + "\n\n".join(secoes_toc) + footer,
        disable_web_page_preview=True,
    )
    deletar_depois(message, 60)
