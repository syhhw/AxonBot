"""
AxonBot — main.py
Ponto de entrada: carrega config, conecta ao Google Drive (opcional) e
sobe o cliente Pyrogram com os plugins.

Antes de subir, resolve sozinho os três tropeços de primeira execução:
  1. config.json ausente     → chama o setup.py interativo;
  2. dependências faltando   → instala e reinicia;
  3. terminal que vai fechar → oferece rodar em segundo plano.
"""
import os
import sys

# Console do Windows em cp1252 (e saída redirecionada pro userbot.log) não
# aguenta acento nem emoji: sem isto o processo morre com UnicodeEncodeError.
for _saida in (sys.stdout, sys.stderr):
    try:
        _saida.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_COR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
VERDE, AMARELO, VERMELHO, AZUL, NEGRITO, RESET = (
    ("\033[92m", "\033[93m", "\033[91m", "\033[94m", "\033[1m", "\033[0m")
    if _COR else ("", "", "", "", "", "")
)


def _em_screen() -> bool:
    """Detecta sessão screen/tmux — conta como segundo plano."""
    return "STY" in os.environ or os.environ.get("TERM") == "screen"


# ── 1. Primeira execução: sem config.json não há o que iniciar ────────────────
def _verificar_primeiro_uso() -> None:
    if os.path.exists("config.json"):
        return

    print(f"\n{AZUL}{NEGRITO}  AxonBot — primeira execução{RESET}")
    print(f"  {AMARELO}config.json não encontrado — o bot ainda não foi configurado.{RESET}\n")

    if not os.path.exists("setup.py"):
        print(f"  {VERMELHO}setup.py também não está aqui. Baixe o projeto completo:{RESET}")
        print("  git clone https://github.com/syhhw/AxonBot.git\n")
        sys.exit(1)

    if input("  Rodar o setup agora? [S/n]: ").strip().lower() not in ("", "s"):
        py = "python" if os.name == "nt" else "python3"
        print(f"\n  {AMARELO}Beleza. Rode `{py} setup.py` quando quiser configurar.{RESET}\n")
        sys.exit(0)

    print()
    import runpy
    runpy.run_path("setup.py", run_name="__main__")

    if not os.path.exists("config.json"):
        print(f"\n  {AMARELO}Setup encerrado sem salvar config.json. Bot não iniciado.{RESET}\n")
        sys.exit(0)
    print(f"\n{VERDE}  Configurado. Iniciando...{RESET}\n")


_verificar_primeiro_uso()


# ── 2. Dependências: instala o que faltar e reinicia ──────────────────────────
LIBS = [
    ("pyrogram", "pyrogram>=2.0.106"), ("tgcrypto", "TgCrypto"),
    ("requests", "requests"), ("aiohttp", "aiohttp"), ("aiofiles", "aiofiles"),
    ("humanize", "humanize"), ("psutil", "psutil"), ("PIL", "Pillow"),
    ("gtts", "gTTS"), ("deep_translator", "deep-translator"),
    ("google.genai", "google-genai"), ("yt_dlp", "yt-dlp"),
    ("instaloader", "instaloader"), ("pydrive2", "PyDrive2"),
]


def _garantir_dependencias() -> None:
    import importlib
    import json
    import subprocess

    faltando = []
    for modulo, pacote in LIBS:
        try:
            importlib.import_module(modulo)
        except ImportError:
            faltando.append(pacote)
    if not faltando:
        return

    print(f"\n{AMARELO}  Faltam dependências: {', '.join(faltando)}{RESET}")
    print(f"{AZUL}  Instalando...{RESET}")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", *faltando, "-q"], check=True)
    except Exception as e:
        print(f"{VERMELHO}  Falha ao instalar: {e}{RESET}")
        print("  Tente manualmente: pip install -r requirements.txt\n")
        sys.exit(1)

    print(f"{VERDE}  Pronto. Reiniciando...{RESET}\n")
    with open(".deps_updated.json", "w", encoding="utf-8") as f:
        json.dump(faltando, f)
    if os.name == "nt":
        sys.exit(subprocess.call([sys.executable] + sys.argv))
    os.execv(sys.executable, [sys.executable] + sys.argv)


_garantir_dependencias()


# ── 3. Segundo plano: relança destacado do terminal e sai ─────────────────────
SESSAO = "meu_userbot.session"


def _oferecer_background() -> None:
    if "--background" in sys.argv or "--debug" in sys.argv or _em_screen():
        return

    # Sem sessão salva, o Pyrogram vai pedir telefone e código aqui no
    # terminal. Em segundo plano o stdin é /dev/null: ele leria EOF e
    # morreria dentro do userbot.log, que ninguém abre. Então o primeiro
    # login é sempre em primeiro plano, sem perguntar.
    if not os.path.exists(SESSAO):
        print(f"\n{AZUL}{NEGRITO}  Primeiro login{RESET}")
        print("  O Telegram vai pedir seu telefone e o código de confirmação aqui.")
        print(f"  {AMARELO}Depois disso, os próximos starts já podem ir pra segundo plano.{RESET}\n")
        return

    print(f"\n{AZUL}{NEGRITO}  Como quer rodar?{RESET}")
    print(f"  {VERDE}Segundo plano{RESET}  — continua vivo depois que você fechar o terminal.")
    print(f"  {VERDE}Primeiro plano{RESET} — para junto com o terminal (bom pra ver erro na hora).\n")

    if input("  Rodar em segundo plano? [S/n]: ").strip().lower() not in ("", "s"):
        print(f"\n  {VERDE}Primeiro plano. Ctrl+C encerra.{RESET}\n")
        return

    import subprocess
    script = os.path.abspath(__file__)
    log = os.path.join(os.path.dirname(script), "userbot.log")

    if os.name == "nt":
        python = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(python):
            python = sys.executable
        extras = {"creationflags": getattr(subprocess, "DETACHED_PROCESS", 0x8)
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0x8000000)}
        parar = "taskkill /F /IM pythonw.exe"
    else:
        python, extras = sys.executable, {"start_new_session": True}
        parar = "kill $(pgrep -f 'python.*main.py')"

    with open(log, "a", encoding="utf-8") as f:
        subprocess.Popen([python, script, "--background"], stdout=f, stderr=f,
                         stdin=subprocess.DEVNULL, **extras)

    print(f"\n{VERDE}  Rodando em segundo plano.{RESET}")
    print(f"  Logs:  {log}")
    print(f"  Parar: {AMARELO}{parar}{RESET}\n")
    sys.exit(0)


_oferecer_background()


# ── Imports principais ────────────────────────────────────────────────────────
import asyncio
import json
import logging
import subprocess
import time
from logging.handlers import RotatingFileHandler

# O loop precisa existir ANTES de importar o pyrogram: no Python 3.14 o
# asyncio.get_event_loop() não cria mais um loop sozinho, e o pyrogram/sync.py
# chama isso já no import — sem esta linha, o import estoura com RuntimeError.
# Também garante que o Dispatcher do Client capture este loop, e não outro.
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

from pyrogram import Client, idle

from utils.helpers import criar_task
from utils.i18n import get_lang, tr

drive = None
try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    _DRIVE_DISPONIVEL = True
except ImportError:
    _DRIVE_DISPONIVEL = False


def _git(*args, timeout: int = 5) -> str:
    """Saída de um comando git, ou string vazia se ele falhar."""
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


# O hash curto do commit é a identidade do build — dispensa versionar à mão.
__VERSAO__    = _git("rev-parse", "--short", "HEAD") or "dev"
UPDATE_BRANCH = _git("rev-parse", "--abbrev-ref", "HEAD") or "main"
UPDATE_FLAG   = ".update_pending.json"

# ── Logs ──────────────────────────────────────────────────────────────────────
_FORMATO = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DATA    = "%H:%M:%S"

logging.basicConfig(level=logging.INFO, format=_FORMATO, datefmt=_DATA)
_arquivo = RotatingFileHandler("userbot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
_arquivo.setFormatter(logging.Formatter(_FORMATO, datefmt=_DATA))
logging.getLogger().addHandler(_arquivo)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

logger = logging.getLogger("AxonBotCore")

# ── Configuração ──────────────────────────────────────────────────────────────
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except json.JSONDecodeError as e:
    logger.error(f"config.json está malformado: {e}")
    sys.exit(1)

PREFIXO  = config.get("PREFIXO", ",")
LANGUAGE = get_lang()

# ── Google Drive (opcional) ───────────────────────────────────────────────────
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
            logger.warning("Credenciais do Drive ausentes em meu_drive.json — Drive offline.")
        else:
            if gauth.access_token_expired:
                gauth.Refresh()
                gauth.SaveCredentialsFile("meu_drive.json")
            else:
                gauth.Authorize()
            drive = GoogleDrive(gauth)
            logger.info("Google Drive conectado.")
    except Exception as e:
        logger.error(f"Falha ao conectar o Drive: {e}")
elif _drive_configurado and not _DRIVE_DISPONIVEL:
    logger.warning("pydrive2 não instalado — Drive offline. Instale com: pip install pydrive2")

# ── Cliente ───────────────────────────────────────────────────────────────────
app = Client(
    "meu_userbot",
    api_id=config["API_ID"],
    api_hash=config["API_HASH"],
    device_model="Samsung Galaxy S25",
    system_version="Android 14",
)

app.config        = config
app.drive         = drive
app.tempo_inicio  = time.time()
app.PREFIXO       = PREFIXO
app.LANG          = LANGUAGE
app.VERSAO        = __VERSAO__
app.UPDATE_FLAG   = UPDATE_FLAG
app.UPDATE_BRANCH = UPDATE_BRANCH


def manipulador_erros(loop, context) -> None:
    """Silencia o ruído conhecido do Pyrogram; o resto vai pro canal de logs."""
    erro = str(context.get("exception", ""))
    if any(x in erro for x in ("Peer id invalid", "Message to delete not found", "MESSAGE_NOT_MODIFIED")):
        return
    log_id = config.get("ID_CANAL_LOGS")
    if log_id:
        criar_task(app.send_message(log_id, tr(
            f"⚠️ **Erro interno**\n`{erro}`",
            f"⚠️ **Internal error**\n`{erro}`",
        )))
    loop.default_exception_handler(context)


def _carregar_plugins() -> None:
    import glob
    import importlib

    plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
    # recursive=True pega os plugins organizados em subpastas por categoria
    # (plugins/moderation/purge.py) além dos soltos na raiz.
    for path in sorted(glob.glob(os.path.join(plugins_dir, "**", "*.py"), recursive=True)):
        nome = os.path.basename(path)[:-3]
        if nome.startswith("_"):
            continue
        rel = os.path.relpath(path, plugins_dir)[:-3]
        try:
            mod = importlib.import_module("plugins." + rel.replace(os.sep, "."))
            total = 0
            for attr in vars(mod).values():
                if callable(attr) and hasattr(attr, "handlers"):
                    for handler, group in attr.handlers:
                        app.add_handler(handler, group)
                        total += 1
            logger.info(f"Plugin carregado: {nome} ({total} handler(s))")
            # Hook opcional pra tarefas de background do plugin.
            inicio = getattr(mod, "_on_start", None)
            if inicio and asyncio.iscoroutinefunction(inicio):
                criar_task(inicio(app))
        except Exception as e:
            logger.warning(f"Falha ao carregar o plugin {nome}: {e}")


async def _avisar(texto: str) -> None:
    """Aviso de status no canal de logs, se houver um configurado."""
    log_id = config.get("ID_CANAL_LOGS")
    if not log_id:
        return
    try:
        await app.send_message(log_id, texto)
    except Exception as e:
        logger.warning(f"Falha ao enviar aviso de status: {e}")


def _consumir_flag(caminho: str):
    """Lê e apaga um arquivo de flag deixado por um restart anterior."""
    if not os.path.exists(caminho):
        return None
    dados = None
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception as e:
        logger.warning(f"Flag '{caminho}' ilegível: {e}")
    try:
        os.remove(caminho)
    except OSError:
        pass
    return dados


async def iniciar() -> None:
    asyncio.get_event_loop().set_exception_handler(manipulador_erros)
    logger.info(f"Iniciando AxonBot ({__VERSAO__})...")
    await app.start()
    _carregar_plugins()

    em_bg = "--background" in sys.argv or _em_screen()
    modo  = tr("segundo plano", "background") if em_bg else tr("primeiro plano", "foreground")

    if (update := _consumir_flag(UPDATE_FLAG)) is not None:
        await _avisar(
            f"AxonBot atualizado ({update.get('commit', __VERSAO__)}).\n"
            f"{update.get('mensagem', 'n/a')}\nRodando em {modo}."
        )
    elif (deps := _consumir_flag(".deps_updated.json")) is not None:
        await _avisar(f"Dependências instaladas: {', '.join(deps)}.\nAxonBot online.")
    else:
        await _avisar(
            f"AxonBot online. Build {__VERSAO__} · prefixo {PREFIXO} · "
            f"Drive {'conectado' if drive else 'offline'}. Rodando em {modo}."
        )

    logger.info(f"AxonBot online | prefixo '{PREFIXO}' | idioma {LANGUAGE.upper()}")
    await idle()
    await _avisar("AxonBot encerrado.")
    await app.stop()
    logger.info("AxonBot encerrado.")


if __name__ == "__main__":
    try:
        _loop.run_until_complete(iniciar())
    except KeyboardInterrupt:
        logger.info("Encerrado pelo usuário.")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)
    finally:
        _loop.close()
