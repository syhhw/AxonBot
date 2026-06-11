"""
plugins/tools.py
Ferramentas e diversão: hack, type, ghost, fake, tr, voz, print, encurtar, ipinfo, clima, specs, clone, reverter
"""
import os
import re
import asyncio
import random
import textwrap
import aiohttp
from datetime import date as _date

from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters, enums, Client
from deep_translator import GoogleTranslator
from utils.helpers import cmd_filter, prefixo, resolver_alvo, carregar, salvar
from utils.i18n import tr, get_lang


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


@Client.on_message(cmd_filter("hack") & filters.me)
async def cmd_hack(client, message):
    """Simulador de hack interativo com dados reais do alvo."""

    # ── Dados reais do alvo ───────────────────────────────────────────────────
    if message.reply_to_message and message.reply_to_message.from_user:
        u        = message.reply_to_message.from_user
        nome     = u.first_name or "User"
        uid      = u.id
        user_tag = f" • @{u.username}" if u.username else ""
        tem_foto = u.photo is not None
    else:
        nome     = "SISTEMA"
        uid      = random.randint(100_000_000, 999_999_999)
        user_tag = ""
        tem_foto = False

    # ── Dados falsos gerados por execução ─────────────────────────────────────
    ip       = ".".join(str(random.randint(1, 254)) for _ in range(4))
    mac      = ":".join(f"{random.randint(0, 255):02X}" for _ in range(6))
    token    = "".join(random.choices("0123456789ABCDEF", k=16))
    senha    = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789!@#", k=random.randint(9, 14)))
    dev      = random.choice(["Samsung Galaxy S25", "iPhone 16 Pro", "Pixel 9 Pro", "Xiaomi 14 Ultra", "OnePlus 13"])
    osv      = random.choice(["Android 14", "iOS 18.3", "Android 15", "iOS 17.6"])
    isp      = random.choice(["Claro BR", "Vivo", "TIM Brasil", "NET Virtua", "Oi Fibra"])
    loc      = random.choice(["São Paulo, BR", "Rio de Janeiro, BR", "Manaus, BR", "Belo Horizonte, BR", "Fortaleza, BR", "Curitiba, BR"])
    lat      = f"{random.uniform(-33.0, 5.0):.6f}"
    lon      = f"{random.uniform(-73.0, -34.0):.6f}"
    ports    = random.choice(["443, 80, 8443", "443, 8080, 22", "443, 993, 3306"])
    pkts     = random.randint(3_000, 12_000)
    tentativa = random.randint(200, 700)
    msgs     = random.randint(1_200, 45_000)
    apagadas = random.randint(30, 500)
    ctcts    = random.randint(50, 800)
    media    = random.randint(200, 5_000)
    salvos   = random.randint(10, 300)
    chamadas = random.randint(50, 400)

    pt = get_lang() != "en"

    terminal: list[str] = []

    async def frame(bar_n: int, phase: str, new_line: str = "", sleep: float = 1.8):
        if new_line:
            terminal.append(new_line)
        b   = "▰" * bar_n + "▱" * (10 - bar_n)
        log = "\n".join(terminal[-7:])
        text = (
            f"{'💀 **ATAQUE EM ANDAMENTO**' if pt else '💀 **ATTACK IN PROGRESS**'}\n"
            f"{'🎯 Alvo' if pt else '🎯 Target'}: **{nome}** (`{uid}`){user_tag}\n\n"
            f"**{phase}**\n"
            f"`[{b}]` **{bar_n * 10}%**\n\n"
            f"```\n{log}\n```"
        )
        try:
            await message.edit_text(text)
        except Exception:
            pass
        await asyncio.sleep(sleep)

    # ── FASE 1 — RECONHECIMENTO ───────────────────────────────────────────────
    p1 = f"🔍 {'FASE 1 — RECONHECIMENTO' if pt else 'PHASE 1 — RECONNAISSANCE'}"
    await frame(1, p1, f"[*] {'Iniciando varredura de rede...' if pt else 'Starting network scan...'}", 1.8)
    await frame(1, p1, f"[*] {'Localizando alvo na rede Telegram...' if pt else 'Locating target on Telegram network...'}", 2.0)
    await frame(2, p1, f"[+] IP {'localizado' if pt else 'found'}: {ip}", 1.8)
    await frame(2, p1, f"[+] MAC: {mac}", 1.5)
    await frame(2, p1, f"[+] {'Provedor' if pt else 'ISP'}: {isp}", 1.6)
    await frame(3, p1, f"[+] {'Dispositivo' if pt else 'Device'}: {dev} ({osv})", 1.8)
    await frame(3, p1, f"[+] {'Localização' if pt else 'Location'}: {loc}", 1.6)
    await frame(3, p1, f"[+] GPS: {lat}, {lon}", 2.0)

    # ── FASE 2 — INFILTRAÇÃO ──────────────────────────────────────────────────
    p2 = f"📡 {'FASE 2 — INFILTRAÇÃO' if pt else 'PHASE 2 — INFILTRATION'}"
    await frame(4, p2, f"[*] {'Portas abertas' if pt else 'Open ports'}: {ports}", 1.8)
    await frame(4, p2, f"[*] {'Estabelecendo canal encoberto...' if pt else 'Establishing covert channel...'}", 2.2)
    await frame(5, p2, f"[*] {'Interceptando tráfego MTProto...' if pt else 'Intercepting MTProto traffic...'}", 2.0)
    await frame(5, p2, f"[i] {'Pacotes capturados' if pt else 'Packets captured'}: {pkts:,}", 1.6)
    await frame(5, p2, f"[*] {'Descriptografando AES-256...' if pt else 'Decrypting AES-256...'}", 2.2)
    await frame(6, p2, f"[*] {'Força bruta na senha: tentativa' if pt else 'Brute force on password: attempt'} {tentativa}/1000", 2.5)
    await frame(6, p2, f"[+] {'Senha encontrada' if pt else 'Password cracked'}: {senha}", 2.0)
    await frame(6, p2, f"[+] {'Token de sessão extraído' if pt else 'Session token extracted'}: {token}", 1.8)
    await frame(7, p2, f"[+] 2FA {'contornado' if pt else 'bypassed'} ✓", 1.6)
    await frame(7, p2, f"[+] {'Sessão hijackada com sucesso' if pt else 'Session successfully hijacked'} ✓", 2.0)

    # ── FASE 3 — EXTRAÇÃO ─────────────────────────────────────────────────────
    p3 = f"📂 {'FASE 3 — EXTRAÇÃO DE DADOS' if pt else 'PHASE 3 — DATA EXTRACTION'}"
    await frame(7, p3, f"[*] {'Espelhando conversas privadas...' if pt else 'Mirroring private conversations...'}", 2.2)
    await frame(8, p3, f"[+] {'Mensagens baixadas' if pt else 'Messages downloaded'}: {msgs:,} ✓", 1.8)
    await frame(8, p3, f"[+] {'Mensagens apagadas recuperadas' if pt else 'Deleted messages recovered'}: {apagadas} ✓", 2.2)
    await frame(8, p3, f"[+] {'Salvos do Telegram' if pt else 'Saved messages'}: {salvos} | {'Chamadas' if pt else 'Calls'}: {chamadas} ✓", 1.8)
    if tem_foto:
        await frame(9, p3, f"[+] {'Fotos de perfil capturadas' if pt else 'Profile photos captured'} ✓", 1.6)
    await frame(9, p3, f"[+] {'Mídias' if pt else 'Media files'}: {media:,} | {'Contatos' if pt else 'Contacts'}: {ctcts} ✓", 1.8)
    await frame(9, p3, f"[!] {'Ativando câmera traseira...' if pt else 'Activating rear camera...'} ✓", 2.5)
    await frame(9, p3, f"[!] {'Ativando microfone...' if pt else 'Activating microphone...'} ✓", 2.5)

    # ── FASE 4 — PAYLOAD ──────────────────────────────────────────────────────
    p4 = f"☢️ {'FASE 4 — PAYLOAD' if pt else 'PHASE 4 — PAYLOAD'}"
    await frame(9,  p4, f"[*] {'Instalando módulo de espionagem...' if pt else 'Installing spyware module...'}", 2.2)
    await frame(10, p4, f"[*] {'Configurando backdoor persistente...' if pt else 'Configuring persistent backdoor...'}", 2.2)
    await frame(10, p4, f"[+] {'Acesso root obtido' if pt else 'Root access granted'} ✓", 1.8)
    await frame(10, p4, f"[+] {'Ocultando rastros do ataque...' if pt else 'Erasing attack traces...'} ✓", 2.0)
    await frame(10, p4, f"[+] {'Upload para servidor remoto: 100%' if pt else 'Upload to remote server: 100%'} ✓", 2.0)

    # ── TELA FINAL ────────────────────────────────────────────────────────────
    if pt:
        final = (
            f"💀 **HACK CONCLUÍDO COM SUCESSO** 💀\n\n"
            f"🎯 **Alvo:** **{nome}** (`{uid}`){user_tag}\n"
            f"🌐 **IP:** `{ip}` — {isp} — {loc}\n"
            f"📍 **GPS:** `{lat}, {lon}`\n"
            f"📱 **Device:** `{dev}` ({osv})\n"
            f"🔑 **Token:** `{token}`\n"
            f"🔐 **Senha:** `{senha}`\n\n"
            f"📊 **Dados extraídos:**\n"
            f"  💬 Mensagens: `{msgs:,}` (+`{apagadas}` apagadas)\n"
            f"  📸 Mídias: `{media:,}`\n"
            f"  👥 Contatos: `{ctcts}`\n"
            f"  📞 Chamadas: `{chamadas}`\n"
            f"  📌 Salvos: `{salvos}`\n"
            f"  🎥 Câmera + 🎙️ Microfone: **ativos**\n\n"
            f"💸 **ATENÇÃO:** Envie **10 Bitcoin** em 24h ou tudo será vazado:\n"
            f"`bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh`"
        )
    else:
        final = (
            f"💀 **HACK SUCCESSFULLY COMPLETED** 💀\n\n"
            f"🎯 **Target:** **{nome}** (`{uid}`){user_tag}\n"
            f"🌐 **IP:** `{ip}` — {isp} — {loc}\n"
            f"📍 **GPS:** `{lat}, {lon}`\n"
            f"📱 **Device:** `{dev}` ({osv})\n"
            f"🔑 **Token:** `{token}`\n"
            f"🔐 **Password:** `{senha}`\n\n"
            f"📊 **Extracted data:**\n"
            f"  💬 Messages: `{msgs:,}` (+`{apagadas}` deleted)\n"
            f"  📸 Media: `{media:,}`\n"
            f"  👥 Contacts: `{ctcts}`\n"
            f"  📞 Calls: `{chamadas}`\n"
            f"  📌 Saved: `{salvos}`\n"
            f"  🎥 Camera + 🎙️ Mic: **active**\n\n"
            f"💸 **WARNING:** Send **10 Bitcoin** in 24h or everything leaks:\n"
            f"`bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh`"
        )
    try:
        await message.edit_text(final)
    except Exception:
        pass


@Client.on_message(cmd_filter("type") & filters.me)
async def cmd_type(client, message):
    """Simula digitação letra por letra."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}type [texto]`", f"⚠️ Use: `{p}type [text]`"))
    texto = partes[1]
    digitado = ""
    for ch in texto:
        digitado += ch
        try:
            await message.edit_text(f"{digitado}▌")
            await asyncio.sleep(random.uniform(0.04, 0.15))
        except Exception:
            pass
    await message.edit_text(digitado)


@Client.on_message(cmd_filter("ghost") & filters.me)
async def cmd_ghost(client, message):
    """Envia uma mensagem que se autodestrói após N segundos."""
    p = prefixo(client)
    partes = message.text.split(None, 2)
    if len(partes) < 3:
        return await message.edit_text(tr(f"⚠️ Use: `{p}ghost [segundos] [texto]`", f"⚠️ Use: `{p}ghost [seconds] [text]`"))
    if not partes[1].isdigit():
        return await message.edit_text(tr(f"⚠️ Tempo inválido. Ex: `{p}ghost 10 Olá`", f"⚠️ Invalid time. Ex: `{p}ghost 10 Hello`"))
    tempo = int(partes[1])
    texto = partes[2]
    await message.edit_text(tr(f"👻 **[Autodestrutiva em {tempo}s]**\n\n{texto}", f"👻 **[Self-destructing in {tempo}s]**\n\n{texto}"))
    await asyncio.sleep(tempo)
    try:
        await message.delete()
    except Exception:
        pass


@Client.on_message(cmd_filter("fake") & filters.me)
async def cmd_fake(client, message):
    """Simula ação de digitação, gravação de áudio ou vídeo."""
    p = prefixo(client)
    partes = message.text.split(None, 1)
    if len(partes) < 2:
        return await message.edit_text(tr(f"⚠️ Use: `{p}fake [audio|video|typing]`", f"⚠️ Use: `{p}fake [audio|video|typing]`"))
    tipo = partes[1].strip().lower()
    try:
        await message.delete()
    except Exception:
        pass
    if tipo == "audio":
        acao = enums.ChatAction.RECORD_AUDIO
    elif tipo == "video":
        acao = enums.ChatAction.RECORD_VIDEO
    else:
        acao = enums.ChatAction.TYPING
    for _ in range(4):
        try:
            await client.send_chat_action(message.chat.id, acao)
            await asyncio.sleep(5)
        except Exception:
            break


@Client.on_message(cmd_filter("tr") & filters.me)
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


@Client.on_message(cmd_filter("voz") & filters.me)
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
    arquivo = "voz_temp.ogg"
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

@Client.on_message(cmd_filter("print") & filters.me)
async def cmd_print(client, message):
    """Gera imagem estilizada de uma mensagem respondida."""
    if not message.reply_to_message:
        return await message.edit_text(tr("⚠️ Responda à mensagem para gerar o print.", "⚠️ Reply to a message to generate the screenshot."))
    await message.edit_text(tr("📸 **Gerando print...**", "📸 **Generating screenshot...**"))
    arquivo = "print_temp.png"
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


@Client.on_message(cmd_filter("encurtar") & filters.me)
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
            async with session.get(f"https://tinyurl.com/api-create.php?url={url}") as r:
                texto_url = await r.text()
        await message.edit_text(tr(f"🔗 **Encurtado:**\n`{texto_url}`", f"🔗 **Shortened:**\n`{texto_url}`"))
    except Exception as e:
        await message.edit_text(tr(f"❌ Erro: `{e}`", f"❌ Error: `{e}`"))


@Client.on_message(cmd_filter("ipinfo") & filters.me)
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


@Client.on_message(cmd_filter("clima") & filters.me)
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


@Client.on_message(cmd_filter("specs") & filters.me)
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


@Client.on_message(cmd_filter("clone") & filters.me)
async def cmd_clone(client, message):
    """Clona nome, bio e foto de perfil de um usuário."""
    user, _, _ = await resolver_alvo(client, message)
    if not user:
        return await message.edit_text(tr(
            f"⚠️ Responda a alguém ou use `{prefixo(client)}clone @user`",
            f"⚠️ Reply to someone or use `{prefixo(client)}clone @user`"
        ))

    msg = await message.edit_text(tr("🎭 **Iniciando clonagem...**", "🎭 **Starting clone...**"))

    # Salva estado original apenas na primeira clonagem
    backup = carregar("clone_backup.json", {})
    if not backup.get("cloned"):
        me      = await client.get_me()
        me_full = await client.get_chat("me")

        # Registra todas as fotos JÁ existentes antes de clonar
        fotos_antes = []
        try:
            async for p in client.get_profile_photos("me", limit=50):
                fotos_antes.append(p.file_unique_id)
        except Exception:
            pass

        backup = {
            "cloned":             True,
            "first_name":         me.first_name or "",
            "last_name":          me.last_name  or "",
            "bio":                me_full.bio   or "",
            "fotos_antes_clone":  fotos_antes,   # UIDs das fotos que existiam antes
        }
        salvar("clone_backup.json", backup)

    target      = await client.get_users(user.id)
    target_full = await client.get_chat(user.id)
    first = target.first_name or ""
    last  = target.last_name  or ""
    bio   = target_full.bio[:70] if target_full.bio else ""

    try:
        await client.update_profile(first_name=first, last_name=last, bio=bio)
    except Exception as e:
        return await msg.edit_text(tr(
            f"❌ Erro ao atualizar perfil: `{e}`",
            f"❌ Error updating profile: `{e}`"
        ))

    if target.photo:
        await msg.edit_text(tr("🎭 **Baixando foto de perfil...**", "🎭 **Downloading profile photo...**"))
        photo_path = None

        # Tentativa 1: foto em alta qualidade via get_profile_photos
        try:
            photos = [p async for p in client.get_profile_photos(user.id, limit=1)]
            if photos:
                photo_path = await client.download_media(photos[0].file_id)
        except Exception:
            pass

        # Tentativa 2: thumbnail sempre acessível via ChatPhoto
        if not photo_path:
            try:
                photo_path = await client.download_media(target.photo.big_file_id)
            except Exception:
                pass

        if photo_path:
            try:
                await client.set_profile_photo(photo=photo_path)

                # Garante visibilidade pública
                from pyrogram import raw as _raw
                await client.invoke(
                    _raw.functions.account.SetPrivacy(
                        key=_raw.types.InputPrivacyKeyProfilePhoto(),
                        rules=[_raw.types.InputPrivacyValueAllowAll()],
                    )
                )
            except Exception as e:
                await msg.edit_text(tr(
                    f"⚠️ Nome/bio clonados, mas erro na foto: `{e}`",
                    f"⚠️ Name/bio cloned, but photo error: `{e}`"
                ))
                salvar("clone_backup.json", {})
                return
            finally:
                try:
                    os.remove(photo_path)
                except Exception:
                    pass

    await msg.edit_text(tr(
        f"✅ **Clone de `{first}` ativado!**\nUse `{prefixo(client)}reverter` para voltar ao normal.",
        f"✅ **Cloned `{first}`!**\nUse `{prefixo(client)}revert` to restore original profile."
    ))


@Client.on_message(cmd_filter("reverter") & filters.me)
async def cmd_reverter(client, message):
    """Restaura o perfil original após um clone."""
    backup = carregar("clone_backup.json", {})
    if not backup.get("cloned"):
        return await message.edit_text(tr("⚠️ Você não está clonando ninguém no momento.", "⚠️ You are not cloning anyone right now."))

    msg = await message.edit_text(tr("🔄 **Revertendo para o perfil original...**", "🔄 **Reverting to original profile...**"))

    # Restaura nome e bio
    try:
        await client.update_profile(
            first_name=backup.get("first_name", ""),
            last_name=backup.get("last_name",  ""),
            bio=backup.get("bio",              "")
        )
    except Exception as e:
        await msg.edit_text(tr(f"⚠️ Erro ao restaurar nome/bio: `{e}`", f"⚠️ Error restoring name/bio: `{e}`"))

    # Deleta fotos adicionadas pelo clone: qualquer foto que NÃO existia antes
    fotos_antes = set(backup.get("fotos_antes_clone", []))
    to_delete   = []
    try:
        async for p in client.get_profile_photos("me", limit=50):
            if p.file_unique_id not in fotos_antes:
                to_delete.append(p.file_id)
    except Exception as e:
        await msg.edit_text(tr(f"⚠️ Erro ao listar fotos: `{e}`", f"⚠️ Error listing photos: `{e}`"))

    if to_delete:
        try:
            await client.delete_profile_photos(to_delete)
        except Exception as e:
            await msg.edit_text(tr(f"⚠️ Erro ao apagar foto clonada: `{e}`", f"⚠️ Error deleting cloned photo: `{e}`"))
            salvar("clone_backup.json", {})
            return

    salvar("clone_backup.json", {})
    await msg.edit_text(tr("✅ **Perfil original restaurado com sucesso!**", "✅ **Original profile restored successfully!**"))
