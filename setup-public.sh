#!/bin/bash
# =====================================
# OnCabito Bot - Setup Super Fácil (Repositório Público)
# =====================================

set -e

echo "🚀 OnCabito Bot - Setup Super Fácil (Repositório Público)"
echo "======================================================="

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "🐳 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    print_success "Docker instalado! Faça logout/login para aplicar permissões"
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "🔧 Instalando Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose instalado"
fi

# Verificar se Git está instalado
if ! command -v git &> /dev/null; then
    echo "📱 Instalando Git..."
    sudo apt update && sudo apt install -y git
    print_success "Git instalado"
fi

# Criar diretório do projeto
PROJECT_DIR="/opt/oncabito-bot"
echo "📁 Configurando diretório do projeto..."
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# Clonar repositório público
echo "📦 Clonando repositório OnCabito Bot..."
if [ -d ".git" ]; then
    echo "Repositório já existe, atualizando..."
    git pull origin main
else
    git clone https://github.com/GustSR/oncabito-gaming-bot.git .
fi

# Criar .env se não existir
if [ ! -f .env ]; then
    cp .env.example .env
    print_warning "Configure o arquivo .env com suas credenciais:"
    echo "   nano $PROJECT_DIR/.env"
    echo ""
    echo "🔑 Credenciais necessárias:"
    echo "   - TELEGRAM_TOKEN (do BotFather)"
    echo "   - TELEGRAM_GROUP_ID (ID do seu grupo)"
    echo "   - HUBSOFT_* (credenciais da API)"
    echo ""
fi

# Criar diretórios necessários
mkdir -p data/database logs backups

# Configurar permissões
chmod 755 data logs backups
print_success "Diretórios criados"

# Criar scripts auxiliares
cat > start.sh << 'EOF'
#!/bin/bash
echo "🚀 Iniciando OnCabito Bot..."
docker-compose up -d
sleep 5
docker-compose ps
echo "✅ Bot iniciado! Use 'docker-compose logs -f' para ver logs"
EOF

cat > stop.sh << 'EOF'
#!/bin/bash
echo "⏹️ Parando OnCabito Bot..."
docker-compose down
echo "✅ Bot parado"
EOF

cat > logs.sh << 'EOF'
#!/bin/bash
echo "📋 Logs do OnCabito Bot:"
docker-compose logs -f oncabito-bot
EOF

cat > status.sh << 'EOF'
#!/bin/bash
echo "📊 Status do OnCabito Bot:"
docker-compose ps
echo ""
echo "💻 Uso de recursos:"
docker stats oncabito-bot --no-stream
EOF

chmod +x start.sh stop.sh logs.sh status.sh deploy.sh

print_success "Setup concluído!"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo ""
echo "1️⃣  Configure suas credenciais:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2️⃣  Faça o primeiro deploy:"
echo "   cd $PROJECT_DIR && ./deploy.sh"
echo ""
echo "3️⃣  Comandos úteis:"
echo "   • Iniciar:    ./start.sh"
echo "   • Parar:      ./stop.sh  "
echo "   • Logs:       ./logs.sh"
echo "   • Status:     ./status.sh"
echo "   • Deploy:     ./deploy.sh"
echo ""
print_warning "⚠️  Configure o .env antes de fazer o deploy!"
echo ""
echo "🔗 Repositório: https://github.com/GustSR/oncabito-gaming-bot"
echo "📚 Documentação: $PROJECT_DIR/docs/"