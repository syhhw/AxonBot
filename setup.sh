#!/bin/bash
# Setup de dependências do sistema para Linux (Ubuntu/Debian) e Termux

echo -e "\033[94m╔════════════════════════════════════════════╗\033[0m"
echo -e "\033[94m║   ⚙️  PREPARANDO DEPENDÊNCIAS DO SISTEMA    ║\033[0m"
echo -e "\033[94m╚════════════════════════════════════════════╝\033[0m\n"

if command -v apt-get &> /dev/null; then
    echo -e "\033[93m▶ Ubuntu/Debian detectado. Atualizando pacotes via apt...\033[0m"
    sudo apt-get update -y -q
    sudo apt-get install -y python3 python3-pip python3-venv git ffmpeg neofetch libwebp-dev
elif command -v pkg &> /dev/null; then
    echo -e "\033[93m▶ Termux detectado. Atualizando pacotes via pkg...\033[0m"
    pkg update -y
    pkg install -y python git ffmpeg neofetch libwebp
else
    echo -e "\033[91m⚠️ Gerenciador de pacotes (apt/pkg) não encontrado.\033[0m"
    echo "Por favor, instale o Python3, Git e FFmpeg manualmente."
fi

echo -e "\n\033[92m✅ Dependências do sistema prontas!\033[0m\n"