#!/bin/bash
# =====================================
# OnCabito Bot - Setup Super Fácil
# =====================================

set -e

echo "🚀 OnCabito Bot - Setup Super Fácil!"
echo "===================================="

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

# Criar diretório do projeto
PROJECT_DIR="/opt/oncabito-bot"
echo "📁 Criando diretório do projeto..."
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# Baixar arquivos necessários
echo "⬇️  Baixando configurações..."
wget -q https://raw.githubusercontent.com/GustSR/oncabito-gaming-bot/main/docker-compose.yml
wget -q https://raw.githubusercontent.com/GustSR/oncabito-gaming-bot/main/.env.example

# Criar .env
if [ ! -f .env ]; then
    cp .env.example .env
    print_warning "Configure o arquivo .env com suas credenciais:"
    echo "   nano $PROJECT_DIR/.env"
fi

# Criar diretórios necessários
mkdir -p data/database logs backups

# Configurar permissões
chmod 755 data logs backups
print_success "Diretórios criados"

# Criar script de deploy simples
cat > deploy.sh << 'EOF'
#!/bin/bash
echo "🚀 Fazendo deploy do OnCabito Bot..."

# Login no GitHub Container Registry (público, não precisa de token)
docker pull ghcr.io/gustsr/oncabito-gaming-bot:latest

# Para container antigo
docker-compose down

# Sobe nova versão
docker-compose up -d

# Verifica status
sleep 5
docker-compose ps
docker-compose logs --tail 10

echo "✅ Deploy concluído!"
EOF

chmod +x deploy.sh

# Criar script de logs
cat > logs.sh << 'EOF'
#!/bin/bash
echo "📋 Logs do OnCabito Bot:"
docker-compose logs -f oncabito-bot
EOF

chmod +x logs.sh

# Criar script de backup
cat > backup.sh << 'EOF'
#!/bin/bash
echo "💾 Fazendo backup..."
docker-compose --profile backup run --rm backup
echo "✅ Backup concluído em ./backups/"
EOF

chmod +x backup.sh

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
echo "3️⃣  Acompanhe os logs:"
echo "   cd $PROJECT_DIR && ./logs.sh"
echo ""
echo "🔧 COMANDOS ÚTEIS:"
echo "   • Deploy:  ./deploy.sh"
echo "   • Logs:    ./logs.sh"
echo "   • Backup:  ./backup.sh"
echo "   • Status:  docker-compose ps"
echo "   • Parar:   docker-compose down"
echo ""
print_warning "Lembre-se de configurar o .env antes do primeiro deploy!"