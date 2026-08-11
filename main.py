"""
🚀 AXONBOT v2.3 - main.py
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
            import subprocess
            _stop_cmd = "kill $(pgrep -f 'python.*main.py')"
            with open(_log, "a") as _f:
                subprocess.Popen(
                    [sys.executable, _script, "--background"],
                    stdout=_f, stderr=_f, stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
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
        print(f"{AZUL}{NEGRITO}║   🚀 AXONBOT — PRIMEIRO USO DETECTADO  ║{RESET}")
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
from utils.helpers import alertar_dono_via_bot

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
def _commit_atual() -> str:
    """Hash curto do commit local — serve de identidade do build, sem precisar
    manter um número de versão manualmente. ,versao/,atualizar já comparam
    esse hash contra origin/<branch> pra saber se há atualização disponível."""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else "dev"
    except Exception:
        return "dev"

__VERSAO__     = _commit_atual()
UPDATE_FLAG    = ".update_pending.json"
UPDATE_BRANCH  = "AxonBot"

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

logger = logging.getLogger("AxonBotCore")
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
app.VERSAO        = __VERSAO__
app.UPDATE_FLAG   = UPDATE_FLAG
app.UPDATE_BRANCH = UPDATE_BRANCH

# ── Companion bot ─────────────────────────────────────────────────────────────
def _matar_companion_anterior(pid_file: str) -> None:
    """Encerra uma instância anterior do bot.py ainda viva, se houver.

    Sem isso, cada restart (,restart/,atualizar) empilhava mais um bot.py
    disputando o mesmo BOT_TOKEN via getUpdates, causando
    'Conflict: terminated by other getUpdates request' no Telegram.
    """
    if not os.path.exists(pid_file):
        return
    try:
        with open(pid_file, "r") as f:
            pid_antigo = int(f.read().strip())
        if os.name == "nt":
            import subprocess as _sp
            _sp.run(["taskkill", "/F", "/PID", str(pid_antigo)], capture_output=True)
        else:
            import signal
            os.kill(pid_antigo, signal.SIGTERM)
        logger.info(f"🤖 bot.py anterior (PID {pid_antigo}) encerrado.")
    except (ProcessLookupError, ValueError, OSError):
        pass
    except Exception as e:
        logger.debug(f"Falha ao encerrar bot.py anterior: {e}")


def _launch_companion_bot() -> None:
    """Sobe bot.py junto se configurado e main.py não foi iniciado por ele."""
    if os.environ.get("PANEL_CHILD"):
        return
    if not config.get("BOT_TOKEN"):
        return
    import subprocess as _sp
    _dir     = os.path.dirname(os.path.abspath(__file__))
    bot_py   = os.path.join(_dir, "bot.py")
    pid_file = os.path.join(_dir, ".bot_companion.pid")
    if not os.path.exists(bot_py):
        return

    _matar_companion_anterior(pid_file)

    env = os.environ.copy()
    env["PANEL_CHILD"] = "1"
    try:
        proc = _sp.Popen([sys.executable, bot_py], env=env, cwd=_dir)
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
        logger.info(f"🤖 bot.py iniciado (PID {proc.pid}).")
    except Exception as e:
        logger.warning(f"⚠️ Falha ao iniciar bot.py: {e}")

_launch_companion_bot()

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
    # recursive=True pra pegar plugins organizados em subpastas por categoria
    # (plugins/moderation/purge.py) além dos soltos na raiz (plugins/*.py).
    for path in sorted(glob.glob(os.path.join(plugins_dir, "**", "*.py"), recursive=True)):
        nome = os.path.basename(path)[:-3]
        if nome.startswith("_"):
            continue
        rel = os.path.relpath(path, plugins_dir)[:-3]
        mod_name = "plugins." + rel.replace(os.sep, ".")
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


async def _notificar_status(texto: str) -> None:
    """Avisos de status do boot (online/atualizado/desligado) — prefere PV
    direto do dono via bot do painel (discreto); só cai pro canal de logs
    se o painel não estiver configurado ou o envio falhar."""
    if await alertar_dono_via_bot(config, texto, parse_mode=None):
        return
    log_id = config.get("ID_CANAL_LOGS")
    if not log_id:
        return
    try:
        await app.send_message(log_id, texto)
    except Exception as e:
        logger.warning(f"⚠️ Falha ao avisar status: {e}")


async def iniciar():
    asyncio.get_event_loop().set_exception_handler(manipulador_erros)
    logger.info(f"🚀 INICIANDO AXONBOT (`{__VERSAO__}`)...")
    await app.start()
    _carregar_plugins()

    em_background = "--background" in sys.argv or _ja_esta_em_screen()
    modo = tr("segundo plano", "background") if em_background else tr("primeiro plano", "foreground")

    if os.path.exists(UPDATE_FLAG):
        try:
            with open(UPDATE_FLAG, "r", encoding="utf-8") as f:
                info_update = json.load(f)
            await _notificar_status(
                f"AxonBot atualizado ({info_update.get('commit', __VERSAO__)}).\n"
                f"{info_update.get('mensagem', 'n/a')}\n"
                f"Rodando em {modo}."
            )
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
            await _notificar_status(
                f"Instalei automaticamente as libs que faltavam: {', '.join(libs_instaladas)}.\n"
                f"AxonBot online."
            )
        except Exception as e:
            logger.warning(f"⚠️ Falha ao notificar libs instaladas: {e}")
        finally:
            try:
                os.remove(".deps_updated.json")
            except OSError:
                pass
    else:
        await _notificar_status(
            f"AxonBot online. Build {__VERSAO__} · prefixo {PREFIXO} · "
            f"Drive {'conectado' if drive else 'offline'}. Rodando em {modo}."
        )

    logger.info(f"✅ AXONBOT ONLINE | Prefixo: '{PREFIXO}' | Aguardando comandos...")
    await idle()
    await _notificar_status("AxonBot encerrado.")
    await app.stop()
    logger.info("👋 AxonBot encerrado.")


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
