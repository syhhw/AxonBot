"""
🚀 USERBOT PRO v2.3 - main.py
Núcleo central que carrega configurações, conecta ao Google Drive
e inicializa o cliente Pyrogram com os plugins.

Inteligência automática:
  - Detecta se está rodando dentro de uma venv; se não estiver, reinicia
    automaticamente usando o Python da venv local (./venv/).
  - Detecta se é novo usuário (config.json ausente) e redireciona para
    o setup.py interativo antes de iniciar.
  - Pergunta se o usuário quer rodar em segundo plano via nohup.
    Se sim, relança o processo com nohup e encerra o processo atual.
"""
import os
import sys

AMARELO  = "\033[93m"
VERDE    = "\033[92m"
AZUL     = "\033[94m"
VERMELHO = "\033[91m"
NEGRITO  = "\033[1m"
RESET    = "\033[0m"

# ══════════════════════════════════════════════════════════════════════════════
# 🟡 BLOCO 1 — PASSO 2: SEGUNDO PLANO VIA NOHUP
# Pergunta se quer rodar em background. Se sim, relança com nohup e encerra.
# A flag --background evita que o processo filho pergunte de novo.
# ══════════════════════════════════════════════════════════════════════════════

def _ja_esta_em_screen() -> bool:
    """Detecta se já está dentro de uma sessão screen (para o aviso no log)."""
    return "STY" in os.environ or os.environ.get("TERM") == "screen"

if "--background" not in sys.argv and "--debug" not in sys.argv:
    print(f"\n{AZUL}{NEGRITO}╔════════════════════════════════════════════╗{RESET}")
    print(f"{AZUL}{NEGRITO}║   🖥️  MODO DE EXECUÇÃO                      ║{RESET}")
    print(f"{AZUL}{NEGRITO}╚════════════════════════════════════════════╝{RESET}\n")
    print(f"  {VERDE}• Primeiro plano:{RESET} o bot para quando você fechar o terminal.")
    print(f"  {VERDE}• Segundo plano:{RESET}  o bot continua rodando mesmo após fechar o terminal.\n")

    _resp = input("  ❓ Rodar em segundo plano? (S/n): ").strip().lower()

    if _resp in ("", "s"):
        _script = os.path.abspath(__file__)
        _log    = os.path.join(os.path.dirname(_script), "userbot.log")
        
        if os.name == "nt":
            import subprocess
            _python_bg = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(_python_bg):
                _python_bg = sys.executable

            with open(_log, "a") as f:
                subprocess.Popen(
                    [_python_bg, _script, "--background"],
                    stdout=f,
                    stderr=f,
                    stdin=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                )
            _stop_cmd = "taskkill /F /IM pythonw.exe"
        else:
            _cmd = f"nohup {sys.executable} {_script} --background > {_log} 2>&1 &"
            _stop_cmd = "kill $(pgrep -f 'python.*main.py')"
            os.system(_cmd)
        print(f"\n{VERDE}✅ Bot iniciado em segundo plano!{RESET}")
        print(f"   Log em: {_log}")
        print(f"   Para parar: {AMARELO}{_stop_cmd}{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n  {VERDE}▶ Rodando em primeiro plano...{RESET}\n")

# ══════════════════════════════════════════════════════════════════════════════
# 🟡 BLOCO 2 — DETECÇÃO DE NOVO USUÁRIO (config.json ausente)
# ══════════════════════════════════════════════════════════════════════════════
def _verificar_primeiro_uso():
    if not os.path.exists("config.json"):
        print(f"\n{AZUL}{NEGRITO}╔════════════════════════════════════════════╗{RESET}")
        print(f"{AZUL}{NEGRITO}║   🚀 USERBOT PRO — PRIMEIRO USO DETECTADO  ║{RESET}")
        print(f"{AZUL}{NEGRITO}╚════════════════════════════════════════════╝{RESET}\n")
        print(f"  {AMARELO}⚠️  config.json não encontrado.{RESET}")
        print(f"  {AMARELO}    É necessário configurar o bot antes de iniciá-lo.{RESET}\n")

        if not os.path.exists("setup.py"):
            print(f"  {AMARELO}❌ setup.py também não encontrado. Baixe o projeto completo.{RESET}\n")
        if not os.path.exists("setup.sh") and os.name != "nt":
            print(f"  {AMARELO}⚠️  setup.sh não encontrado (pode ser ignorado no Windows).{RESET}\n")

        resp = input(f"  ❓ Deseja executar o setup agora? (S/n): ").strip().lower()
        if resp in ("", "s"):
            print(f"\n{VERDE}▶ Iniciando setup...{RESET}\n")
            import runpy
            runpy.run_path("setup.py", run_name="__main__")
            
            import subprocess
            if os.path.exists("setup.sh") and os.name != "nt":
                subprocess.run(["bash", "setup.sh"])

            if not os.path.exists("config.json"):
                print(f"\n  {AMARELO}⚠️  Setup encerrado sem criar config.json. Bot não iniciado.{RESET}\n")
                sys.exit(0)

            print(f"\n{VERDE}✅ Setup concluído! Iniciando o bot...{RESET}\n")
        else:
            cmd_run = "python setup.py" if os.name == "nt" else "python3 setup.py"
            print(f"\n  {AMARELO}Setup cancelado. Execute '{cmd_run}' quando estiver pronto.{RESET}\n")
            sys.exit(0)

_verificar_primeiro_uso()

# ══════════════════════════════════════════════════════════════════════════════
# 🟡 BLOCO 3 — DETECÇÃO AUTOMÁTICA E AUTO-REPAIR DE DEPENDÊNCIAS
# ══════════════════════════════════════════════════════════════════════════════
def _garantir_dependencias():
    import importlib
    import subprocess
    import sys
    import os
    import json

    libs = [
        ("pyrogram",            "pyrogram>=2.0.106"),
        ("requests",            "requests"),
        ("humanize",            "humanize"),
        ("speedtest",           "speedtest-cli"),
        ("PIL",                 "Pillow"),
        ("gtts",                "gTTS"),
        ("deep_translator",     "deep-translator"),
        ("psutil",              "psutil"),
        ("tgcrypto",            "TgCrypto"),
        ("aiofiles",            "aiofiles"),
        ("aiohttp",             "aiohttp"),
        ("google.genai", "google-genai"),
        ("yt_dlp",              "yt-dlp"),
        ("pydrive2",            "PyDrive2")
    ]

    faltando = []
    for lib_import, lib_name in libs:
        try:
            importlib.import_module(lib_import)
        except ImportError:
            faltando.append(lib_name)
            
    if faltando:
        print(f"\n{AMARELO}⚠️  Dependências ausentes detectadas: {', '.join(faltando)}{RESET}")
        print(f"{AZUL}▶  Baixando e instalando em background (isso pode levar alguns segundos)...{RESET}")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", *faltando, "-q"], check=True)
            print(f"{VERDE}✅ Instalação concluída! Reiniciando o bot...{RESET}\n")
            with open(".deps_updated.json", "w", encoding="utf-8") as f:
                json.dump(faltando, f)
            if os.name == "nt":
                sys.exit(subprocess.call([sys.executable] + sys.argv))
            else:
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"{VERMELHO}❌ Falha crítica ao tentar instalar pacotes automaticamente: {e}{RESET}")
            sys.exit(1)

_garantir_dependencias()

# ══════════════════════════════════════════════════════════════════════════════
# 🟢 IMPORTS PRINCIPAIS
# ══════════════════════════════════════════════════════════════════════════════
import json
import time
import logging
import asyncio

from pyrogram import Client, filters, idle
from utils.i18n import tr, get_lang

# Cria e define o event loop ANTES do Client para que o Pyrogram
# capture o loop correto ao inicializar o Dispatcher
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

# Google Drive é opcional
drive = None
try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    _DRIVE_DISPONIVEL = True
except ImportError:
    _DRIVE_DISPONIVEL = False

# ══════════════════════════════════════════════════════════════════════════════
# 🟢 IDENTIDADE DO PROJETO
# ══════════════════════════════════════════════════════════════════════════════
__VERSAO__ = "2.3"
UPDATE_FLAG = ".update_pending.json"

# ══════════════════════════════════════════════════════════════════════════════
# 🟢 LOGS COLORIDOS NO TERMINAL
# ══════════════════════════════════════════════════════════════════════════════
from logging.handlers import RotatingFileHandler as _RFH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
_file_handler = _RFH("userbot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%H:%M:%S")
)
logging.getLogger().addHandler(_file_handler)

logger = logging.getLogger("UserbotCore")
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# ══════════════════════════════════════════════════════════════════════════════
# 🟢 CARREGAMENTO DE CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except json.JSONDecodeError as e:
    logger.error(f"❌ config.json está malformado: {e}")
    sys.exit(1)

PREFIXO = config.get("PREFIXO", ",")
logger.info(f"🔧 Prefixo carregado: '{PREFIXO}'")
LANGUAGE = get_lang()
logger.info(f"🌐 Idioma / Language: '{LANGUAGE.upper()}'")

# ══════════════════════════════════════════════════════════════════════════════
# 🟢 AUTENTICAÇÃO GOOGLE DRIVE (opcional)
# ══════════════════════════════════════════════════════════════════════════════
# Ativa Drive automaticamente se: pydrive2 instalado + credenciais existem + pasta configurada
_drive_configurado = (
    config.get("ID_PASTA_RAIZ_DRIVE")
    and os.path.exists("meu_drive.json")
    and os.path.exists("client_secrets.json")
)

if _DRIVE_DISPONIVEL and _drive_configurado:
    try:
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile("meu_drive.json")
        if gauth.credentials is None:
            logger.warning("⚠️ Credenciais do Drive não encontradas em meu_drive.json — Drive offline.")
        elif gauth.access_token_expired:
            gauth.Refresh()
            gauth.SaveCredentialsFile("meu_drive.json")
            drive = GoogleDrive(gauth)
            logger.info("✅ Google Drive conectado (token renovado).")
        else:
            gauth.Authorize()
            drive = GoogleDrive(gauth)
            logger.info("✅ Google Drive conectado.")
    except Exception as e:
        logger.error(f"❌ Falha ao conectar Drive: {e}")
elif _drive_configurado and not _DRIVE_DISPONIVEL:
    logger.warning("⚠️ pydrive2 não instalado. Instale com: pip install pydrive2")
elif config.get("ID_PASTA_RAIZ_DRIVE") and not os.path.exists("client_secrets.json"):
    logger.warning("⚠️ client_secrets.json não encontrado — Drive offline. Baixe em console.cloud.google.com.")
else:
    logger.info("ℹ️  Google Drive não configurado (opcional).")

# ══════════════════════════════════════════════════════════════════════════════
# 🟢 INICIALIZAÇÃO DO CLIENTE PYROGRAM
# ══════════════════════════════════════════════════════════════════════════════
os.makedirs("plugins", exist_ok=True)

app = Client(
    "meu_userbot",
    api_id=config["API_ID"],
    api_hash=config["API_HASH"],
    device_model="Samsung Galaxy S25",
    system_version="Android 14",
)

app.config       = config
app.drive        = drive
app.tempo_inicio = time.time()
app.PREFIXO      = PREFIXO
app.LANG         = LANGUAGE
app.VERSAO       = __VERSAO__
app.UPDATE_FLAG  = UPDATE_FLAG

# ══════════════════════════════════════════════════════════════════════════════
# 🟢 TRATAMENTO SILENCIOSO DE ERROS COMUNS
# ══════════════════════════════════════════════════════════════════════════════
def manipulador_erros(loop, context):
    erro = str(context.get("exception", ""))
    if any(x in erro for x in ["Peer id invalid", "Message to delete not found", "MESSAGE_NOT_MODIFIED"]):
        return
    try:
        msg = tr(f"⚠️ **ALERTA DO SISTEMA:**\nErro interno detectado em uma das tarefas de execução:\n`{erro}`", f"⚠️ **SYSTEM ALERT:**\nInternal error detected in an execution task:\n`{erro}`")
        app.loop.create_task(app.send_message(config["ID_CANAL_LOGS"], msg))
    except Exception:
        pass
    loop.default_exception_handler(context)

# ══════════════════════════════════════════════════════════════════════════════
# 🟢 ROTINA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def _carregar_plugins():
    import importlib
    import glob
    from pyrogram.handlers import MessageHandler
    plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
    for path in sorted(glob.glob(os.path.join(plugins_dir, "*.py"))):
        nome = os.path.basename(path)[:-3]
        if nome.startswith("_"):
            continue
        mod_name = f"plugins.{nome}"
        try:
            mod = importlib.import_module(mod_name)
            count = 0
            for attr in vars(mod).values():
                if callable(attr) and hasattr(attr, "handlers"):
                    for handler, group in attr.handlers:
                        app.add_handler(handler, group)
                        count += 1
            logger.info(f"✅ Plugin carregado: {nome} ({count} handler(s))")
            # Hook opcional: _on_start(client) para tarefas de background
            startup = getattr(mod, "_on_start", None)
            if startup and asyncio.iscoroutinefunction(startup):
                asyncio.create_task(startup(app))
                logger.info(f"  ↳ _on_start() agendado para {nome}")
        except Exception as e:
            logger.warning(f"⚠️ Falha ao carregar plugin {nome}: {e}")


async def iniciar():
    asyncio.get_event_loop().set_exception_handler(manipulador_erros)
    logger.info(f"🚀 INICIANDO USERBOT PRO v{__VERSAO__}...")
    await app.start()
    _carregar_plugins()

    em_background = "--background" in sys.argv or _ja_esta_em_screen()
    if em_background:
        screen_info = tr("\n🖥️ Rodando em **segundo plano**", "\n🖥️ Running in **background**")
    else:
        screen_info = tr("\n🖥️ Rodando em **primeiro plano** (terminal aberto)", "\n🖥️ Running in **foreground** (terminal open)")

    try:
        if os.path.exists(UPDATE_FLAG):
            try:
                with open(UPDATE_FLAG, "r", encoding="utf-8") as f:
                    info_update = json.load(f)
                arquivos = info_update.get("arquivos", [])
                lista_arq = "\n".join([f"  • `{a}`" for a in arquivos[:15]]) or "  • (sem detalhes)"
                if len(arquivos) > 15:
                    lista_arq += f"\n  • ... e mais {len(arquivos) - 15} arquivo(s)"
                texto_update = (
                    f"🔄 **SISTEMA ATUALIZADO** / **SYSTEM UPDATED**\n\n"
                    f"📦 **v{__VERSAO__}** (`{info_update.get('commit', 'n/a')}`)\n"
                    f"💬 `{info_update.get('mensagem', 'n/a')}`\n"
                    f"{screen_info}"
                )
                await app.send_message(config["ID_CANAL_LOGS"], texto_update)
            except Exception as e:
                logger.warning(f"⚠️ Falha ao ler flag de update: {e}")
            finally:
                try:
                    os.remove(UPDATE_FLAG)
                except OSError:
                    pass
        elif os.path.exists(".deps_updated.json"):
            try:
                with open(".deps_updated.json", "r", encoding="utf-8") as f:
                    libs_instaladas = json.load(f)
                lista_libs = "\n".join([f"📦 `{lib}`" for lib in libs_instaladas])
                await app.send_message(
                    config["ID_CANAL_LOGS"],
                    f"🛠️ **AUTO-REPAIR DETECTADO:**\n\nDetectei que bibliotecas vitais estavam faltando e as instalei automaticamente antes de dar boot:\n{lista_libs}\n\n🚀 **Userbot v{__VERSAO__} ONLINE!**"
                )
            except Exception as e:
                logger.warning(f"⚠️ Falha ao notificar libs instaladas: {e}")
            finally:
                try:
                    os.remove(".deps_updated.json")
                except OSError:
                    pass
        else:
            await app.send_message(
                config["ID_CANAL_LOGS"],
                f"🟢 **USERBOT ONLINE**\n\n"
                f"├ **Versão:** `v{__VERSAO__}`\n"
                f"├ **Prefixo:** `{PREFIXO}`\n"
                f"└ **Drive:** {'✅ Conectado' if drive else '❌ Offline'}\n"
                f"{screen_info}"
            )
    except Exception as e:
        logger.warning(f"⚠️ Falha ao avisar no canal de logs: {e}")

    logger.info(f"✅ USERBOT ONLINE | Prefixo: '{PREFIXO}' | Aguardando comandos...")
    await idle()
    try:
        await app.send_message(config["ID_CANAL_LOGS"], "🛑 **USERBOT OFFLINE**\nO processo foi encerrado de forma segura.")
    except Exception:
        pass
    await app.stop()
    logger.info("👋 Userbot encerrado.")


if __name__ == "__main__":
    try:
        _loop.run_until_complete(iniciar())
    except KeyboardInterrupt:
        logger.info("👋 Encerrado pelo usuário.")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)
    finally:
        _loop.close()
