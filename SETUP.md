# 🔧 Guide de Configuration - Scorpius RAG

## 🎯 Vue d'Ensemble

Ce guide détaille tous les aspects de configuration pour déployer et maintenir Scorpius RAG en local ou en production.

## 🐳 Configuration Docker (Recommandée)

### Prérequis
- Docker 20.10+ et Docker Compose 2.0+
- 4GB RAM minimum, 8GB recommandé
- Clé API OpenAI active

### Démarrage Rapide

```bash
# 1. Clone du projet
git clone https://github.com/cisbeo/scorpius-rag.git
cd scorpius-rag

# 2. Configuration environnement
cp .env.example .env
# Éditez .env et renseignez votre OPENAI_API_KEY

# 3. Démarrage services
docker compose up -d

# 4. Vérification
docker compose ps
docker compose logs scorpius-rag
```

### Services Déployés

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| Scorpius RAG | 8000 | http://localhost:8000 | Application principale |
| ChromaDB | 8001 | http://localhost:8001 | Base vectorielle |
| Redis | 6379 | localhost:6379 | Cache et sessions |

### Scripts d'Automatisation

```bash
# Build personnalisé
./scripts/docker-build.sh -t production -g v1.0.0

# Gestion simplifiée
./scripts/docker-run.sh status     # État des services
./scripts/docker-run.sh logs       # Logs en temps réel
./scripts/docker-run.sh restart    # Redémarrage propre
./scripts/docker-run.sh clean      # Nettoyage complet
```

## 🔑 Configuration OpenAI

### Obtention Clé API

1. **Créer un compte** : https://platform.openai.com/
2. **Générer une clé** : https://platform.openai.com/api-keys
3. **Configurer facturation** : Ajouter méthode de paiement
4. **Vérifier limites** : 3000 RPM recommandé minimum

### Configuration dans Scorpius RAG

**Fichier `.env` :**
```bash
# OpenAI Configuration (OBLIGATOIRE)
OPENAI_API_KEY=sk-proj-votre-vraie-cle-ici
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TIMEOUT=30
OPENAI_MAX_RETRIES=3
OPENAI_RATE_LIMIT_RPM=3000
```

### Test de Configuration

```bash
# Test avec Docker
docker compose exec scorpius-rag python -c "
from src.utils.config import Config
config = Config.from_env()
config.validate()
print('✅ Configuration OpenAI validée!')
print(f'Modèle: {config.openai_model}')
print(f'Rate limit: {config.openai_rate_limit_rpm} RPM')
"
```

### Optimisation Coûts

```bash
# Cache activé par défaut (économise 60-70%)
CACHE_ENABLED=true
CACHE_TTL_HOURS=24
CACHE_MAX_SIZE_MB=500

# Ajustement batch processing
EMBEDDING_BATCH_SIZE=100        # Plus élevé = plus efficace
MAX_CONCURRENT_REQUESTS=5       # Selon vos limites API
```

## 🗄️ Configuration ChromaDB

### Configuration de Base

```bash
# Variables ChromaDB dans .env
CHROMA_HOST=chromadb            # Nom service Docker
CHROMA_PORT=8000               # Port standard
CHROMA_PERSISTENT_PATH=/app/data/chromadb
```

### Collections Recommandées

```python
# Collections métier spécialisées
COLLECTIONS = {
    "reglementaire": {
        "description": "Code marchés publics, CCAG, jurisprudences",
        "metadatas": ["type_regle", "secteur", "date_maj"]
    },
    "historique_ao": {
        "description": "AO analysés avec résultats",
        "metadatas": ["organisme", "montant", "secteur", "type_ao", "resultat"]
    },
    "references_clients": {
        "description": "Projets réalisés avec détails",
        "metadatas": ["client", "secteur", "montant", "duree", "satisfaction"]
    },
    "templates_performants": {
        "description": "Mémoires techniques gagnants",
        "metadatas": ["secteur", "type_ao", "montant_min", "montant_max"]
    },
    "intelligence_concurrentielle": {
        "description": "Profils concurrents et stratégies",
        "metadatas": ["concurrent", "secteur", "specialite", "taux_gain"]
    }
}
```

### Métadonnées Standards

```python
# Schema métadonnées pour AO
METADATA_SCHEMA = {
    "organisme": "Région Nouvelle-Aquitaine",
    "montant": 750000,                    # En euros
    "secteur": "Territorial",             # État, Territorial, Hospitalier
    "type_ao": "Ouvert",                  # MAPA, Ouvert, Restreint
    "fourchette_montant": "500k-1M",      # Auto-calculée
    "domaine_technique": "Développement", 
    "date_publication": "2024-01-15",
    "zone_geo": "Nouvelle-Aquitaine",
    "duree_contrat": 24,                  # En mois
    "criteres_selection": ["technique", "prix", "delai"],
    "tags": ["eservices", "plateforme", "citoyens"]
}
```

## ⚙️ Configuration Avancée

### Variables d'Environnement Complètes

```bash
# ===== OpenAI Configuration =====
OPENAI_API_KEY=sk-proj-votre-cle
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TIMEOUT=30
OPENAI_MAX_RETRIES=3
OPENAI_RATE_LIMIT_RPM=3000

# ===== ChromaDB Configuration =====
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_PERSISTENT_PATH=/app/data/chromadb

# ===== Cache Configuration =====
CACHE_ENABLED=true
CACHE_DIR=/app/cache/embeddings
CACHE_TTL_HOURS=24
CACHE_MAX_SIZE_MB=500

# ===== Application Configuration =====
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
ENVIRONMENT=prod                  # dev, test, staging, prod
DEBUG_MODE=false

# ===== Performance Configuration =====
EMBEDDING_BATCH_SIZE=100
MAX_CONCURRENT_REQUESTS=5
```

### Configuration Multi-Environnements

**Développement (`.env.dev`) :**
```bash
LOG_LEVEL=DEBUG
DEBUG_MODE=true
ENVIRONMENT=dev
CACHE_TTL_HOURS=1                # TTL réduit pour tests
EMBEDDING_BATCH_SIZE=10          # Batch réduit pour debug
OPENAI_RATE_LIMIT_RPM=500        # Limite réduite
```

**Production (`.env.prod`) :**
```bash
LOG_LEVEL=INFO
DEBUG_MODE=false
ENVIRONMENT=prod
CACHE_TTL_HOURS=24
EMBEDDING_BATCH_SIZE=100
OPENAI_RATE_LIMIT_RPM=3000
```

### Configuration Logging

```python
# Configuration avancée dans config.py
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": "structlog.dev.ConsoleRenderer",
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "/app/logs/scorpius.log",
            "formatter": "structured",
        },
    },
    "loggers": {
        "scorpius": {
            "handlers": ["default", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
```

## 🔧 Installation Python Native (Alternative)

### Prérequis Système

```bash
# Python 3.11+ requis
python --version  # >= 3.11

# Dépendances système (Ubuntu/Debian)
sudo apt update
sudo apt install python3-pip python3-venv build-essential curl

# Dépendances système (macOS)
brew install python@3.11
```

### Installation Projet

```bash
# Clone et setup
git clone https://github.com/cisbeo/scorpius-rag.git
cd scorpius-rag

# Environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows

# Installation dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Éditez .env avec votre clé OpenAI
```

### Démarrage Services Externes

```bash
# ChromaDB en local
pip install chromadb
chroma run --path ./data/chromadb --port 8000

# Redis (optionnel, via Docker)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Test application
python -m src.main
```

## 🚨 Troubleshooting

### Problèmes Courants

#### 1. Erreur Clé API OpenAI

**Symptôme :**
```
ConfigurationError: OPENAI_API_KEY: Format invalide
```

**Solutions :**
```bash
# Vérifier format
echo $OPENAI_API_KEY | grep -E "^sk-(proj-)?[a-zA-Z0-9-_]+"

# Tester directement
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

#### 2. ChromaDB Inaccessible

**Symptôme :**
```
ChromaDBError: Connection failed to localhost:8000
```

**Solutions :**
```bash
# Vérifier service
docker compose ps chromadb

# Redémarrer ChromaDB
docker compose restart chromadb

# Logs diagnostics
docker compose logs chromadb
```

#### 3. Cache Non Accessible

**Symptôme :**
```
CacheError: Cannot write to cache directory
```

**Solutions :**
```bash
# Vérifier permissions
ls -la cache/
sudo chown -R $USER:$USER cache/

# Créer répertoires
mkdir -p cache/embeddings logs data/chromadb
```

#### 4. Rate Limit OpenAI

**Symptôme :**
```
OpenAIError: Rate limit exceeded
```

**Solutions :**
```bash
# Réduire rate limit dans .env
OPENAI_RATE_LIMIT_RPM=500

# Vérifier usage sur platform.openai.com
# Upgrader plan si nécessaire
```

### Tests de Validation

```bash
# Test configuration complète
docker compose exec scorpius-rag python -c "
from src.utils.config import Config
from src.core.scorpius_rag_engine import ScorpiusRAGEngine
import asyncio

async def test():
    config = Config.from_env()
    config.validate()
    print('✅ Config validée')
    
    engine = await ScorpiusRAGEngine.create_from_env()
    health = await engine.health_check()
    print(f'✅ Santé: {health[\"overall_status\"]}')

asyncio.run(test())
"
```

### Monitoring Santé

```bash
# Commandes de monitoring
docker compose ps                           # État services
docker compose logs --tail=50 scorpius-rag  # Logs récents
docker stats                                # Utilisation ressources

# Health check API
curl http://localhost:8000/health

# Métriques ChromaDB
curl http://localhost:8001/api/v2/version
```

## 📊 Métriques et Performance

### KPIs à Surveiller

```python
# Métriques business
{
    "requetes_par_jour": 1500,
    "hit_rate_cache": 0.72,
    "latence_moyenne_ms": 285,
    "cout_daily_usd": 2.45
}

# Métriques techniques
{
    "embeddings_generated": 15420,
    "collections_count": 5,
    "documents_total": 2876,
    "storage_usage_gb": 1.2
}
```

### Alertes Recommandées

```bash
# Seuils d'alerte
LATENCY_THRESHOLD_MS=500
CACHE_HIT_RATE_MIN=0.5
DAILY_COST_THRESHOLD_USD=10
ERROR_RATE_THRESHOLD=0.05
```

---

*Guide maintenu par l'équipe Scorpius RAG*  
*Dernière mise à jour : 17 septembre 2024*