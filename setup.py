"""
🚀 AXONBOT v2.3 — setup.py
Configurador interativo cross-platform: Windows, Linux (Ubuntu/Debian), Termux Android.
Sem venv obrigatório — instala direto no Python do sistema com as flags certas.
"""
import os
import sys
import json
import subprocess
import importlib
import sysconfig
import platform

# ══════════════════════════════════════════════════════════════════════════════
# 🎨 CORES DO TERMINAL
# ══════════════════════════════════════════════════════════════════════════════
VERDE    = "\033[92m"
VERMELHO = "\033[91m"
AMARELO  = "\033[93m"
AZUL     = "\033[94m"
CIANO    = "\033[96m"
NEGRITO  = "\033[1m"
RESET    = "\033[0m"

# ══════════════════════════════════════════════════════════════════════════════
# 🔍 DETECÇÃO DE PLATAFORMA
# ══════════════════════════════════════════════════════════════════════════════
_IS_ANDROID = os.path.exists("/system/build.prop") or "TERMUX_VERSION" in os.environ
_IS_WINDOWS = platform.system() == "Windows"
_IS_LINUX   = platform.system() == "Linux" and not _IS_ANDROID

def _nome_plataforma() -> str:
    if _IS_ANDROID:
        return "📱 Android (Termux)"
    if _IS_WINDOWS:
        return f"🪟 Windows {platform.release()}"
    return f"🐧 Linux ({platform.linux_distribution()[0] if hasattr(platform, 'linux_distribution') else platform.version()[:30]})"

def _python_cmd() -> str:
    """Retorna o comando python correto para este sistema."""
    return sys.executable

def _pip_flags() -> list:
    """Retorna flags extras para pip install quando necessário."""
    stdlib = sysconfig.get_path("stdlib") or ""
    if os.path.exists(os.path.join(stdlib, "EXTERNALLY-MANAGED")):
        return ["--break-system-packages"]
    return []

# ══════════════════════════════════════════════════════════════════════════════
# 🟢 UTILITÁRIOS
# ══════════════════════════════════════════════════════════════════════════════
def cabecalho():
    print(f"\n{AZUL}{NEGRITO}╔══════════════════════════════════════════════════╗{RESET}")
    print(f"{AZUL}{NEGRITO}║   🚀  AXONBOT v2.3 — SETUP INTERATIVO        ║{RESET}")
    print(f"{AZUL}{NEGRITO}╚══════════════════════════════════════════════════╝{RESET}\n")
    print(f"  {CIANO}Plataforma : {RESET}{_nome_plataforma()}")
    print(f"  {CIANO}Python     : {RESET}{sys.version.split()[0]} ({sys.executable})")
    print()


def secao(n: int, total: int, titulo: str):
    print(f"\n{NEGRITO}{'─'*50}{RESET}")
    print(f"{NEGRITO}[{n}/{total}] {titulo}{RESET}")
    print(f"{NEGRITO}{'─'*50}{RESET}\n")


def ok(msg: str):
    print(f"  {VERDE}✅ {msg}{RESET}")

def aviso(msg: str):
    print(f"  {AMARELO}⚠️  {msg}{RESET}")

def erro(msg: str):
    print(f"  {VERMELHO}❌ {msg}{RESET}")

def info(msg: str):
    print(f"  {CIANO}ℹ️  {msg}{RESET}")


def perguntar(prompt: str, padrao: str = "") -> str:
    sufixo = f" [{padrao}]" if padrao else ""
    try:
        resp = input(f"  ❓ {prompt}{sufixo}: ").strip()
        return resp if resp else padrao
    except (KeyboardInterrupt, EOFError):
        print()
        raise KeyboardInterrupt


# ══════════════════════════════════════════════════════════════════════════════
# 📦 VERIFICAÇÃO E INSTALAÇÃO DE DEPENDÊNCIAS
# ══════════════════════════════════════════════════════════════════════════════
LIBS = [
    ("pyrogram",        "pyrogram>=2.0.106"),
    ("tgcrypto",        "tgcrypto"),
    ("requests",        "requests"),
    ("humanize",        "humanize"),
    ("speedtest",       "speedtest-cli"),
    ("PIL",             "Pillow"),
    ("gtts",            "gTTS"),
    ("deep_translator", "deep-translator"),
    ("psutil",          "psutil"),
    ("aiofiles",        "aiofiles"),
    ("aiohttp",         "aiohttp"),
    ("google.genai",    "google-genai"),
    ("yt_dlp",          "yt-dlp"),
    ("pydrive2",        "PyDrive2"),
]


def verificar_libs() -> list:
    faltando = []
    for lib_import, lib_pip in LIBS:
        try:
            importlib.import_module(lib_import)
            ok(lib_pip)
        except ImportError:
            erro(lib_pip)
            faltando.append(lib_pip)
    return faltando


def instalar_libs(pacotes: list) -> bool:
    flags = _pip_flags()
    req = "requirements.txt"

    if os.path.exists(req):
        print(f"\n  {AMARELO}▶ Instalando via requirements.txt...{RESET}")
        cmd = [sys.executable, "-m", "pip", "install", "-r", req, "-q"] + flags
        ret = subprocess.run(cmd)
        if ret.returncode == 0:
            ok("Todas as dependências instaladas!")
            return True
        aviso("Falha com requirements.txt, tentando pacote por pacote...")

    sucesso = True
    for pkg in pacotes:
        cmd = [sys.executable, "-m", "pip", "install", pkg, "-q"] + flags
        ret = subprocess.run(cmd, capture_output=True)
        if ret.returncode == 0:
            ok(pkg)
        else:
            erro(f"{pkg} — falha na instalação")
            sucesso = False

    return sucesso


def _instrucao_pip_manual():
    """Exibe instrução específica por plataforma se pip falhar."""
    if _IS_ANDROID:
        info("No Termux: pkg install python && pip install -r requirements.txt")
    elif _IS_LINUX:
        info("Se precisar: pip install -r requirements.txt --break-system-packages")
        info("Ou crie um venv: python3 -m venv venv && source venv/bin/activate")
    elif _IS_WINDOWS:
        info("Execute: pip install -r requirements.txt")
        info("Se der erro de permissão: execute o terminal como Administrador")


# ══════════════════════════════════════════════════════════════════════════════
# ⚙️  CONFIGURAÇÃO DO BOT
# ══════════════════════════════════════════════════════════════════════════════
def configurar() -> dict:
    print(f"  Obtenha seu API_ID e API_HASH em: {AMARELO}https://my.telegram.org{RESET}\n")

    config = {}

    api_id_raw = perguntar("API_ID (somente números)")
    config["API_ID"] = int(api_id_raw)

    config["API_HASH"] = perguntar("API_HASH")

    canal_raw = perguntar("ID do canal de logs (ex: -1001234567890)")
    config["ID_CANAL_LOGS"] = int(canal_raw)

    config["PREFIXO"] = perguntar("Prefixo dos comandos", ",")
    config["LANGUAGE"] = perguntar("Idioma [pt/en]", "pt").lower()
    if config["LANGUAGE"] not in ("pt", "en"):
        config["LANGUAGE"] = "pt"

    print()
    info("(Opcional) Chave do Google Gemini para comandos de IA.")
    info("Pegue grátis em: https://aistudio.google.com/app/apikey")
    gemini = perguntar("GEMINI_API_KEY (Enter para pular)", "")
    if gemini:
        config["GEMINI_API_KEY"] = gemini

    return config


# ══════════════════════════════════════════════════════════════════════════════
# 📂 GOOGLE DRIVE (OPCIONAL)
# ══════════════════════════════════════════════════════════════════════════════
def configurar_drive(config: dict) -> dict:
    print(f"  O Google Drive permite backup e organização automática de arquivos.")
    print(f"  {AMARELO}Você pode pular e configurar depois editando config.json.{RESET}\n")

    usar = perguntar("Deseja configurar o Google Drive agora? [s/N]", "n").lower()
    if usar != "s":
        info("Google Drive ignorado. Configure depois se quiser.")
        return config

    # Verifica arquivos necessários
    tem_secrets = os.path.exists("client_secrets.json")
    tem_creds   = os.path.exists("meu_drive.json")

    if not tem_secrets:
        aviso("client_secrets.json não encontrado.")
        print(f"\n  {CIANO}Como obter:{RESET}")
        print(f"   1. Acesse: {AMARELO}https://console.cloud.google.com{RESET}")
        print(f"   2. Crie um projeto → Ative a Google Drive API")
        print(f"   3. Credenciais → Criar credencial → ID do cliente OAuth")
        print(f"   4. Tipo: Aplicativo para computador")
        print(f"   5. Baixe o JSON e salve como {VERDE}client_secrets.json{RESET} nesta pasta")
        print(f"\n  {AMARELO}Cole o arquivo e execute o setup novamente para continuar.{RESET}")
    else:
        ok("client_secrets.json encontrado.")

    if not tem_creds:
        aviso("meu_drive.json não encontrado — será criado na primeira autenticação.")
    else:
        ok("meu_drive.json encontrado.")

    if tem_secrets:
        pasta = perguntar("ID da pasta raiz do Drive (Enter para usar raiz)", "")
        if pasta:
            config["ID_PASTA_RAIZ_DRIVE"] = pasta
        limite = perguntar("Limite de auto-upload em MB", "20")
        config["LIMITE_AUTO_UPLOAD"] = int(limite) * 1024 * 1024

    return config


# ══════════════════════════════════════════════════════════════════════════════
# 🚀 INSTRUÇÕES DE EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════════
def instrucoes_finais():
    print(f"\n{AZUL}{NEGRITO}╔══════════════════════════════════════════════════╗{RESET}")
    print(f"{AZUL}{NEGRITO}║   ✅  SETUP CONCLUÍDO — PRÓXIMOS PASSOS          ║{RESET}")
    print(f"{AZUL}{NEGRITO}╚══════════════════════════════════════════════════╝{RESET}\n")

    if _IS_WINDOWS:
        print(f"  {VERDE}▶ Iniciar o bot:{RESET}")
        print(f"     python main.py\n")
        print(f"  {VERDE}▶ Rodar em segundo plano (fecha com o terminal):{RESET}")
        print(f"     pythonw main.py --background\n")

    elif _IS_ANDROID:
        print(f"  {VERDE}▶ Iniciar o bot:{RESET}")
        print(f"     python main.py\n")
        print(f"  {VERDE}▶ Rodar em segundo plano (continua após fechar Termux):{RESET}")
        print(f"     nohup python main.py --background > userbot.log 2>&1 &\n")
        print(f"  {VERDE}▶ Ver logs:{RESET}")
        print(f"     tail -f userbot.log\n")

    else:  # Linux
        print(f"  {VERDE}▶ Iniciar o bot:{RESET}")
        print(f"     python3 main.py\n")
        print(f"  {VERDE}▶ Rodar em segundo plano (recomendado no servidor):{RESET}")
        print(f"     nohup python3 main.py --background > userbot.log 2>&1 &\n")
        print(f"  {VERDE}▶ Ou usando screen (persiste após fechar SSH):{RESET}")
        print(f"     screen -S userbot\n")
        print(f"     python3 main.py\n")
        print(f"     # Ctrl+A, D para desanexar\n")
        print(f"  {VERDE}▶ Ver logs:{RESET}")
        print(f"     tail -f userbot.log\n")
        print(f"  {VERDE}▶ Parar o bot:{RESET}")
        print(f"     kill $(pgrep -f 'python.*main.py')\n")

    print(f"  {CIANO}Dica: use o comando ,menu no Telegram para ver todos os comandos.{RESET}\n")


# ══════════════════════════════════════════════════════════════════════════════
# 🟢 FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
TOTAL_ETAPAS = 4

def main():
    cabecalho()

    # ── [1/4] VERIFICAÇÃO DE VERSÃO PYTHON ───────────────────────────────────
    secao(1, TOTAL_ETAPAS, "Verificando requisitos do sistema")
    py = sys.version_info
    if py < (3, 10):
        erro(f"Python {py.major}.{py.minor} detectado. Necessário Python 3.10+.")
        if _IS_ANDROID:
            info("No Termux: pkg upgrade && pkg install python")
        elif _IS_LINUX:
            info("Ubuntu/Debian: sudo apt install python3.11 python3.11-distutils")
        sys.exit(1)
    ok(f"Python {py.major}.{py.minor}.{py.micro} — OK")

    # ── [2/4] DEPENDÊNCIAS ────────────────────────────────────────────────────
    secao(2, TOTAL_ETAPAS, "Verificando dependências")
    faltando = verificar_libs()

    if faltando:
        aviso(f"{len(faltando)} pacote(s) faltando.")
        resp = perguntar("Instalar automaticamente agora? [S/n]", "s").lower()
        if resp in ("s", ""):
            sucesso = instalar_libs(faltando)
            if not sucesso:
                aviso("Alguns pacotes falharam. Tente instalar manualmente:")
                _instrucao_pip_manual()
                resp2 = perguntar("Continuar mesmo assim? [s/N]", "n").lower()
                if resp2 != "s":
                    print(f"\n{VERMELHO}Setup interrompido.{RESET}\n")
                    return
        else:
            aviso("Dependências não instaladas. O bot pode não funcionar corretamente.")
    else:
        ok("Todas as dependências estão instaladas!")

    # ── [3/4] CONFIGURAÇÃO ────────────────────────────────────────────────────
    secao(3, TOTAL_ETAPAS, "Configurando credenciais")

    if os.path.exists("config.json"):
        aviso("Já existe um config.json.")
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                atual = json.load(f)
            print(f"     • API_ID:   {atual.get('API_ID', '?')}")
            print(f"     • Prefixo:  '{atual.get('PREFIXO', ',')}'")
            print(f"     • Idioma:   {atual.get('LANGUAGE', 'pt').upper()}")
            print(f"     • Drive:    {'Ativo' if atual.get('ID_PASTA_RAIZ_DRIVE') else 'Inativo'}")
        except Exception:
            aviso("config.json parece corrompido.")
        resp = perguntar("Deseja reconfigurar? [s/N]", "n").lower()
        if resp != "s":
            ok("Mantendo configurações atuais.")

            # Pergunta sobre Drive mesmo sem reconfigurar tudo
            secao(4, TOTAL_ETAPAS, "Google Drive (opcional)")
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                config = configurar_drive(config)
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
            except Exception:
                pass
            instrucoes_finais()
            return

    try:
        config = configurar()
    except KeyboardInterrupt:
        print(f"\n\n{AMARELO}Setup cancelado pelo usuário.{RESET}\n")
        return
    except ValueError as e:
        erro(f"API_ID e ID do canal devem ser números inteiros. Detalhe: {e}")
        return

    # ── [4/4] GOOGLE DRIVE ────────────────────────────────────────────────────
    secao(4, TOTAL_ETAPAS, "Google Drive (opcional)")
    try:
        config = configurar_drive(config)
    except KeyboardInterrupt:
        info("Drive ignorado.")

    # Salva config.json
    try:
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        ok("config.json salvo com sucesso!")
    except Exception as e:
        erro(f"Não foi possível salvar config.json: {e}")
        return

    instrucoes_finais()


if __name__ == "__main__":
    main()
