"""
plugins/dev.py
Desenvolvimento e gerenciamento: eval, term, install, uninstall
"""
import os
import sys
import io
import traceback
import asyncio
import contextlib
import aiohttp

from pyrogram import filters, Client
from utils.helpers import cmd_filter, prefixo, reiniciar_processo
from utils.i18n import tr

@Client.on_message(cmd_filter("term") & filters.me)
async def cmd_term(client, message):
    """Executa comandos de terminal/shell do sistema."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}term [comando]`", f"⚠️ Use: `{p}term [command]`"))
    cmd = partes[1]
    await message.edit_text(tr("🖥️ **Executando...**", "🖥️ **Executing...**"))
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        res = (stdout.decode() + stderr.decode()).strip() or "✅ Concluído (sem saída)."
        
        if len(res) > 4000:
            with open("term_output.txt", "w", encoding="utf-8") as f:
                f.write(res)
            await message.delete()
            await client.send_document(message.chat.id, "term_output.txt", caption=f"💻 `$ {cmd}`")
            os.remove("term_output.txt")
        else:
            await message.edit_text(f"💻 `$ {cmd}`\n\n```text\n{res}\n```")
    except Exception as e:
        await message.edit_text(f"❌ Erro: `{e}`")

@Client.on_message(cmd_filter("eval") & filters.me)
async def cmd_eval(client, message):
    """Executa código Python dinamicamente."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}eval [código]`", f"⚠️ Use: `{p}eval [code]`"))
    code = partes[1]
    
    env = {
        "client": client, "app": client, "message": message, "m": message,
        "asyncio": asyncio, "os": os, "sys": sys
    }
    
    # Cria uma função async wrapping the code
    exec_code = "async def _aexec():\n" + "".join(f"    {l}\n" for l in code.split("\n"))
    
    stdout = io.StringIO()
    await message.edit_text(tr("⚙️ **Avaliando código...**", "⚙️ **Evaluating code...**"))
    try:
        exec(exec_code, env)
        with contextlib.redirect_stdout(stdout):
            await env["_aexec"]()
        out = stdout.getvalue().strip() or "✅ Sucesso (sem saída)."
    except Exception:
        out = traceback.format_exc()
        
    if len(out) > 4000:
        with open("eval_output.txt", "w", encoding="utf-8") as f:
            f.write(out)
        await message.delete()
        await client.send_document(message.chat.id, "eval_output.txt", caption="🐍 **Eval Output**")
        os.remove("eval_output.txt")
    else:
        await message.edit_text(f"🐍 **Eval Output**\n\n```python\n{out}\n```")

@Client.on_message(cmd_filter("instalar") & filters.me)
async def cmd_install(client, message):
    """Baixa e instala um novo plugin via URL."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}instalar [url do .py]`", f"⚠️ Use: `{p}install [url to .py]`"))
    url = partes[1].strip()
    filename = url.split("/")[-1] if url.endswith(".py") else "plugin_baixado.py"
    filepath = os.path.join("plugins", filename)
    
    msg = await message.edit_text(tr("📥 **Baixando plugin...**", "📥 **Downloading plugin...**"))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(await r.read())
        await msg.edit_text(tr(f"✅ **Plugin `{filename}` instalado!**\nReiniciando o bot...", f"✅ **Plugin `{filename}` installed!**\nRestarting bot..."))
        await asyncio.sleep(2)
        reiniciar_processo()
    except Exception as e:
        await msg.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))

@Client.on_message(cmd_filter("desinstalar") & filters.me)
async def cmd_uninstall(client, message):
    """Desinstala um plugin existente."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}desinstalar [nome]`", f"⚠️ Use: `{p}uninstall [filename]`"))
    filename = partes[1].strip() if partes[1].endswith(".py") else f"{partes[1].strip()}.py"
    filepath = os.path.join("plugins", filename)
    if not os.path.exists(filepath):
        return await message.edit_text(tr(f"❌ Plugin `{filename}` não encontrado.", f"❌ Plugin `{filename}` not found."))
    if filename in ["system.py", "menu.py", "dev.py", "tools.py", "moderation.py", "account.py"]:
        return await message.edit_text(tr("⚠️ Não é recomendado apagar plugins principais do sistema.", "⚠️ Not recommended to delete core plugins."))
    os.remove(filepath)
    await message.edit_text(tr(f"🗑️ **Plugin `{filename}` apagado!**\nReiniciando o bot...", f"🗑️ **Plugin `{filename}` deleted!**\nRestarting bot..."))
    await asyncio.sleep(2)
    reiniciar_processo()