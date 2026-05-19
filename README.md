<div align="center">
  <img src="https://img.shields.io/badge/Telegram-Userbot-blue?style=for-the-badge&logo=telegram" alt="Telegram Userbot">
  <img src="https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge&logo=python" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Pyrogram-v2.0+-green?style=for-the-badge" alt="Pyrogram">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Termux-lightgrey?style=for-the-badge" alt="Platforms">
</div>

<br>

# 🚀 USERBOT PRO v2.1

O **Userbot Pro** é um assistente pessoal avançado para Telegram construído com [Pyrogram](https://docs.pyrogram.org/). Ele roda diretamente na sua conta, automatizando tarefas, moderando grupos, clonando figurinhas, integrando Inteligência Artificial e até fazendo backup no seu Google Drive!

Totalmente adaptado para rodar de forma invisível no **Windows**, servidores **Linux** (Ubuntu/Debian) e até no **Termux** pelo celular.

---

## ✨ Destaques e Funcionalidades

- 🧠 **Inteligência Artificial:** Integrado nativamente com a IA do Google Gemini (Resumos de chat e perguntas).
- ☁️ **Google Drive:** Baixe arquivos da web direto para o Drive, pesquise arquivos, organize pastas e gerencie seu armazenamento pelo Telegram.
- 👻 **Background Invisível:** Suporte nativo para rodar em segundo plano, seja usando `nohup` (Linux) ou processos desanexados sem janela (`pythonw.exe`) no Windows.
- 🛡️ **Moderação e Segurança:** Captcha automático para quem te chama no privado (PV), GBAN (Banimento Global em seus grupos), limpeza de contas deletadas (zumbis).
- 🎭 **Diversão e Ferramentas:** Kang automático de figurinhas (cria pacotes sozinho), clonagem de perfil, downloads universais (TikTok, YouTube, Insta) via `yt-dlp`.
- 🔄 **Auto-Atualização:** Atualize o bot com um simples comando `,atualizar` via GitHub. Ele baixa as dependências e reinicia sozinho.

---

## 🛠️ Pré-requisitos

Antes de instalar, você precisará de:
1. **Python 3.8** ou superior instalado no seu sistema.
2. **Git** instalado.
3. Suas credenciais do Telegram (`API_ID` e `API_HASH`). Você pode obtê-las em my.telegram.org.

---

## 📥 Instalação (Passo a Passo)

O Userbot Pro possui um instalador interativo inteligente que cuida de quase tudo para você!

### Passo 1: Clonar o Repositório
Abra seu terminal (CMD, PowerShell, Bash ou Termux) e digite:
```bash
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd SEU_REPOSITORIO
```
*(Lembre-se de alterar o link para a URL real do seu repositório no GitHub)*

### Passo 2: Executar o Setup Inteligente
Inicie o script de configuração. Ele criará o ambiente virtual (venv) automaticamente e instalará as bibliotecas necessárias.

**No Windows:**
```cmd
python setup.py
```

**No Linux / Termux:**
```bash
python3 setup.py
```

### Passo 3: Siga as Instruções na Tela
O terminal fará algumas perguntas interativas:
1. Insira seu `API_ID` e `API_HASH`.
2. Insira o ID de um grupo/canal privado seu para receber os logs (adicione `-100` no início).
3. Escolha o seu prefixo de comandos (o padrão é a vírgula `,`).
4. *(Opcional)* Configure a API Key do Google Gemini.
5. *(Opcional)* Configure o Google Drive.

---

## 🚀 Iniciando o Bot

Após o setup ser concluído com sucesso, basta rodar o bot:

**No Windows:**
```cmd
python main.py
```

**No Linux / Termux:**
```bash
python3 main.py
```

> 💡 **Dica:** Logo ao abrir, o bot perguntará se você deseja rodar em **Primeiro Plano** ou **Segundo Plano**. Se escolher Segundo Plano (`S`), o bot se tornará invisível e você poderá fechar o terminal tranquilamente!

---

## 📚 Principais Comandos

O prefixo padrão é `,` (vírgula). Digite `,menu` em qualquer chat para ver todos os comandos disponíveis categorizados!

### 🖥️ Sistema
| Comando | Descrição |
| :--- | :--- |
| `,menu` | Exibe todos os módulos e comandos dinamicamente. |
| `,versao` | Mostra se o bot está atualizado com o GitHub. |
| `,atualizar` | Baixa as últimas atualizações do Git e reinicia. |
| `,restart` | Reinicia o processo do Userbot. |
| `,ping` | Verifica a latência (ping) do bot no Telegram. |
| `,sysinfo` | Mostra os recursos usados (CPU, RAM, OS). |

### 👮 Moderação
| Comando | Descrição |
| :--- | :--- |
| `,ban` / `,unban` | Bane ou desbane um usuário do grupo. |
| `,purge` | Apaga todas as mensagens a partir da que você respondeu. |
| `,zombies` | Remove contas deletadas (fantasmas) do grupo atual. |
| `,gban` / `,fban` | Bane o alvo globalmente (em todos os seus grupos) ou nas Federações. |

### 🎭 Ferramentas & Diversão
| Comando | Descrição |
| :--- | :--- |
| `,kang` | Responda a uma figurinha para roubá-la e adicioná-la ao seu pacote. |
| `,clone` | Clona o nome, bio e foto de perfil do usuário respondido. |
| `,reverter`| Restaura seu perfil original após usar o clone. |
| `,voz pt Texto` | Converte um texto em áudio e envia no chat. |
| `,dl [url]` | Baixa vídeos do YouTube, Instagram, TikTok diretamente. |

### 🧠 Inteligência Artificial (Gemini)
| Comando | Descrição |
| :--- | :--- |
| `,ask [texto]` | Faz uma pergunta ou pede algo para o Google Gemini. |
| `,resumir` | Lê as últimas 50 mensagens do chat e gera um resumo em tópicos. |

### 📂 Google Drive
| Comando | Descrição |
| :--- | :--- |
| `,status` | Mostra o espaço livre/usado no seu Drive. |
| `,get [url]` | Faz o download de um arquivo direto para a nuvem. |
| `,procurar [nome]`| Pesquisa arquivos no seu Drive e permite apagá-los ou gerar links diretos. |

---

## 🛡️ Firewall de PV (AFK e Captcha)

O Userbot Pro protege sua paz. Se alguém não autorizado tentar te enviar uma mensagem privada, o bot interceptará a mensagem e enviará um **Captcha matemático**.
- Se o usuário acertar, o PV é liberado automaticamente.
- Para liberar manualmente, use o comando `,permit` no chat do usuário.
- Use `,afk [motivo]` para deixar um aviso automático quando estiver ausente. O AFK sai sozinho assim que você enviar qualquer mensagem.

---

## 🔑 Configurando a IA e o Drive (Opcional)

### Google Gemini (IA)
1. Acesse o Google AI Studio e gere uma API Key gratuita.
2. Abra o arquivo `config.json` e adicione a chave na opção `"GEMINI_API_KEY"`.

### Google Drive
1. Crie um projeto no Google Cloud Console.
2. Ative a **Google Drive API**.
3. Crie credenciais OAuth 2.0 (Tipo: Desktop Application).
4. Baixe o arquivo JSON, renomeie para `client_secrets.json` e coloque na pasta raiz do Userbot.
5. Edite o `config.json` deixando `"DRIVE_ATIVO": true` e coloque o ID da pasta do Drive em `"ID_PASTA_RAIZ_DRIVE"`.
6. Ao reiniciar o bot, ele pedirá para autorizar no navegador (apenas na primeira vez).

---

## ⚠️ Aviso Legal

Este projeto é apenas para fins educacionais. O uso de "Userbots" não é oficialmente suportado pelos Termos de Serviço do Telegram. A automação massiva de envio de mensagens ou spam pode resultar no banimento da sua conta.

**Use por sua conta e risco! Não utilize o bot para prejudicar outros usuários.**

---

<div align="center">
  Desenvolvido com ❤️ | <b>Userbot Pro v2.1</b>
</div>