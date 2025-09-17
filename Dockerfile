# Dockerfile multi-stage pour Scorpius RAG
# Optimisé pour production avec cache Docker et sécurité

# ===== Stage Base =====
FROM python:3.11-slim as base

# Métadonnées
LABEL maintainer="Scorpius RAG Team"
LABEL description="Système RAG pour analyse d'appels d'offres publics français"
LABEL version="1.0.0"

# Variables d'environnement de base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Création utilisateur non-root pour sécurité
RUN groupadd --gid 1000 scorpius && \
    useradd --uid 1000 --gid scorpius --shell /bin/bash --create-home scorpius

# Installation dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ===== Stage Dependencies =====
FROM base as dependencies

# Répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .
COPY requirements-dev.txt* ./

# Installation des dépendances Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ===== Stage Development =====
FROM dependencies as development

# Installation dépendances développement si disponibles
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

# Installation outils développement
RUN pip install \
    ipython \
    jupyter \
    pytest-cov \
    pytest-xdist

# Copie du code source
COPY --chown=scorpius:scorpius . .

# Configuration développement
ENV ENVIRONMENT=dev \
    DEBUG_MODE=true \
    LOG_LEVEL=DEBUG

# Ports pour développement
EXPOSE 8000 8888

# Utilisateur non-root
USER scorpius

# Commande par défaut développement
CMD ["python", "-m", "src.main"]

# ===== Stage Production Build =====
FROM dependencies as production-build

# Copie du code source
COPY --chown=scorpius:scorpius src/ ./src/
COPY --chown=scorpius:scorpius setup.py* ./
COPY --chown=scorpius:scorpius pyproject.toml* ./
COPY --chown=scorpius:scorpius README.md* ./

# Installation du package si setup.py existe
RUN if [ -f setup.py ]; then pip install -e .; fi

# Nettoyage des fichiers temporaires
RUN find . -type d -name __pycache__ -delete && \
    find . -type f -name "*.pyc" -delete

# ===== Stage Production =====
FROM python:3.11-slim as production

# Variables d'environnement production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=prod \
    DEBUG_MODE=false \
    LOG_LEVEL=INFO

# Création utilisateur non-root
RUN groupadd --gid 1000 scorpius && \
    useradd --uid 1000 --gid scorpius --shell /bin/bash --create-home scorpius

# Installation dépendances système minimales
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Répertoire de travail
WORKDIR /app

# Copie des dépendances installées depuis le stage dependencies
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copie du code source depuis production-build
COPY --from=production-build --chown=scorpius:scorpius /app .

# Copie du script entrypoint et permissions
COPY --chown=scorpius:scorpius docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh

# Création des répertoires nécessaires
RUN mkdir -p /app/data/chromadb /app/cache/embeddings /app/logs && \
    chown -R scorpius:scorpius /app

# Configuration sécurité
USER scorpius

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Port par défaut
EXPOSE 8000

# Point d'entrée avec gestion des signaux
ENTRYPOINT ["/app/docker/entrypoint.sh"]

# Commande par défaut
CMD ["python", "-m", "src.main"]