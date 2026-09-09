"""
plugins/tools/tools.py
Ferramentas: ghost, tr, voz, print, encurtar, ipinfo, clima, specs.
"""
import asyncio
import logging
import os
import re
import tempfile
import textwrap
from datetime import date as _date
from urllib.parse import quote_plus

import aiohttp

logger = logging.getLogger("AxonBot.tools")

from deep_translator import GoogleTranslator
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

from utils.commands import cmd
from utils.helpers import prefixo
from utils.i18n import get_lang, tr

_CLIMA_CODES_THUNDER = {200, 386, 389, 392, 395}
_CLIMA_CODES_RAIN    = {176, 263, 266, 281, 284, 293, 296, 299, 302, 305, 308, 311}
_CLIMA_CODES_SNOW    = {179, 182, 185, 227, 230, 314, 317, 320, 323, 326, 329,
                        332, 335, 338, 350, 353, 356, 359, 362, 365, 368, 371, 374, 377}
_CLIMA_CODES_FOG     = {143, 248, 260}


def _clima_icon(code: int) -> str:
    if code == 113:                    return "☀️"
    if code == 116:                    return "⛅"
    if code in (119, 122):             return "☁️"
    if code in _CLIMA_CODES_FOG:       return "🌫️"
    if code in _CLIMA_CODES_THUNDER:   return "⛈️"
    if code in _CLIMA_CODES_RAIN:      return "🌧️"
    if code in _CLIMA_CODES_SNOW:      return "❄️"
    return "🌡️"


@cmd("ghost")
async def cmd_ghost(client, message):
    """Envia uma mensagem que se autodestrói após N segundos."""
    p = prefixo(client)
    partes = message.text.split(None, 2)
    if len(partes) < 3:
        return await message.edit_text(tr(f"⚠️ Use: `{p}ghost [segundos] [texto]`", f"⚠️ Use: `{p}ghost [seconds] [text]`"))
    if not partes[1].isdigit():
        return await message.edit_text(tr(f"⚠️ Tempo inválido. Ex: `{p}ghost 10 Olá`", f"⚠️ Invalid time. Ex: `{p}ghost 10 Hello`"))
    tempo = min(int(partes[1]), 3600)  # máximo 1 hora
    texto = partes[2]
    await message.edit_text(tr(f"👻 **[Autodestrutiva em {tempo}s]**\n\n{texto}", f"👻 **[Self-destructing in {tempo}s]**\n\n{texto}"))
    await asyncio.sleep(tempo)
    try:
        await message.delete()
    except Exception as e:
        logger.debug(f"[tools.py] ignorado: {e}")


@cmd("tr")
async def cmd_tr(client, message):
    """Traduz uma mensagem respondida para o idioma especificado."""
    if not message.reply_to_message:
        return await message.edit_text(tr("⚠️ Responda ao texto a traduzir.", "⚠️ Reply to the text to translate."))
    partes = message.text.split(None, 1)
    alvo = partes[1].strip() if len(partes) > 1 else "pt"
    texto = message.reply_to_message.text or message.reply_to_message.caption
    if not texto:
        return await message.edit_text(tr("⚠️ Mensagem sem texto.", "⚠️ Message has no text."))
    await message.edit_text(tr(f"🌐 **Traduzindo para `{alvo}`...**", f"🌐 **Translating to `{alvo}`...**"))
    try:
        res = GoogleTranslator(source='auto', target=alvo).translate(texto)
        await message.edit_text(tr(f"🌐 **Tradução ({alvo.upper()}):**\n\n{res}", f"🌐 **Translation ({alvo.upper()}):**\n\n{res}"))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@cmd("voz")
async def cmd_voz(client, message):
    """Converte texto em áudio de voz (br, pt, en, es, ja, ru)."""
    p = prefixo(client)
    
    sotaques_map = {
        "br": ("pt", "com.br"), "pt": ("pt", "pt"),
        "en": ("en", "com"), "es": ("es", "es"),
        "ja": ("ja", "co.jp"), "ru": ("ru", "ru")
    }
    
    lang, tld = "pt", "com.br"
    texto = ""
    
    partes = message.text.split()
    if len(partes) > 1 and partes[1].lower() in sotaques_map:
        lang, tld = sotaques_map[partes[1].lower()]
        texto = " ".join(partes[2:])
    elif len(partes) > 1:
        texto = " ".join(partes[1:])
        
    if not texto and message.reply_to_message:
        texto = message.reply_to_message.text or message.reply_to_message.caption
        
    if not texto:
        return await message.edit_text(tr(f"⚠️ Use: `{p}voz [sotaque] [texto]`\nEx: `{p}voz pt Fala gajo!`", f"⚠️ Use: `{p}voice [accent] [text]`\nEx: `{p}voice en Hello friend!`"))
        
    await message.edit_text(tr("🎙️ **Gerando áudio...**", "🎙️ **Generating audio...**"))
    arquivo = os.path.join(tempfile.gettempdir(), f"voz_{message.id}.ogg")
    try:
        def gerar_tts():
            tts = gTTS(text=texto, lang=lang, tld=tld)
            tts.save(arquivo)
            
        await asyncio.to_thread(gerar_tts)
        await client.send_voice(message.chat.id, arquivo)
        os.remove(arquivo)
        await message.delete()
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))
        if os.path.exists(arquivo):
            os.remove(arquivo)


def gerar_print_img(texto, autor, arquivo):
    ft = ImageFont.truetype("Roboto-Medium.ttf", 26)
    fa = ImageFont.truetype("Roboto-Medium.ttf", 22)
    linhas = textwrap.wrap(texto, width=38)
    altura = 100 + (len(linhas) * 35)
    img = Image.new('RGBA', (600, altura), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([(10, 10), (590, altura - 10)], radius=15, fill=(33, 45, 59))
    d.text((30, 25), autor, fill=(100, 181, 239), font=fa)
    y = 65
    for linha in linhas:
        d.text((30, y), linha, fill=(255, 255, 255), font=ft)
        y += 35
    img.save(arquivo)

@cmd("print")
async def cmd_print(client, message):
    """Gera imagem estilizada de uma mensagem respondida."""
    if not message.reply_to_message:
        return await message.edit_text(tr("⚠️ Responda à mensagem para gerar o print.", "⚠️ Reply to a message to generate the screenshot."))
    await message.edit_text(tr("📸 **Gerando print...**", "📸 **Generating screenshot...**"))
    arquivo = os.path.join(tempfile.gettempdir(), f"print_{message.id}.png")
    try:
        texto = message.reply_to_message.text or message.reply_to_message.caption or tr("[Mídia sem texto]", "[Media without text]")
        autor = tr("Usuário", "User")
        if message.reply_to_message.from_user:
            autor = message.reply_to_message.from_user.first_name
        if not os.path.exists("Roboto-Medium.ttf"):
            async with aiohttp.ClientSession() as session:
                async with session.get("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Medium.ttf") as r:
                    conteudo = await r.read()
            with open("Roboto-Medium.ttf", "wb") as f:
                f.write(conteudo)
                
        await asyncio.to_thread(gerar_print_img, texto, autor, arquivo)
        await client.send_document(message.chat.id, arquivo, file_name="Print.png")
        os.remove(arquivo)
        await message.delete()
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))
        if os.path.exists(arquivo):
            os.remove(arquivo)


@cmd("encurtar")
async def cmd_encurtar(client, message):
    """Encurta uma URL usando o TinyURL."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}encurtar [URL]`", f"⚠️ Use: `{p}shorten [URL]`"))
    url = partes[1].strip()
    await message.edit_text(tr("🔗 **Encurtando...**", "🔗 **Shortening...**"))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://tinyurl.com/api-create.php?url={quote_plus(url)}") as r:
                texto_url = await r.text()
        await message.edit_text(tr(f"🔗 **Encurtado:**\n`{texto_url}`", f"🔗 **Shortened:**\n`{texto_url}`"))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@cmd("ipinfo")
async def cmd_ipinfo(client, message):
    """Exibe informações sobre um endereço IP."""
    partes = message.text.split(None, 1)
    ip = partes[1].strip() if len(partes) > 1 else ""
    await message.edit_text(tr("🌐 **Buscando dados do IP...**", "🌐 **Fetching IP data...**"))
    try:
        url = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as res:
                r = await res.json()
        await message.edit_text(tr(
            f"🌐 **IP Info** (`{r.get('ip', 'N/A')}`)\n"
            f"├ 🏙️ **Cidade:** `{r.get('city', 'N/A')}`\n"
            f"├ 🗺️ **Região:** `{r.get('region', 'N/A')}`\n"
            f"├ 🌍 **País:** `{r.get('country', 'N/A')}`\n"
            f"├ 🏢 **Org:** `{r.get('org', 'N/A')}`\n"
            f"└ ⏰ **Fuso:** `{r.get('timezone', 'N/A')}`",
            f"🌐 **IP Info** (`{r.get('ip', 'N/A')}`)\n"
            f"├ 🏙️ **City:** `{r.get('city', 'N/A')}`\n"
            f"├ 🗺️ **Region:** `{r.get('region', 'N/A')}`\n"
            f"├ 🌍 **Country:** `{r.get('country', 'N/A')}`\n"
            f"├ 🏢 **Org:** `{r.get('org', 'N/A')}`\n"
            f"└ ⏰ **Timezone:** `{r.get('timezone', 'N/A')}`"
        ))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@cmd("clima")
async def cmd_clima(client, message):
    """Clima atual e previsão de 3 dias para uma cidade."""
    p      = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(
            f"⚠️ Use: `{p}clima [cidade]`\nEx: `{p}clima São Paulo`",
            f"⚠️ Use: `{p}weather [city]`\nEx: `{p}weather New York`",
        ))
    cidade = partes[1].strip()
    await message.edit_text(tr(
        f"🌤️ **Buscando clima de** `{cidade}`**...**",
        f"🌤️ **Fetching weather for** `{cidade}`**...**",
    ))

    lang_param = "en" if get_lang() == "en" else "pt"
    cidade_url = cidade.replace(" ", "+")
    url        = f"https://wttr.in/{cidade_url}?format=j1&lang={lang_param}"

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(
            headers={"User-Agent": "curl/7.68.0"}, timeout=timeout
        ) as session:
            async with session.get(url) as r:
                if r.status != 200:
                    return await message.edit_text(tr(
                        "❌ Localidade não encontrada.",
                        "❌ Location not found.",
                    ))
                data = await r.json(content_type=None)
    except asyncio.TimeoutError:
        return await message.edit_text(tr(
            "❌ Tempo esgotado ao consultar o serviço.",
            "❌ Request timed out.",
        ))
    except Exception as e:
        return await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))

    if not data.get("current_condition") or not data.get("nearest_area"):
        return await message.edit_text(tr(
            "❌ Localidade não encontrada.",
            "❌ Location not found.",
        ))

    try:
        current   = data["current_condition"][0]
        area_info = data["nearest_area"][0]
        forecasts = data["weather"]

        area    = area_info["areaName"][0]["value"]
        country = area_info["country"][0]["value"]
        loc_str = f"{area}, {country}"

        temp_c     = current["temp_C"]
        feels_c    = current["FeelsLikeC"]
        humidity   = current["humidity"]
        wind_kmph  = current["windspeedKmph"]
        wind_dir   = current["winddir16Point"]
        uv_index   = current.get("uvIndex", "?")
        visibility = current["visibility"]

        desc_key  = "lang_pt" if lang_param == "pt" else "weatherDesc"
        desc_list = current.get(desc_key) or current.get("weatherDesc", [])
        cond_desc = desc_list[0]["value"] if desc_list else "?"

        cond_icon = _clima_icon(int(current.get("weatherCode", 0)))

        # Previsão dos próximos 3 dias
        _DAY_PT = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
        _DAY_EN = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        day_names = _DAY_PT if lang_param == "pt" else _DAY_EN

        forecast_lines = []
        for day in forecasts[:3]:
            d       = _date.fromisoformat(day["date"])
            dname   = day_names[d.isoweekday() % 7]   # isoweekday: Mon=1..Sun=7 → %7: Sun=0
            max_c   = day["maxtempC"]
            min_c   = day["mintempC"]
            slot    = day.get("hourly", [{}])
            midday  = slot[4] if len(slot) > 4 else (slot[-1] if slot else {})
            d_list  = midday.get(desc_key) or midday.get("weatherDesc", [])
            d_desc  = d_list[0]["value"] if d_list else "?"
            forecast_lines.append(f"  {dname}  {min_c}° ~ {max_c}°C  —  {d_desc}")

        forecast_block = "\n".join(forecast_lines) or "N/A"

        txt = tr(
            f"{cond_icon} **{loc_str}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"├ 🌡️ **Temp.:** `{temp_c}°C` _(sensação `{feels_c}°C`)_\n"
            f"├ 💧 **Umidade:** `{humidity}%`\n"
            f"├ 💨 **Vento:** `{wind_kmph} km/h` {wind_dir}\n"
            f"├ 👁️ **Visibilidade:** `{visibility} km`\n"
            f"├ ☀️ **Índice UV:** `{uv_index}`\n"
            f"└ 🌤️ **Condição:** {cond_desc}\n\n"
            f"📅 **Previsão (3 dias)**\n"
            f"```\n{forecast_block}\n```",
            f"{cond_icon} **{loc_str}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"├ 🌡️ **Temp.:** `{temp_c}°C` _(feels like `{feels_c}°C`)_\n"
            f"├ 💧 **Humidity:** `{humidity}%`\n"
            f"├ 💨 **Wind:** `{wind_kmph} km/h` {wind_dir}\n"
            f"├ 👁️ **Visibility:** `{visibility} km`\n"
            f"├ ☀️ **UV Index:** `{uv_index}`\n"
            f"└ 🌤️ **Condition:** {cond_desc}\n\n"
            f"📅 **Forecast (3 days)**\n"
            f"```\n{forecast_block}\n```",
        )
        await message.edit_text(txt, disable_web_page_preview=True)

    except (KeyError, IndexError, ValueError) as e:
        await message.edit_text(tr(
            f"❌ Erro ao processar os dados do clima: `{e}`",
            f"❌ Error parsing weather data: `{e}`",
        ))


@cmd("specs")
async def cmd_specs(client, message):
    """Especificações técnicas de celular via GSMArena."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}specs [modelo do celular]`", f"⚠️ Use: `{p}specs [phone model]`"))
    modelo = partes[1].strip()
    await message.edit_text(tr(f"📱 **Buscando specs de `{modelo}`...**", f"📱 **Fetching specs for `{modelo}`...**"))
    try:
        termo = modelo.replace(" ", "+")
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14)"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"https://www.gsmarena.com/results.php3?sQuickSearch=yes&sName={termo}") as r:
                html_busca = await r.text()
        links = re.findall(r'href="([a-z0-9_]+-\d+\.php)"', html_busca)
        if links:
            url_ficha = f"https://www.gsmarena.com/{links[0]}"
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url_ficha) as r2:
                    html = await r2.text()
            nome = re.search(r'<h1 class="specs-phone-name-title">(.*?)</h1>', html)
            proc = re.search(r'data-spec="chipset">(.*?)</td>', html, re.DOTALL)
            ram = re.search(r'data-spec="internalmemory">(.*?)</td>', html, re.DOTALL)
            bat = re.search(r'data-spec="batdescription1">(.*?)</td>', html, re.DOTALL)
            disp = re.search(r'data-spec="displaysize">(.*?)</td>', html, re.DOTALL)
            cam = re.search(r'data-spec="cam1modules">(.*?)</td>', html, re.DOTALL)
            limpar = lambda t: re.sub('<.*?>', '', t).strip() if t else "N/A"
            await message.edit_text(
                f"📱 **{nome.group(1).strip() if nome else modelo.upper()}**\n"
                f"├ ⚙️ **CPU:** `{limpar(proc.group(1)) if proc else 'N/A'}`\n"
                f"├ 💾 **RAM:** `{limpar(ram.group(1)) if ram else 'N/A'}`\n"
                f"├ 📺 **Tela:** `{limpar(disp.group(1)) if disp else 'N/A'}`\n"
                f"├ 📷 **Câmera:** `{limpar(cam.group(1))[:60] if cam else 'N/A'}`\n"
                f"└ 🔋 **Bateria:** `{limpar(bat.group(1))[:60] if bat else 'N/A'}`\n\n"
                f"🔗 Ficha completa no GSMArena"
            )
        else:
            await message.edit_text(
                f"📱 **{modelo.upper()}**\n\n"
                f"⚠️ Modelo não encontrado no GSMArena.\n"
                f"🔗 [Buscar no Google](https://www.google.com/search?q={termo}+specs)"
            )
    except Exception as e:
        await message.edit_text(f"❌ Erro: `{e}`")
