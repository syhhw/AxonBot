"""
plugins/info.py
  ,github [user]  — perfil de usuário ou repositório no GitHub
  ,filme [nome]   — informações de filme ou série (OMDb)
"""
import aiohttp

from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, deletar_depois, tr

_GH_API    = "https://api.github.com"
_OMDB_BASE = "https://www.omdbapi.com/"
_OMDB_KEY  = "trilogy"           # chave pública gratuita; substitua pela sua se parar de funcionar


def _n(val, fallback="?") -> str:
    return str(val) if val and val not in ("N/A", "null", None) else fallback


@Client.on_message(cmd_filter("github") & filters.me)
async def cmd_github(client, message):
    """Consulta perfil ou repositório do GitHub. ,github user  ou  ,github user/repo"""
    p      = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(
            f"⚠️ Use: `{p}github [usuario]` ou `{p}github [usuario/repo]`",
            f"⚠️ Use: `{p}github [user]` or `{p}github [user/repo]`",
        ))

    query   = partes[1].strip().lstrip("/")
    is_repo = "/" in query
    endpoint = f"{_GH_API}/repos/{query}" if is_repo else f"{_GH_API}/users/{query}"

    await message.edit_text(tr("🔍 **Buscando no GitHub...**", "🔍 **Searching GitHub...**"))

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(
                endpoint,
                headers={"Accept": "application/vnd.github+json"},
            ) as resp:
                if resp.status == 404:
                    return await message.edit_text(tr(
                        f"❌ `{query}` não encontrado no GitHub.",
                        f"❌ `{query}` not found on GitHub.",
                    ))
                data = await resp.json()
    except Exception as e:
        return await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))

    if is_repo:
        nome      = data.get("full_name", query)
        desc      = _n(data.get("description"))
        stars     = data.get("stargazers_count", 0)
        forks     = data.get("forks_count", 0)
        watch     = data.get("watchers_count", 0)
        issues    = data.get("open_issues_count", 0)
        lang      = _n(data.get("language"))
        licenca   = _n(data.get("license", {}).get("name") if data.get("license") else None)
        topicos   = ", ".join(data.get("topics", [])) or "—"
        url       = data.get("html_url", "")
        criado    = (_n(data.get("created_at")) or "")[:10]
        atualiz   = (_n(data.get("updated_at")) or "")[:10]

        txt = tr(
            f"📦 **[{nome}]({url})**\n\n"
            f"├ 📝 {desc}\n"
            f"├ ⭐ Stars: `{stars:,}` · 🍴 Forks: `{forks:,}`\n"
            f"├ 👁️ Watch: `{watch:,}` · 🐛 Issues: `{issues:,}`\n"
            f"├ 💻 Linguagem: `{lang}`\n"
            f"├ 📜 Licença: `{licenca}`\n"
            f"├ 🏷️ Tópicos: {topicos}\n"
            f"├ 📅 Criado: `{criado}`\n"
            f"└ 🔄 Atualizado: `{atualiz}`",

            f"📦 **[{nome}]({url})**\n\n"
            f"├ 📝 {desc}\n"
            f"├ ⭐ Stars: `{stars:,}` · 🍴 Forks: `{forks:,}`\n"
            f"├ 👁️ Watch: `{watch:,}` · 🐛 Issues: `{issues:,}`\n"
            f"├ 💻 Language: `{lang}`\n"
            f"├ 📜 License: `{licenca}`\n"
            f"├ 🏷️ Topics: {topicos}\n"
            f"├ 📅 Created: `{criado}`\n"
            f"└ 🔄 Updated: `{atualiz}`",
        )
    else:
        nome    = data.get("name") or data.get("login", query)
        login   = data.get("login", query)
        bio     = _n(data.get("bio"))
        repos   = data.get("public_repos", 0)
        gists   = data.get("public_gists", 0)
        seguid  = data.get("followers", 0)
        seguind = data.get("following", 0)
        local   = _n(data.get("location"))
        empresa = _n(data.get("company"))
        blog    = _n(data.get("blog"))
        url     = data.get("html_url", "")
        criado  = (_n(data.get("created_at")) or "")[:10]

        txt = tr(
            f"👤 **[{nome}]({url})** (`{login}`)\n\n"
            f"├ 📝 {bio}\n"
            f"├ 📦 Repos: `{repos}` · 📋 Gists: `{gists}`\n"
            f"├ 👥 Seguidores: `{seguid:,}` · Seguindo: `{seguind:,}`\n"
            f"├ 📍 Local: `{local}`\n"
            f"├ 🏢 Empresa: `{empresa}`\n"
            f"├ 🌐 Blog: {blog}\n"
            f"└ 📅 Desde: `{criado}`",

            f"👤 **[{nome}]({url})** (`{login}`)\n\n"
            f"├ 📝 {bio}\n"
            f"├ 📦 Repos: `{repos}` · 📋 Gists: `{gists}`\n"
            f"├ 👥 Followers: `{seguid:,}` · Following: `{seguind:,}`\n"
            f"├ 📍 Location: `{local}`\n"
            f"├ 🏢 Company: `{empresa}`\n"
            f"├ 🌐 Blog: {blog}\n"
            f"└ 📅 Since: `{criado}`",
        )

    await message.edit_text(txt, disable_web_page_preview=True)
    deletar_depois(message, 60)


@Client.on_message(cmd_filter("filme") & filters.me)
async def cmd_filme(client, message):
    """Busca informações de filme ou série no IMDb via OMDb. ,filme [nome]"""
    p      = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(
            f"⚠️ Use: `{p}filme [nome do filme]`",
            f"⚠️ Use: `{p}movie [movie name]`",
        ))

    query = partes[1].strip()
    await message.edit_text(tr("🎬 **Buscando filme...**", "🎬 **Searching movie...**"))

    cfg  = getattr(client, "config", {})
    key  = cfg.get("OMDB_API_KEY") or _OMDB_KEY

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(
                _OMDB_BASE,
                params={"apikey": key, "t": query, "plot": "short"},
            ) as resp:
                data = await resp.json(content_type=None)
    except Exception as e:
        return await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))

    if data.get("Response") == "False":
        erro = data.get("Error", "Não encontrado")
        if "Invalid API key" in erro:
            return await message.edit_text(tr(
                "❌ Chave OMDb inválida.\nAdicione `OMDB_API_KEY` no `config.json` "
                "(gratuita em omdbapi.com).",
                "❌ Invalid OMDb API key.\nAdd `OMDB_API_KEY` to `config.json` "
                "(free at omdbapi.com).",
            ))
        return await message.edit_text(tr(
            f"❌ Filme não encontrado: `{query}`",
            f"❌ Movie not found: `{query}`",
        ))

    titulo   = _n(data.get("Title"))
    ano      = _n(data.get("Year"))
    genero   = _n(data.get("Genre"))
    diretor  = _n(data.get("Director"))
    elenco   = _n(data.get("Actors"))
    nota     = _n(data.get("imdbRating"))
    votos    = _n(data.get("imdbVotes"))
    duracao  = _n(data.get("Runtime"))
    idioma   = _n(data.get("Language"))
    pais     = _n(data.get("Country"))
    plot     = _n(data.get("Plot"))
    tipo     = _n(data.get("Type"))
    imdb_id  = _n(data.get("imdbID"))
    poster   = data.get("Poster") if data.get("Poster") not in ("N/A", None) else None

    tipo_icon = "📺" if tipo == "series" else "🎬"
    imdb_url  = f"https://www.imdb.com/title/{imdb_id}" if imdb_id != "?" else ""

    caption = tr(
        f"{tipo_icon} **[{titulo}]({imdb_url})** ({ano})\n\n"
        f"├ 🎭 Gênero: `{genero}`\n"
        f"├ 🎬 Diretor: `{diretor}`\n"
        f"├ 🌟 Elenco: {elenco}\n"
        f"├ ⭐ IMDb: `{nota}/10` ({votos} votos)\n"
        f"├ ⏱️ Duração: `{duracao}`\n"
        f"├ 🌐 Idioma: `{idioma}` · País: `{pais}`\n"
        f"└ 📝 {plot}",

        f"{tipo_icon} **[{titulo}]({imdb_url})** ({ano})\n\n"
        f"├ 🎭 Genre: `{genero}`\n"
        f"├ 🎬 Director: `{diretor}`\n"
        f"├ 🌟 Cast: {elenco}\n"
        f"├ ⭐ IMDb: `{nota}/10` ({votos} votes)\n"
        f"├ ⏱️ Runtime: `{duracao}`\n"
        f"├ 🌐 Language: `{idioma}` · Country: `{pais}`\n"
        f"└ 📝 {plot}",
    )

    try:
        if poster:
            await message.delete()
            await client.send_photo(message.chat.id, poster, caption=caption)
        else:
            await message.edit_text(caption, disable_web_page_preview=True)
    except Exception:
        await message.edit_text(caption, disable_web_page_preview=True)

    deletar_depois(message, 60)
