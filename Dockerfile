# OnCabito Gaming Bot - Dockerfile
# Bot oficial da comunidade gamer OnCabo
FROM python:3.10-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Labels para identificação
LABEL maintainer="OnCabo Gaming Community"
LABEL description="OnCabito - Bot oficial da comunidade gamer OnCabo"
LABEL version="2.0"

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código da aplicação para o diretório de trabalho
COPY . .

# Define o comando que será executado quando o contêiner iniciar
CMD ["python", "main.py"]
