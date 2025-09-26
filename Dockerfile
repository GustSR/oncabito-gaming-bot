# =====================================
# OnCabito Gaming Bot - Production Dockerfile
# =====================================
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r oncabito && useradd -r -g oncabito oncabito

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=oncabito:oncabito src/ ./src/
COPY --chown=oncabito:oncabito main.py ./
COPY --chown=oncabito:oncabito .env.example ./
COPY --chown=oncabito:oncabito migrations/ ./migrations/

# Create required directories
RUN mkdir -p data/database logs \
    && chown -R oncabito:oncabito /app

# Switch to non-root user
USER oncabito

# Expose health check port (if needed)
EXPOSE 8080

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import sys; sys.path.append('/app/src'); \
    from sentinela.core.config import TELEGRAM_TOKEN; \
    exit(0 if TELEGRAM_TOKEN else 1)" || exit 1

# Labels (OCI standard)
LABEL org.opencontainers.image.title="OnCabito Gaming Bot"
LABEL org.opencontainers.image.description="Intelligent Telegram bot for OnCabo Gaming Community"
LABEL org.opencontainers.image.version="2.0"
LABEL org.opencontainers.image.vendor="OnCabo Gaming Community"
LABEL org.opencontainers.image.authors="gaming@oncabo.com.br"
LABEL org.opencontainers.image.url="https://github.com/GustSR/oncabito-gaming-bot"
LABEL org.opencontainers.image.source="https://github.com/GustSR/oncabito-gaming-bot"
LABEL org.opencontainers.image.licenses="MIT"

# Environment variables
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Run application
CMD ["python3", "main.py"]