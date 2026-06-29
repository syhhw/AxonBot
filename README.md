<div align="center">
  <img src="https://img.shields.io/badge/Telegram-AxonBot-blue?style=for-the-badge&logo=telegram" alt="Telegram AxonBot">
  <img src="https://img.shields.io/badge/Python-3.10+-yellow?style=for-the-badge&logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Pyrogram-v2.0+-green?style=for-the-badge" alt="Pyrogram">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Termux-lightgrey?style=for-the-badge" alt="Platforms">
</div>

<br>

<div align="center">
  <a href="#-userbot-pro-v23--english">🇺🇸 English</a> &nbsp;|&nbsp; <a href="#-userbot-pro-v23--português">🇧🇷 Português</a>
</div>

---

# 🇺🇸 AXONBOT v2.4 — English

**AxonBot** is an advanced personal assistant for Telegram built with [Pyrogram](https://docs.pyrogram.org/). It runs directly on your account, automating tasks, moderating groups, cloning stickers, integrating AI, and backing up files to Google Drive — all from a simple command in the chat.

Runs natively on **Windows**, **Linux** (Ubuntu/Debian/servers), and **Android** (Termux). No virtual environment needed.

---

## ✨ Features

| | Feature |
|---|---|
| 🧠 | **Gemini AI** — ask questions and summarize conversations |
| ☁️ | **Google Drive** — upload Telegram files, search, organize and manage your cloud storage |
| 🛡️ | **Moderation** — ban, mute, purge, remove zombie accounts, global ban |
| 🔒 | **PM Firewall** — math captcha for unauthorized private messages, AFK auto-reply |
| 🎭 | **Stickers** — auto-kang (steal and create packs autonomously) |
| ⬇️ | **Downloader** — YouTube, Instagram, TikTok via `yt-dlp` |
| 🔄 | **Auto-update** — pull latest version from GitHub and restart with one command |
| 🔌 | **Dynamic plugins** — hot-install new plugins from a URL |
| 🌐 | **Bilingual** — English and Portuguese, toggle anytime |

---

## 📋 Requirements

- **Python 3.10+**
- **Git**
- A Telegram account with `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
- A private channel or group to receive bot logs (you'll need its ID)

---

## 📥 Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/syhhw/userbot.git
cd userbot
```

### Step 2 — Run the interactive setup

The setup script auto-detects your platform, checks Python version, installs all dependencies, and guides you through the configuration.

**Windows:**
```cmd
python setup.py
```

**Linux / Termux:**
```bash
python3 setup.py
```

> **Note for Ubuntu/Debian:** The script automatically handles the `--break-system-packages` restriction from Python 3.12+. No manual workaround needed.

> **Note for Termux:** Make sure you have Python and Git installed first:
> ```bash
> pkg update && pkg install python git
> ```

### Step 3 — Follow the prompts

The setup will ask for:
1. `API_ID` and `API_HASH` — from [my.telegram.org](https://my.telegram.org)
2. **Log channel ID** — a private channel/group where the bot sends system alerts (format: `-1001234567890`)
3. **Command prefix** — default is `,` (comma)
4. **Language** — `pt` (Portuguese) or `en` (English)
5. *(Optional)* Google Gemini API key — free at [aistudio.google.com](https://aistudio.google.com/app/apikey)
6. *(Optional)* Google Drive setup

---

## 🚀 Starting the Bot

**Windows (foreground):**
```cmd
python main.py
```

**Linux / Termux (foreground):**
```bash
python3 main.py
```

**Linux — background (stays running after closing the terminal):**
```bash
nohup python3 main.py --background > userbot.log 2>&1 &
```

**Linux — with screen (recommended for servers):**
```bash
screen -S userbot
python3 main.py
# Press Ctrl+A, D to detach
```

**View logs:**
```bash
tail -f userbot.log
```

**Stop the bot:**
```bash
kill $(pgrep -f 'python.*main.py')
```

> On first run, the bot will log in to your Telegram account (enter your phone number and the code). This session is saved locally — you won't need to log in again.

---

## 📚 Commands

Type `,menu` in any chat to see all commands grouped by module.

### 🖥️ System
| Command | Description |
|:---|:---|
| `,menu` | List all available commands by module |
| `,version` | Check local vs remote version on GitHub |
| `,update` | Pull latest updates from Git and restart |
| `,restart` | Restart the bot process |
| `,ping` | Measure bot latency |
| `,lang [pt/en]` | Switch language |
| `,sysinfo` | Full neofetch: CPU, GPU, RAM, Swap, Disk, Net |
| `,speed` | Run internet speed test |
| `,shutdown` | Gracefully shut down the bot |

### 👮 Moderation
| Command | Description |
|:---|:---|
| `,ban` / `,unban` | Ban or unban a user |
| `,mute` / `,unmute` | Mute or unmute a user |
| `,del` | Delete the replied message |
| `,purge` | Delete all messages from the replied one to the command |
| `,zombies` | Remove deleted accounts from the group |
| `,gban` | Ban a user across all your admin groups |
| `,fban` | Ban a user across all federation groups |
| `,admins` | List all group admins |

### 👤 Account & AFK
| Command | Description |
|:---|:---|
| `,afk [reason]` | Activate AFK mode with auto-reply |
| `,unafk` | Deactivate AFK mode manually |
| `,permit` | Authorize a user to send you private messages |

### 🧠 AI (Gemini)
| Command | Description |
|:---|:---|
| `,ask [question]` | Ask anything to Google Gemini |
| `,summarize` | Summarize the last 50 messages in bullet points |

### 🎭 Stickers
| Command | Description |
|:---|:---|
| `,kang [emoji]` | Reply to a sticker/photo to steal it into your pack |
| `,packinfo` | List your sticker packs with links |

### ⬇️ Downloader
| Command | Description |
|:---|:---|
| `,dl [url]` | Download video from YouTube, Instagram, TikTok |

### 📂 Google Drive
| Command | Description |
|:---|:---|
| `,status` | Show Drive usage (space bar) |
| `,get [url]` | Download a file from a URL directly to Drive |
| `,direct` | Reply to a Telegram file to upload it to Drive |
| `,search [name]` | Search files in your Drive |
| `,delete [N]` | Delete file from search results |
| `,organize` | Sort root folder files into category subfolders |

### ⚙️ Developer
| Command | Description |
|:---|:---|
| `,eval [code]` | Execute Python code dynamically |
| `,term [command]` | Run a shell/terminal command and return output |
| `,install [url]` | Install a `.py` plugin from a URL |
| `,uninstall [name]` | Remove an installed plugin |

### ⚡ Triggers
| Command | Description |
|:---|:---|
| `,addtrigger "word" "reply"` | Add an auto-reply trigger |
| `,deltrigger "word"` | Remove a trigger |
| `,triggers` | List all active triggers |

---

## 🔑 Optional Integrations

### Google Gemini AI
1. Get a free API key at [aistudio.google.com](https://aistudio.google.com/app/apikey)
2. During `setup.py`, paste it when asked — or add it manually to `config.json`:
```json
"GEMINI_API_KEY": "your-key-here"
```

### Google Drive
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable the **Google Drive API**
3. Go to **Credentials** → Create Credential → **OAuth 2.0 Client ID**
4. Application type: **Desktop app**
5. Download the JSON and save it as **`client_secrets.json`** in the bot's root folder
6. Run `setup.py` and choose Drive setup — or restart the bot; it will auto-detect the file
7. On first run with Drive enabled, a browser window will open to authorize — after that it saves automatically to `meu_drive.json`

---

## 🛡️ PM Firewall

When an unknown user messages you in private, the bot intercepts and sends a **math captcha**. Only after solving it does the conversation reach you. Use `,permit` in the user's chat to bypass it manually.

---

## ⚠️ Disclaimer

This project is for educational purposes only. AxonBot usage is not officially supported by Telegram's Terms of Service. Heavy automation or spam may result in account restrictions. **Use responsibly.**

---

# 🇧🇷 AXONBOT v2.4 — Português

O **AxonBot** é um assistente pessoal avançado para Telegram construído com [Pyrogram](https://docs.pyrogram.org/). Ele roda diretamente na sua conta, automatizando tarefas, moderando grupos, clonando figurinhas, integrando IA e fazendo backup no Google Drive — tudo por um comando simples no chat.

Funciona nativamente no **Windows**, **Linux** (Ubuntu/Debian/servidores) e **Android** (Termux). Sem ambiente virtual obrigatório.

---

## ✨ Funcionalidades

| | Funcionalidade |
|---|---|
| 🧠 | **Gemini IA** — faça perguntas e resuma conversas |
| ☁️ | **Google Drive** — envie arquivos do Telegram, pesquise, organize e gerencie sua nuvem |
| 🛡️ | **Moderação** — ban, mute, purge, remover zumbis, banimento global |
| 🔒 | **Firewall de PV** — captcha matemático para mensagens privadas não autorizadas, auto-resposta AFK |
| 🎭 | **Figurinhas** — kang automático (rouba e cria pacotes sozinho) |
| ⬇️ | **Downloader** — YouTube, Instagram, TikTok via `yt-dlp` |
| 🔄 | **Auto-atualização** — puxa a versão mais recente do GitHub com um comando |
| 🔌 | **Plugins dinâmicos** — instale novos plugins por URL sem reiniciar manualmente |
| 🌐 | **Bilíngue** — Português e Inglês, troque a qualquer momento |

---

## 📋 Requisitos

- **Python 3.10+**
- **Git**
- Uma conta do Telegram com `API_ID` e `API_HASH` obtidos em [my.telegram.org](https://my.telegram.org)
- Um canal ou grupo privado seu para receber os logs do bot (você vai precisar do ID)

---

## 📥 Instalação

### Passo 1 — Clone o repositório

```bash
git clone https://github.com/syhhw/userbot.git
cd userbot
```

### Passo 2 — Execute o setup interativo

O setup detecta sua plataforma automaticamente, verifica o Python, instala todas as dependências e guia você pela configuração.

**Windows:**
```cmd
python setup.py
```

**Linux / Termux:**
```bash
python3 setup.py
```

> **Nota para Ubuntu/Debian:** O script trata automaticamente a restrição `--break-system-packages` do Python 3.12+. Não é preciso fazer nada manualmente.

> **Nota para Termux:** Certifique-se de ter Python e Git instalados antes:
> ```bash
> pkg update && pkg install python git
> ```

### Passo 3 — Siga as perguntas na tela

O setup vai pedir:
1. `API_ID` e `API_HASH` — em [my.telegram.org](https://my.telegram.org)
2. **ID do canal de logs** — um canal/grupo privado seu onde o bot manda alertas do sistema (formato: `-1001234567890`)
3. **Prefixo dos comandos** — padrão é `,` (vírgula)
4. **Idioma** — `pt` (Português) ou `en` (Inglês)
5. *(Opcional)* Chave do Google Gemini — grátis em [aistudio.google.com](https://aistudio.google.com/app/apikey)
6. *(Opcional)* Configuração do Google Drive

---

## 🚀 Iniciando o Bot

**Windows (primeiro plano):**
```cmd
python main.py
```

**Linux / Termux (primeiro plano):**
```bash
python3 main.py
```

**Linux — segundo plano (continua após fechar o terminal):**
```bash
nohup python3 main.py --background > userbot.log 2>&1 &
```

**Linux — com screen (recomendado para servidores):**
```bash
screen -S userbot
python3 main.py
# Pressione Ctrl+A, D para desanexar
```

**Ver logs em tempo real:**
```bash
tail -f userbot.log
```

**Parar o bot:**
```bash
kill $(pgrep -f 'python.*main.py')
```

> Na primeira execução, o bot vai fazer login na sua conta do Telegram (número de telefone + código). Essa sessão é salva localmente — você não precisará logar de novo.

---

## 📚 Comandos

Digite `,menu` em qualquer chat para ver todos os comandos agrupados por módulo.

### 🖥️ Sistema
| Comando | Descrição |
|:---|:---|
| `,menu` | Lista todos os comandos disponíveis por módulo |
| `,versao` | Verifica versão local vs remota no GitHub |
| `,atualizar` | Baixa as atualizações do Git e reinicia |
| `,restart` | Reinicia o processo do bot |
| `,ping` | Mede a latência do bot |
| `,idioma [pt/en]` | Muda o idioma do bot |
| `,sysinfo` | Neofetch completo: CPU, GPU, RAM, Swap, Disco, Rede |
| `,speed` | Testa a velocidade da internet |
| `,desligar` | Encerra o bot com segurança |

### 👮 Moderação
| Comando | Descrição |
|:---|:---|
| `,ban` / `,unban` | Bane ou desbane um usuário |
| `,mute` / `,unmute` | Silencia ou desmuta um usuário |
| `,del` | Apaga a mensagem respondida |
| `,purge` | Apaga todas as mensagens a partir da respondida |
| `,zombies` | Remove contas deletadas do grupo |
| `,gban` | Bane um usuário em todos os seus grupos admin |
| `,fban` | Bane um usuário em todos os grupos da federação |
| `,admins` | Lista todos os admins do grupo |

### 👤 Conta & AFK
| Comando | Descrição |
|:---|:---|
| `,afk [motivo]` | Ativa o modo AFK com auto-resposta |
| `,unafk` | Desativa o AFK manualmente |
| `,permit` | Autoriza um usuário a te enviar mensagens privadas |

### 🧠 IA (Gemini)
| Comando | Descrição |
|:---|:---|
| `,perguntar [pergunta]` | Pergunta qualquer coisa ao Google Gemini |
| `,resumir` | Resume as últimas 50 mensagens do chat em tópicos |

### 🎭 Figurinhas
| Comando | Descrição |
|:---|:---|
| `,kang [emoji]` | Responda a uma figurinha/foto para roubá-la pro seu pacote |
| `,packinfo` | Lista seus pacotes de figurinhas com links |

### ⬇️ Downloader
| Comando | Descrição |
|:---|:---|
| `,dl [url]` | Baixa vídeo do YouTube, Instagram, TikTok |

### 📂 Google Drive
| Comando | Descrição |
|:---|:---|
| `,status` | Mostra uso do Drive (barra de espaço) |
| `,get [url]` | Baixa um arquivo de uma URL direto para o Drive |
| `,direto` | Responda a um arquivo do Telegram para subir no Drive |
| `,procurar [nome]` | Pesquisa arquivos no seu Drive |
| `,apagar [N]` | Apaga arquivo dos resultados da busca |
| `,organizar` | Organiza os arquivos da pasta raiz em subpastas por tipo |

### ⚙️ Desenvolvedor
| Comando | Descrição |
|:---|:---|
| `,eval [código]` | Executa código Python dinamicamente |
| `,term [comando]` | Executa um comando no terminal e retorna a saída |
| `,instalar [url]` | Instala um plugin `.py` a partir de uma URL |
| `,desinstalar [nome]` | Remove um plugin instalado |

### ⚡ Gatilhos
| Comando | Descrição |
|:---|:---|
| `,addtrigger "palavra" "resposta"` | Adiciona uma auto-resposta por gatilho |
| `,deltrigger "palavra"` | Remove um gatilho |
| `,triggers` | Lista todos os gatilhos ativos |

---

## 🔑 Integrações Opcionais

### Google Gemini IA
1. Crie uma chave grátis em [aistudio.google.com](https://aistudio.google.com/app/apikey)
2. Durante o `setup.py`, cole quando solicitado — ou adicione manualmente ao `config.json`:
```json
"GEMINI_API_KEY": "sua-chave-aqui"
```

### Google Drive
1. Acesse o [Google Cloud Console](https://console.cloud.google.com)
2. Crie um projeto → Ative a **Google Drive API**
3. Vá em **Credenciais** → Criar Credencial → **ID do cliente OAuth 2.0**
4. Tipo de aplicativo: **App para computador**
5. Baixe o JSON e salve como **`client_secrets.json`** na pasta raiz do bot
6. Execute `setup.py` e escolha configurar o Drive — ou reinicie o bot, ele detecta o arquivo automaticamente
7. Na primeira execução com Drive ativado, uma janela do navegador abrirá para autorizar — depois disso a sessão é salva automaticamente em `meu_drive.json`

---

## 🛡️ Firewall de PV

Quando um usuário desconhecido te manda mensagem privada, o bot intercepta e envia um **captcha matemático**. Só após resolver é que a conversa chega até você. Use `,permit` no chat do usuário para liberar manualmente.

---

## ⚠️ Aviso Legal

Este projeto é apenas para fins educacionais. O uso de userbots não é oficialmente suportado pelos Termos de Serviço do Telegram. Automação massiva ou spam pode resultar em restrições na sua conta. **Use com responsabilidade.**

---

<div align="center">
  Desenvolvido com ❤️ &nbsp;|&nbsp; <b>AxonBot v2.4</b>
</div>
