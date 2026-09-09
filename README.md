<div align="center">

# ⚡ AxonBot

**Um userbot de Telegram que roda na sua própria conta.**
87 comandos: moderação, download, figurinhas, IA, Google Drive e automação — tudo por mensagem, sem app extra.

<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+">
<img src="https://img.shields.io/badge/Pyrogram-2.0+-red?style=flat-square" alt="Pyrogram 2.0+">
<img src="https://img.shields.io/badge/Windows%20·%20Linux%20·%20Termux-lightgrey?style=flat-square" alt="Plataformas">

</div>

---

## O que é um userbot

Um bot comum é uma conta separada, criada no @BotFather, que só enxerga o que mandam pra ele.

Um **userbot** é diferente: ele se conecta como **você**. Os comandos são mensagens que *você* escreve, em qualquer conversa, e o bot edita a própria mensagem com a resposta. Ninguém precisa te adicionar em nada — onde você está, ele está.

> [!WARNING]
> Automatizar uma conta pessoal é tolerado pelo Telegram, mas **spam derruba conta**. Não use `,mencionar` a cada cinco minutos, não use `,gban` como brincadeira e não saia mandando PV em massa. A conta é sua, o risco é seu.

---

## Instalação

Precisa de **Python 3.10 ou mais novo** e **Git**.

```bash
git clone https://github.com/syhhw/AxonBot.git
cd AxonBot
python setup.py
```

O `setup.py` cuida de tudo em 5 etapas: confere o Python, instala as dependências, pergunta as credenciais, oferece o Google Drive e faz seu login no Telegram. No fim ele te diz exatamente como iniciar.

<details>
<summary><b>Linux e Termux — dependências do sistema</b></summary>

Alguns recursos (converter vídeo, gerar figurinha) precisam de `ffmpeg` e `libwebp`. Rode antes do setup:

```bash
bash setup.sh
```

Se o `pip` reclamar de *externally-managed-environment* (Debian 12+, Ubuntu 24.04+), o setup já contorna sozinho com `--break-system-packages`. Preferindo isolar:

```bash
python3 -m venv venv && source venv/bin/activate
```

</details>

---

## Configuração

Tudo mora num único `config.json`, criado pelo setup. Você **não precisa editar nada à mão** — mas aqui está o que cada campo significa, caso queira mexer depois.

| Campo | Obrigatório | O que é |
|---|:---:|---|
| `API_ID` | **sim** | Número que identifica seu app no Telegram |
| `API_HASH` | **sim** | Chave secreta que vem junto do `API_ID` |
| `PREFIXO` | não | Caractere que inicia os comandos. Padrão: `,` |
| `LANGUAGE` | não | `pt` ou `en`. Padrão: `pt` |
| `ID_CANAL_LOGS` | não | Canal privado onde o bot registra o que acontece |
| `GEMINI_API_KEY` | não | Libera `,perguntar` e `,resumir` |
| `ID_PASTA_RAIZ_DRIVE` | não | Pasta do Google Drive usada como raiz |
| `LIMITE_AUTO_UPLOAD` | não | Tamanho máximo, em bytes, do envio automático pro Drive |

### 1. API_ID e API_HASH — os únicos itens obrigatórios

São as chaves que provam que o app é seu. O Telegram dá de graça:

1. Abra **[my.telegram.org](https://my.telegram.org)** e entre com o seu número
2. Clique em **API development tools**
3. Preencha qualquer nome de app (`axonbot` serve) e qualquer plataforma
4. Copie o **`api_id`** (números) e o **`api_hash`** (letras e números)

> [!CAUTION]
> Essas duas chaves dão acesso à sua conta. Elas ficam só no `config.json`, que o `.gitignore` já bloqueia — **nunca** poste print delas nem suba o arquivo pro GitHub.

### 2. Prefixo

O caractere que transforma uma mensagem sua em comando. Com o padrão `,`, você digita `,ping`.

Escolha algo que você **não usa escrevendo normalmente**. Vírgula funciona bem porque ninguém começa frase com vírgula. Evite `/`, que é o prefixo dos bots comuns e ia conflitar em grupos.

### 3. Canal de logs (opcional)

Um canal privado só seu onde o bot avisa que ligou, reporta erros e registra cada moderação — útil pra saber o que aconteceu enquanto você não estava olhando.

1. No Telegram, crie um **canal** (não grupo) e deixe como privado
2. Mande qualquer mensagem nele
3. Encaminhe essa mensagem para **[@userinfobot](https://t.me/userinfobot)**
4. Ele responde com o ID do canal, algo como `-1001234567890` — cole no setup

Pulando essa etapa, o bot funciona igual: ele só deixa de ter onde escrever o histórico.

### 4. Login no Telegram

Na última etapa o setup pede seu telefone e o código que o Telegram manda no app. Se você usa verificação em duas etapas, ele pede a senha também.

Isso cria o arquivo `meu_userbot.session` — é ele que mantém você logado. Trate como senha: **quem tiver esse arquivo entra na sua conta.** Ele também já está no `.gitignore`.

### Reconfigurar depois

Rodar `python setup.py` de novo mostra o que já está salvo e pergunta se você quer refazer. Para trocar só o idioma, nem precisa: `,idioma en` resolve na hora.

---

## Rodando

```bash
python main.py
```

No primeiro start ele fica em primeiro plano de propósito — o login precisa do terminal. Depois disso, ele passa a perguntar como você quer rodar:

- **Segundo plano** — continua vivo depois que você fechar o terminal. É o que você quer numa VPS.
- **Primeiro plano** — para junto com o terminal. Bom pra ver erro acontecendo.

| | Linux / Termux | Windows |
|---|---|---|
| **Parar** | `kill $(pgrep -f 'python.*main.py')` | `taskkill /F /IM pythonw.exe` |
| **Ver logs** | `tail -f userbot.log` | `Get-Content userbot.log -Wait` |

Confirme que funcionou digitando **`,alive`** em qualquer conversa do Telegram. Depois **`,menu`** pra ver tudo.

---

## Comandos

São 87, em 25 módulos. `,menu` lista as categorias; `,menu mod` abre uma delas.

Os comandos têm nome em português e em inglês — `,atualizar` e `,update` fazem a mesma coisa, independente do idioma configurado.

<details open>
<summary><b>🖥️ Sistema</b></summary>

| Comando | O que faz |
|---|---|
| `,alive` | Confirma que está no ar: uptime, build, versões |
| `,setalive` · `,delalive` | Define ou remove a mídia mostrada no `,alive` |
| `,versao` | Build local, remota e se há atualização |
| `,atualizar` | Baixa a última versão do GitHub e reinicia |
| `,reiniciar` · `,desligar` | Reinicia ou encerra o userbot |
| `,logs [n]` | Últimas linhas do `userbot.log` |
| `,sysinfo` | CPU, GPU, RAM, disco e rede da máquina |
| `,ping` | Latência |
| `,idioma pt\|en` | Troca o idioma |
| `,menu [módulo]` | Lista os comandos |
| `,id` | ID do chat, do usuário ou da mensagem |
| `,stats` | Estatísticas da sua conta (grupos, canais, contatos) |
| `,eval` | Executa Python no contexto do bot |

</details>

<details>
<summary><b>👮 Moderação</b></summary>

| Comando | O que faz |
|---|---|
| `,ban` · `,unban` | Bane e desbane no grupo |
| `,mute` · `,unmute` | Silencia e libera |
| `,gban` | Bane em todos os grupos onde você é admin |
| `,fban` · `,addfed` · `,delfed` · `,feds` | Banimento por federação de grupos |
| `,admins` | Lista os administradores |
| `,zombies` | Remove contas deletadas (pede confirmação) |
| `,fixar` · `,desafixar` | Fixa e desafixa mensagem |
| `,purge` · `,del` · `,purgeme` | Apaga mensagens em lote, uma, ou só as suas |
| `,sd 10 texto` | Manda mensagem que se autodestrói |
| `,travar` · `,destravar` · `,travas` | Trava tipos de conteúdo no grupo |
| `,setflood` · `,noflood` · `,flood` | Antiflood por grupo |
| `,addfiltro` · `,delfiltro` · `,filtros` | Respostas automáticas por palavra |
| `,nota` · `,delnota` · `,notas` | Notas salvas do grupo |
| `,setbemvindo` · `,delbemvindo` · `,bemvindo` | Boas-vindas a quem entra |
| `,addtrigger` · `,deltrigger` · `,triggers` | Gatilhos de resposta |
| `,mencionar` | Menciona todo mundo, em lotes de 5 |

</details>

<details>
<summary><b>👤 Conta e privacidade</b></summary>

| Comando | O que faz |
|---|---|
| `,afk [motivo]` · `,unafk` | Responde sozinho enquanto você está fora |
| `,pmpermit on\|off` | Firewall de mensagens privadas |
| `,captcha on\|off\|math\|palavra\|emoji` | Desafio pra quem te manda PV |
| `,permit` · `,unpermit` · `,permitidos` | Autoriza, revoga e lista quem pode te mandar PV |
| `,monitor on\|off` | Encaminha PVs e menções pro canal de logs |
| `,setname` · `,setbio` · `,setpfp` · `,delpfp` | Edita seu perfil |

</details>

<details>
<summary><b>🛠️ Ferramentas, mídia e IA</b></summary>

| Comando | O que faz |
|---|---|
| `,dl` · `,dlinfo` | Baixa de YouTube, Instagram, TikTok e afins |
| `,kang` · `,packinfo` | Rouba figurinha pro seu pacote |
| `,tr [idioma]` | Traduz a mensagem respondida |
| `,voz [texto]` | Transforma texto em áudio |
| `,print` | Vira a mensagem respondida numa imagem |
| `,carbon` | Imagem estilizada de código |
| `,paste` | Sobe texto num pastebin e devolve o link |
| `,clima [cidade]` | Tempo agora e nos próximos 3 dias |
| `,encurtar [url]` · `,ipinfo` · `,specs` | Encurtador, dados de IP, ficha de celular |
| `,github user/repo` · `,filme [nome]` | Consulta GitHub e IMDb |
| `,ghost` | Mensagem que se apaga sozinha |
| `,perguntar` · `,resumir` | Pergunta à IA e resume as últimas 50 mensagens |
| `,status` · `,organizar` · `,get` · `,direto` · `,procurar` · `,apagar` | Google Drive |

</details>

---

## O que vem desligado

Recursos que afetam outras pessoas **começam desativados de propósito**. Uma instalação nova não bloqueia ninguém nem copia mensagem pra lugar nenhum:

| Recurso | Padrão | Ligue com |
|---|---|---|
| Firewall de PV | desligado | `,pmpermit on` |
| Encaminhar PVs e menções pro canal de logs | desligado | `,monitor on` |
| Antiflood, filtros, notas, boas-vindas, travas | desligado | configurados por grupo |

O bot **nunca** encaminha nem responde mensagens da conta oficial do Telegram (`777000`) — é de lá que vêm códigos de login, e mexer nisso pode travar o acesso à sua própria conta.

---

## Integrações opcionais

<details>
<summary><b>🧠 Google Gemini — libera <code>,perguntar</code> e <code>,resumir</code></b></summary>

1. Pegue uma chave grátis em **[aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)**
2. Cole no setup, ou adicione `"GEMINI_API_KEY": "sua-chave"` no `config.json`

</details>

<details>
<summary><b>☁️ Google Drive — envio e organização automática de arquivos</b></summary>

1. Abra o **[Google Cloud Console](https://console.cloud.google.com)**
2. Crie um projeto e ative a **Google Drive API**
3. **Credenciais → Criar credencial → ID do cliente OAuth**, tipo **Computador**
4. Baixe o JSON, renomeie para **`client_secrets.json`** e coloque na pasta do AxonBot
5. Rode `python setup.py` de novo e aceite configurar o Drive

Na primeira conexão o navegador abre pedindo autorização; depois disso o `meu_drive.json` guarda o acesso.

</details>

---

## Atualizando

```
,atualizar
```

Ele busca a última versão da branch, aplica e reinicia sozinho.

> [!NOTE]
> O `,atualizar` usa `git reset --hard`: qualquer alteração que você tenha feito nos arquivos é descartada. Se você mexe no código, use `git pull` na mão.

---

## Problemas comuns

<details>
<summary><b>O bot não sobe e o terminal fecha sozinho</b></summary>

Rode em primeiro plano pra ver o erro: responda **n** quando ele perguntar sobre segundo plano. Ou leia o `userbot.log`, que guarda tudo.

</details>

<details>
<summary><b>Escolhi segundo plano e o bot nunca ficou online</b></summary>

Costumava acontecer quando ainda não havia sessão salva: o login pede o código no terminal, e em segundo plano não existe terminal pra responder. Hoje o `main.py` detecta isso e força o primeiro plano até você logar. Se ainda acontecer, apague `meu_userbot.session` e rode `python main.py` de novo.

</details>

<details>
<summary><b><code>externally-managed-environment</code> ao instalar</b></summary>

É o Debian/Ubuntu novo protegendo o Python do sistema. O setup já contorna. Manualmente:

```bash
pip install -r requirements.txt --break-system-packages
```

</details>

<details>
<summary><b><code>UnicodeEncodeError</code> no Windows</b></summary>

Console antigo em cp1252 engasgando com acento. O `setup.py` e o `main.py` já forçam UTF-8 na saída. Se aparecer em outro script, rode antes:

```
chcp 65001
```

</details>

<details>
<summary><b><code>Conflict: terminated by other getUpdates</code> ou dois bots respondendo</b></summary>

Sobrou um processo antigo rodando. Pare todos e suba um só:

```bash
kill $(pgrep -f 'python.*main.py')     # Linux/Termux
taskkill /F /IM pythonw.exe            # Windows
```

</details>

<details>
<summary><b>Perdi o acesso / quero deslogar</b></summary>

Apague o `meu_userbot.session` e rode o setup de novo. Para revogar de qualquer lugar, use o próprio Telegram: **Configurações → Dispositivos → encerrar sessão**.

</details>

---

## 🇺🇸 English

AxonBot is a Telegram **userbot** — it runs on your own account, not on a separate bot account. You type commands as regular messages and it edits them in place with the answer.

**Install:**

```bash
git clone https://github.com/syhhw/AxonBot.git
cd AxonBot
python setup.py
```

The setup is interactive and walks you through everything: Python check, dependencies, credentials, optional Google Drive, and the Telegram login. Only `API_ID` and `API_HASH` are required — get them free at [my.telegram.org](https://my.telegram.org) under *API development tools*.

Then run `python main.py` and type `,alive` in any Telegram chat.

**The interface is bilingual.** Switch with `,idioma en` and every command answers in English. Command names work in both languages: `,atualizar` and `,update` are the same command. Type `,menu` for the full list.

Features that affect other people — the PM firewall and message forwarding — ship **disabled**. Enable them with `,pmpermit on` and `,monitor on`.

> **Warning:** automating a personal account is tolerated by Telegram, but spamming gets accounts banned. Your account, your risk.

---

<div align="center">
<sub>Feito com Pyrogram · Use com responsabilidade</sub>
</div>
