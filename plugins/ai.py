"""
plugins/ai.py
Integração com Google Gemini (Inteligência Artificial)
"""
import asyncio
from pyrogram import filters, Client
from utils.helpers import cmd_filter, tr

try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


_MODEL_CACHE: dict[str, str] = {}


def _criar_cliente(api_key: str):
    return genai.Client(api_key=api_key)


def obter_modelo_otimizado(api_key: str) -> str:
    """Descobre o melhor modelo flash disponível para a chave (resultado cacheado)."""
    if api_key in _MODEL_CACHE:
        return _MODEL_CACHE[api_key]
    client = _criar_cliente(api_key)
    try:
        for m in client.models.list():
            name = m.name.replace("models/", "")
            if "flash" in name.lower():
                _MODEL_CACHE[api_key] = name
                return name
    except Exception:
        pass
    _MODEL_CACHE[api_key] = "gemini-2.0-flash"
    return _MODEL_CACHE[api_key]


@Client.on_message(cmd_filter("perguntar") & filters.me)
async def cmd_ask(client, message):
    """Faz uma pergunta para a IA (Gemini)."""
    if not HAS_GEMINI:
        return await message.edit_text(tr("❌ Biblioteca `google-genai` não instalada.", "❌ Library `google-genai` not installed."))

    api_key = getattr(client, "config", {}).get("GEMINI_API_KEY")
    if not api_key:
        return await message.edit_text(tr("❌ Chave `GEMINI_API_KEY` não configurada no `config.json`.", "❌ `GEMINI_API_KEY` not configured in `config.json`."))

    partes = message.text.split(None, 1)
    pergunta = partes[1].strip() if len(partes) > 1 else ""
    if message.reply_to_message and not pergunta:
        pergunta = message.reply_to_message.text or message.reply_to_message.caption

    if not pergunta:
        return await message.edit_text(tr("⚠️ Use: `,perguntar [pergunta]` ou responda a algo.", "⚠️ Use: `,ask [question]` or reply to something."))

    await message.edit_text(tr("🧠 **Processando consulta...**", "🧠 **Processing query...**"))
    try:
        def run_ai():
            modelo = obter_modelo_otimizado(api_key)
            ai = _criar_cliente(api_key)
            return ai.models.generate_content(model=modelo, contents=pergunta).text

        resposta = await asyncio.to_thread(run_ai)
        await message.edit_text(tr(f"🧠 **Gemini IA:**\n\n{resposta}", f"🧠 **Gemini AI:**\n\n{resposta}"))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro na IA: `{e}`", f"❌ AI Error: `{e}`"))


@Client.on_message(cmd_filter("resumir") & filters.me)
async def cmd_resumir(client, message):
    """Lê as últimas 50 mensagens do chat e pede um resumo em tópicos para a IA."""
    api_key = getattr(client, "config", {}).get("GEMINI_API_KEY")
    if not HAS_GEMINI or not api_key:
        return await message.edit_text(tr("❌ IA não configurada (faltando chave ou biblioteca).", "❌ AI not configured (missing key or library)."))

    await message.edit_text(tr("📚 **Analisando últimas mensagens...**", "📚 **Analyzing recent messages...**"))
    try:
        msgs = []
        async for m in client.get_chat_history(message.chat.id, limit=50):
            if m.text or m.caption:
                autor = m.from_user.first_name if m.from_user else "Usuário"
                msgs.append(f"{autor}: {m.text or m.caption}")

        if not msgs:
            return await message.edit_text(tr("⚠️ Poucas mensagens para resumir.", "⚠️ Not enough messages to summarize."))

        conversa = "\n".join(reversed(msgs))
        prompt = tr(
            "Aqui estão as últimas mensagens de um chat. Crie um resumo conciso e em bullet points sobre os principais tópicos discutidos:\n\n",
            "Here are the last messages of a chat. Create a concise bullet-point summary of the main topics discussed:\n\n"
        ) + conversa

        def run_summary():
            modelo = obter_modelo_otimizado(api_key)
            ai = _criar_cliente(api_key)
            return ai.models.generate_content(model=modelo, contents=prompt).text

        resposta = await asyncio.to_thread(run_summary)
        await message.edit_text(tr(f"📚 **Resumo Analítico:**\n\n{resposta}", f"📚 **Analytical Summary:**\n\n{resposta}"))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro ao resumir: `{e}`", f"❌ Error summarizing: `{e}`"))
