#!/bin/bash
# =====================================
# OnCabito Bot - Server Setup Script
# =====================================

set -e

echo "🚀 OnCabito Bot - Configuração do Servidor"
echo "=========================================="

# Variáveis
PROJECT_NAME="oncabito-gaming-bot"
DEPLOY_USER="oncabito"
DEPLOY_PATH="/home/$DEPLOY_USER/$PROJECT_NAME"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar se está rodando como root
if [[ $EUID -eq 0 ]]; then
   print_error "Este script não deve ser executado como root"
   exit 1
fi

echo "📦 1. Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

echo "🐳 2. Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    print_status "Docker instalado"
else
    print_status "Docker já instalado"
fi

echo "🐍 3. Instalando Python e Git..."
sudo apt install -y python3 python3-pip git

echo "👤 4. Criando usuário de deploy..."
if ! id "$DEPLOY_USER" &>/dev/null; then
    sudo adduser --disabled-password --gecos "" $DEPLOY_USER
    sudo usermod -aG docker $DEPLOY_USER
    print_status "Usuário $DEPLOY_USER criado"
else
    print_status "Usuário $DEPLOY_USER já existe"
fi

echo "📁 5. Configurando diretório de deploy..."
sudo -u $DEPLOY_USER mkdir -p $DEPLOY_PATH
sudo -u $DEPLOY_USER mkdir -p /home/$DEPLOY_USER/.ssh

echo "🔑 6. Configurando SSH..."
print_warning "Configure a chave SSH pública em /home/$DEPLOY_USER/.ssh/authorized_keys"
sudo touch /home/$DEPLOY_USER/.ssh/authorized_keys
sudo chown $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER/.ssh/authorized_keys
sudo chmod 600 /home/$DEPLOY_USER/.ssh/authorized_keys

echo "🌐 7. Clonando repositório..."
sudo -u $DEPLOY_USER git clone https://github.com/GustSR/oncabito-gaming-bot.git $DEPLOY_PATH

echo "📝 8. Configurando .env..."
sudo -u $DEPLOY_USER cp $DEPLOY_PATH/.env.example $DEPLOY_PATH/.env
print_warning "Configure o arquivo $DEPLOY_PATH/.env com suas credenciais"

echo "🔧 9. Configurando permissões..."
sudo chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH
sudo chmod +x $DEPLOY_PATH/deployment/*.sh
sudo chmod +x $DEPLOY_PATH/scripts/*.sh

echo "⏰ 10. Configurando cron..."
sudo -u $DEPLOY_USER crontab -l 2>/dev/null | { cat; echo "0 6 * * * $DEPLOY_PATH/deployment/run_checkup.sh"; } | sudo -u $DEPLOY_USER crontab -

print_status "Servidor configurado com sucesso!"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "1. Configure a chave SSH em /home/$DEPLOY_USER/.ssh/authorized_keys"
echo "2. Configure o arquivo $DEPLOY_PATH/.env"
echo "3. Configure os secrets no GitHub:"
echo "   - SSH_PRIVATE_KEY: Sua chave privada SSH"
echo "   - SSH_USER: $DEPLOY_USER"
echo "   - SSH_HOST: IP do seu servidor"
echo "   - DEPLOY_PATH: $DEPLOY_PATH"
echo ""
echo "4. Teste o deploy manual:"
echo "   sudo -u $DEPLOY_USER $DEPLOY_PATH/deployment/deploy.sh"
echo ""
print_warning "Lembre-se de configurar firewall e SSL se necessário!"