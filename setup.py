"""
AxonBot — setup.py
Configurador interativo para Windows, Linux e Termux (Android).

Instala direto no Python do sistema, com as flags certas pra cada
plataforma — venv é opcional, não obrigatório.
"""
import importlib
import json
import os
import platform
import subprocess
import sys
import sysconfig

# O console do Windows ainda abre em cp1252, e a saída redirecionada pra
# arquivo também. Sem isto, um traço "─" ou um emoji derruba o setup inteiro
# com UnicodeEncodeError antes da primeira pergunta.
for _saida in (sys.stdout, sys.stderr):
    try:
        _saida.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Sem terminal de verdade (saída num pipe ou arquivo), código de cor vira lixo.
_COR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(codigo: str) -> str:
    return codigo if _COR else ""


VERDE    = _c("\033[92m")
VERMELHO = _c("\033[91m")
AMARELO  = _c("\033[93m")
AZUL     = _c("\033[94m")
CIANO    = _c("\033[96m")
CINZA    = _c("\033[90m")
NEGRITO  = _c("\033[1m")
RESET    = _c("\033[0m")

_IS_ANDROID = os.path.exists("/system/build.prop") or "TERMUX_VERSION" in os.environ
_IS_WINDOWS = platform.system() == "Windows"
_IS_LINUX   = platform.system() == "Linux" and not _IS_ANDROID

TOTAL_ETAPAS = 5


# ══════════════════════════════════════════════════════════════════════════════
# Plataforma
# ══════════════════════════════════════════════════════════════════════════════
def _nome_distro_linux() -> str:
    """Lê /etc/os-release. platform.linux_distribution() saiu no Python 3.8."""
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for linha in f:
                if linha.startswith("PRETTY_NAME="):
                    return linha.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return platform.version()[:30]


def _nome_plataforma() -> str:
    if _IS_ANDROID:
        return "Android (Termux)"
    if _IS_WINDOWS:
        return f"Windows {platform.release()}"
    return f"Linux ({_nome_distro_linux()})"


def _pip_flags() -> list:
    """Distros novas bloqueiam pip fora de venv (PEP 668) — contorna."""
    stdlib = sysconfig.get_path("stdlib") or ""
    if os.path.exists(os.path.join(stdlib, "EXTERNALLY-MANAGED")):
        return ["--break-system-packages"]
    return []


# ══════════════════════════════════════════════════════════════════════════════
# Saída no terminal
# ══════════════════════════════════════════════════════════════════════════════
def cabecalho():
    print(f"\n{AZUL}{NEGRITO}  AxonBot — instalação{RESET}")
    print(f"{CINZA}  {_nome_plataforma()} · Python {sys.version.split()[0]}{RESET}\n")


def secao(n: int, titulo: str):
    print(f"\n{NEGRITO}[{n}/{TOTAL_ETAPAS}] {titulo}{RESET}")
    print(f"{CINZA}{'─' * 52}{RESET}")


def ok(msg):     print(f"  {VERDE}✓{RESET} {msg}")
def aviso(msg):  print(f"  {AMARELO}!{RESET} {msg}")
def erro(msg):   print(f"  {VERMELHO}✗{RESET} {msg}")
def info(msg):   print(f"  {CINZA}{msg}{RESET}")


def perguntar(prompt: str, padrao: str = "") -> str:
    sufixo = f" {CINZA}[{padrao}]{RESET}" if padrao else ""
    try:
        resp = input(f"  {CIANO}?{RESET} {prompt}{sufixo}: ").strip()
        return resp if resp else padrao
    except (KeyboardInterrupt, EOFError):
        print()
        raise KeyboardInterrupt


def confirmar(prompt: str, padrao: bool = True) -> bool:
    """Pergunta de sim/não. A letra maiúscula em [S/n] é o que o Enter escolhe."""
    dica = "S/n" if padrao else "s/N"
    try:
        resp = input(f"  {CIANO}?{RESET} {prompt} {CINZA}[{dica}]{RESET}: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        raise KeyboardInterrupt
    if not resp:
        return padrao
    return resp in ("s", "sim", "y", "yes")


def perguntar_int(prompt: str, obrigatorio: bool = True) -> int | None:
    """Insiste até receber um número inteiro. Enter pula quando é opcional."""
    while True:
        resp = perguntar(prompt + ("" if obrigatorio else " (Enter para pular)"))
        if not resp and not obrigatorio:
            return None
        try:
            return int(resp)
        except ValueError:
            erro("Isso precisa ser um número inteiro, sem letras nem espaços.")


# ══════════════════════════════════════════════════════════════════════════════
# Dependências
# ══════════════════════════════════════════════════════════════════════════════
LIBS = [
    ("pyrogram",        "pyrogram>=2.0.106"),
    ("tgcrypto",        "tgcrypto"),
    ("requests",        "requests"),
    ("aiohttp",         "aiohttp"),
    ("aiofiles",        "aiofiles"),
    ("humanize",        "humanize"),
    ("psutil",          "psutil"),
    ("PIL",             "Pillow"),
    ("gtts",            "gTTS"),
    ("deep_translator", "deep-translator"),
    ("google.genai",    "google-genai"),
    ("yt_dlp",          "yt-dlp"),
    ("instaloader",     "instaloader"),
    ("pydrive2",        "PyDrive2"),
]


def verificar_libs() -> list:
    faltando = [pip for mod, pip in LIBS if not _tem(mod)]
    if faltando:
        aviso(f"{len(faltando)} de {len(LIBS)} pacotes faltando: {', '.join(faltando)}")
    else:
        ok(f"Todos os {len(LIBS)} pacotes já estão instalados.")
    return faltando


def _tem(modulo: str) -> bool:
    """Instalado e importável. Captura Exception, não só ImportError: no
    Python 3.14 o pyrogram estoura RuntimeError no import por causa do
    event loop, e isso não pode derrubar o setup inteiro."""
    try:
        importlib.import_module(modulo)
        return True
    except Exception:
        return False


def instalar_libs(pacotes: list) -> bool:
    flags = _pip_flags()

    if os.path.exists("requirements.txt"):
        info("Instalando via requirements.txt...")
        if subprocess.run([sys.executable, "-m", "pip", "install",
                           "-r", "requirements.txt", "-q"] + flags).returncode == 0:
            ok("Dependências instaladas.")
            return True
        aviso("requirements.txt falhou. Tentando pacote por pacote...")

    falhou = []
    for pkg in pacotes:
        r = subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"] + flags,
                           capture_output=True)
        if r.returncode == 0:
            ok(pkg)
        else:
            erro(pkg)
            falhou.append(pkg)

    if falhou:
        print()
        aviso(f"Não instalou: {', '.join(falhou)}")
        if _IS_ANDROID:
            info("No Termux: pkg install python && pip install -r requirements.txt")
        elif _IS_LINUX:
            info("Tente: pip install -r requirements.txt --break-system-packages")
            info("Ou num venv: python3 -m venv venv && source venv/bin/activate")
        else:
            info("Tente: pip install -r requirements.txt")
            info("Se der erro de permissão, abra o terminal como Administrador.")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Credenciais
# ══════════════════════════════════════════════════════════════════════════════
def configurar() -> dict:
    print("  O AxonBot roda na SUA conta do Telegram, então precisa das chaves")
    print("  de API que o próprio Telegram te dá de graça.\n")
    print(f"  {NEGRITO}Como pegar:{RESET}")
    print(f"    1. Abra {AMARELO}https://my.telegram.org{RESET} e entre com seu número")
    print("    2. Clique em 'API development tools'")
    print("    3. Preencha qualquer nome de app (ex: axonbot)")
    print(f"    4. Copie o {NEGRITO}api_id{RESET} e o {NEGRITO}api_hash{RESET} que aparecerem\n")
    print(f"  {CINZA}Essas chaves ficam só no seu config.json, que o .gitignore já protege.{RESET}\n")

    config = {}
    config["API_ID"]   = perguntar_int("API_ID (só números)")
    config["API_HASH"] = perguntar("API_HASH")

    print()
    print("  O canal de logs é um canal privado seu, onde o bot avisa quando")
    print("  liga, quando dá erro e o que foi moderado. É opcional.")
    print(f"  {CINZA}Para usar: crie um canal privado, adicione sua conta, e pegue o ID{RESET}")
    print(f"  {CINZA}encaminhando qualquer mensagem dele para @userinfobot.{RESET}\n")
    canal = perguntar_int("ID do canal de logs, tipo -1001234567890", obrigatorio=False)
    if canal:
        config["ID_CANAL_LOGS"] = canal

    print()
    config["PREFIXO"] = perguntar("Prefixo dos comandos", ",")
    idioma = perguntar("Idioma [pt/en]", "pt").lower()
    config["LANGUAGE"] = idioma if idioma in ("pt", "en") else "pt"

    print()
    print("  A chave do Google Gemini libera ,perguntar e ,resumir. É grátis e opcional.")
    print(f"  {CINZA}Pegue em https://aistudio.google.com/app/apikey{RESET}\n")
    if gemini := perguntar("GEMINI_API_KEY (Enter para pular)", ""):
        config["GEMINI_API_KEY"] = gemini

    return config


# ══════════════════════════════════════════════════════════════════════════════
# Google Drive (opcional)
# ══════════════════════════════════════════════════════════════════════════════
def configurar_drive(config: dict) -> dict:
    print("  O Drive guarda e organiza sozinho os arquivos que te mandam no Telegram.")
    print("  Dá pra configurar depois — o resto do bot funciona sem isso.\n")

    if not confirmar("Configurar o Google Drive agora?", padrao=False):
        info("Drive ignorado.")
        return config

    if not os.path.exists("client_secrets.json"):
        aviso("client_secrets.json não está nesta pasta.")
        print(f"\n  {NEGRITO}Como conseguir:{RESET}")
        print(f"    1. Abra {AMARELO}https://console.cloud.google.com{RESET}")
        print("    2. Crie um projeto e ative a Google Drive API")
        print("    3. Credenciais → Criar credencial → ID do cliente OAuth")
        print("    4. Tipo de aplicativo: Computador")
        print(f"    5. Baixe o JSON, renomeie para {VERDE}client_secrets.json{RESET} e ponha aqui")
        print(f"\n  {CINZA}Depois rode o setup de novo pra terminar essa parte.{RESET}")
        return config

    ok("client_secrets.json encontrado.")
    if not os.path.exists("meu_drive.json"):
        info("meu_drive.json será criado na primeira autenticação.")

    if pasta := perguntar("ID da pasta raiz do Drive (Enter usa a raiz)", ""):
        config["ID_PASTA_RAIZ_DRIVE"] = pasta
    limite = perguntar("Enviar automaticamente arquivos de até quantos MB?", "20")
    try:
        config["LIMITE_AUTO_UPLOAD"] = int(limite) * 1024 * 1024
    except ValueError:
        config["LIMITE_AUTO_UPLOAD"] = 20 * 1024 * 1024

    return config


# ══════════════════════════════════════════════════════════════════════════════
# Login no Telegram
# ══════════════════════════════════════════════════════════════════════════════
def fazer_login(config: dict) -> bool:
    """Cria a sessão do Telegram já aqui, em vez de deixar pro primeiro start.

    Vale por dois motivos: tira o passo mais confuso do caminho, e confere
    na hora se o API_ID/API_HASH digitados realmente funcionam — errar essas
    chaves é de longe o problema mais comum de quem instala.
    """
    if os.path.exists("meu_userbot.session"):
        ok("Sessão já existe — você continua logado.")
        return True

    print("  Falta entrar na sua conta. O Telegram vai mandar um código no app;")
    print("  se você usa verificação em duas etapas, ele pede a senha também.")
    print(f"  {CINZA}Nada disso fica salvo em texto: vira uma sessão local, que o{RESET}")
    print(f"  {CINZA}.gitignore já impede de subir pro GitHub.{RESET}\n")

    if not confirmar("Entrar na conta agora?"):
        info("Sem problema — o login acontece no primeiro `python main.py`.")
        return False

    try:
        import asyncio
        # No Python 3.14 o import do pyrogram exige um loop já existente.
        asyncio.set_event_loop(asyncio.new_event_loop())
        from pyrogram import Client
    except Exception as e:
        erro(f"Não consegui carregar o Pyrogram: {e}")
        return False

    print()
    try:
        with Client("meu_userbot",
                    api_id=config["API_ID"],
                    api_hash=config["API_HASH"]) as app:
            me = app.get_me()
        print()
        ok(f"Logado como {me.first_name}"
           + (f" (@{me.username})" if me.username else "") + ".")
        return True
    except KeyboardInterrupt:
        print()
        info("Login cancelado. Dá pra fazer depois, no primeiro start.")
        return False
    except Exception as e:
        print()
        erro(f"O login falhou: {e}")
        info("Quase sempre é API_ID ou API_HASH copiado errado de my.telegram.org.")
        info("Rode o setup de novo e escolha refazer a configuração.")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Encerramento
# ══════════════════════════════════════════════════════════════════════════════
def instrucoes_finais(config: dict, logado: bool = True):
    p  = config.get("PREFIXO", ",")
    py = "python" if _IS_WINDOWS else "python3"

    print(f"\n{VERDE}{NEGRITO}  Tudo pronto.{RESET}\n")
    print(f"  {NEGRITO}Iniciar{RESET}")
    print(f"    {py} main.py")
    if logado:
        print(f"  {CINZA}Ele pergunta se você quer rodar em segundo plano — responder S deixa{RESET}")
        print(f"  {CINZA}o bot vivo depois que você fechar o terminal.{RESET}\n")
    else:
        print(f"  {CINZA}No primeiro start ele pede seu telefone e o código do Telegram.{RESET}")
        print(f"  {CINZA}Deixe o terminal aberto até aparecer 'AxonBot online'.{RESET}\n")

    print(f"  {NEGRITO}Parar{RESET}")
    if _IS_WINDOWS:
        print("    taskkill /F /IM pythonw.exe")
    else:
        print("    kill $(pgrep -f 'python.*main.py')")
    print(f"\n  {NEGRITO}Ver o que está acontecendo{RESET}")
    print("    tail -f userbot.log" if not _IS_WINDOWS else "    Get-Content userbot.log -Wait")

    print(f"\n  {NEGRITO}Primeiros comandos{RESET} {CINZA}(digite no Telegram, em qualquer conversa){RESET}")
    print(f"    {p}alive    — confirma que está no ar")
    print(f"    {p}menu     — lista tudo que ele sabe fazer")
    print(f"    {p}versao   — mostra a build e se há atualização")

    print(f"\n  {CINZA}O firewall de PV e o encaminhamento de mensagens vêm desligados.{RESET}")
    print(f"  {CINZA}Ligue com {p}pmpermit on e {p}monitor on se quiser usá-los.{RESET}\n")


# ══════════════════════════════════════════════════════════════════════════════
def main():
    cabecalho()

    # ── [1/4] Requisitos ─────────────────────────────────────────────────────
    secao(1, "Requisitos")
    py = sys.version_info
    if py < (3, 10):
        erro(f"Python {py.major}.{py.minor} é antigo demais. O AxonBot precisa de 3.10 ou mais novo.")
        if _IS_ANDROID:
            info("No Termux: pkg upgrade && pkg install python")
        elif _IS_LINUX:
            info("Ubuntu/Debian: sudo apt install python3.11")
        sys.exit(1)
    ok(f"Python {py.major}.{py.minor}.{py.micro}")

    if subprocess.run(["git", "--version"], capture_output=True).returncode == 0:
        ok("Git — atualização por ,atualizar disponível")
    else:
        aviso("Git não encontrado — ,atualizar não vai funcionar (o resto sim).")

    # ── [2/4] Dependências ───────────────────────────────────────────────────
    secao(2, "Dependências")
    if faltando := verificar_libs():
        if confirmar("Instalar agora?"):
            if not instalar_libs(faltando):
                if not confirmar("Continuar mesmo assim?", padrao=False):
                    print(f"\n{VERMELHO}  Setup interrompido.{RESET}\n")
                    return
        else:
            aviso("Sem elas o bot não sobe. Rode: pip install -r requirements.txt")

    # ── [3/4] Credenciais ────────────────────────────────────────────────────
    secao(3, "Credenciais do Telegram")

    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                atual = json.load(f)
            aviso("Já existe um config.json:")
            info(f"API_ID {atual.get('API_ID', '?')} · prefixo '{atual.get('PREFIXO', ',')}' · "
                 f"idioma {atual.get('LANGUAGE', 'pt').upper()} · "
                 f"Drive {'ligado' if atual.get('ID_PASTA_RAIZ_DRIVE') else 'desligado'}")
        except Exception:
            aviso("config.json existe, mas está ilegível.")
            atual = {}

        if not confirmar("Refazer a configuração do zero?", padrao=False):
            ok("Mantendo o que já estava configurado.")
            instrucoes_finais(atual)
            return

    try:
        config = configurar()
    except KeyboardInterrupt:
        print(f"\n\n{AMARELO}  Setup cancelado.{RESET}\n")
        return

    # ── [4/4] Google Drive ───────────────────────────────────────────────────
    secao(4, "Google Drive (opcional)")
    try:
        config = configurar_drive(config)
    except KeyboardInterrupt:
        info("Drive ignorado.")

    try:
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        ok("config.json salvo.")
    except Exception as e:
        erro(f"Não consegui salvar o config.json: {e}")
        return

    # ── [5/5] Login ──────────────────────────────────────────────────────────
    secao(5, "Entrar na sua conta do Telegram")
    try:
        logado = fazer_login(config)
    except KeyboardInterrupt:
        logado = False

    instrucoes_finais(config, logado)


if __name__ == "__main__":
    main()
