"""
plugins/dev.py
Desenvolvimento: eval.

,term e ,instalar/,desinstalar foram movidos pro painel bot (/painel →
💻 Sistema → Shell, e 🔌 Plugins) — gerenciamento de infraestrutura e
plugins agora é responsabilidade do painel, não do userbot. ,eval fica
aqui porque é scripting da própria conta (usa client/message do
Pyrogram), não administração de VPS.
"""
import logging
import os
import sys
import io
import traceback
import asyncio
import contextlib
logger = logging.getLogger("AxonBot.dev")

from utils.helpers import prefixo
from utils.commands import cmd
from utils.i18n import tr

@cmd("eval")
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
        try:
            await message.delete()
            await client.send_document(message.chat.id, "eval_output.txt", caption="🐍 **Eval Output**")
        finally:
            try:
                os.remove("eval_output.txt")
            except Exception as e:
                logger.debug(f"[dev.py] ignorado: {e}")
    else:
        await message.edit_text(f"🐍 **Eval Output**\n\n```python\n{out}\n```")
