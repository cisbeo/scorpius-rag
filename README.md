# 🏛️ Scorpius RAG

Système RAG (Retrieval-Augmented Generation) spécialisé pour l'analyse d'appels d'offres publics français.

## 🎯 Objectif

Scorpius RAG augmente le **win rate** des ESN sur les marchés publics en automatisant l'analyse des DCE et l'optimisation des réponses grâce à l'intelligence artificielle.

### Gains attendus
- **Win Rate** : +20-30% vs baseline actuelle
- **Temps d'analyse** : 3 jours → 4 heures (-40%)
- **Conformité réglementaire** : 95%+ de validation
- **ROI** : 500%+ première année

## 🏗️ Architecture

### Stack Technique
- **Backend** : Python 3.9+ avec async/await
- **Base vectorielle** : ChromaDB pour le RAG
- **IA** : OpenAI API (text-embedding-3-large, GPT-4)
- **Cache** : Système persistant pour optimiser les coûts
- **Logging** : Structlog pour observabilité

### Composants Principaux

```
src/
├── core/           # ScorpiusRAGEngine (moteur principal)
├── services/       # OpenAIEmbeddingService, ChromaDBService
├── models/         # SearchResult, AOContext, EmbeddingConfig
├── utils/          # Config, Cache, Logger
└── exceptions/     # Gestion robuste des erreurs
```

## ⚡ Installation & Configuration

### 🐳 Méthode Recommandée : Docker (Production Ready)

```bash
# Clone du projet
git clone https://github.com/cisbeo/scorpius-rag.git
cd scorpius-rag

# Configuration
cp .env.example .env
# Éditez .env et renseignez votre clé OpenAI

# Démarrage complet
docker compose up -d

# Vérification
docker compose ps
docker compose logs scorpius-rag
```

**Services déployés :**
- 🚀 **Scorpius RAG** : http://localhost:8000
- 🗄️ **ChromaDB** : http://localhost:8001  
- 🔴 **Redis** : localhost:6379

### 🔧 Méthode Alternative : Installation Python

```bash
# Prérequis : Python 3.11+, clé API OpenAI

# Clone et setup
git clone https://github.com/cisbeo/scorpius-rag.git
cd scorpius-rag

# Environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows

# Installation
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Éditez .env avec votre clé OpenAI

# Démarrage ChromaDB séparé
chroma run --path ./data/chromadb --port 8000
```

### 🔑 Configuration OpenAI (Obligatoire)

1. **Obtenez votre clé** : https://platform.openai.com/api-keys
2. **Éditez `.env`** :
```bash
OPENAI_API_KEY=sk-proj-votre-vraie-cle-ici
```
3. **Testez la config** :
```bash
# Avec Docker
docker compose exec scorpius-rag python -c "
from src.utils.config import Config
config = Config.from_env()
config.validate()
print('✅ Configuration validée!')
"
```

## 🚀 Usage

### Initialisation
```python
from src.core import ScorpiusRAGEngine
from src.models import AOContext, AOType, Sector, TechnicalDomain

# Initialisation automatique depuis .env
engine = await ScorpiusRAGEngine.create_from_env()
```

### Recherche contextuelle
```python
# Contexte AO pour optimiser la recherche
context = AOContext(
    ao_type=AOType.OUVERT,
    sector=Sector.TERRITORIAL,
    estimated_amount=500000,
    technical_domains=[TechnicalDomain.DEVELOPPEMENT]
)

# Recherche intelligente
results = await engine.search(
    query="développement plateforme e-services citoyens",
    context=context,
    collection="historique_ao",
    limit=5
)

# Analyse des résultats
for result in results:
    print(f"Score: {result.similarity_score:.2f}")
    print(f"AO: {result.ao_type} - {result.sector}")
    print(f"Contenu: {result.get_display_summary()}")
```

### Ajout de documents
```python
# Documents avec métadonnées enrichies
await engine.add_documents(
    collection="historique_ao",
    documents=["Cahier des charges plateforme numérique..."],
    metadatas=[{
        "organisme": "Région Nouvelle-Aquitaine",
        "montant": 750000,
        "secteur": "Territorial",
        "type_ao": "Ouvert",
        "fourchette_montant": "500k-1M",
        "date_publication": "2024-01-15"
    }]
)
```

### Métriques de performance
```python
# Statistiques détaillées
stats = engine.get_performance_stats()
print(f"Hit rate cache: {stats['computed_metrics']['cache_effectiveness']:.2%}")
print(f"Coût total: ${stats['rag_engine']['total_cost_usd']:.3f}")

# Diagnostic de santé
health = await engine.health_check()
print(f"Statut: {health['overall_status']}")
```

## 📊 Collections RAG

### Collections par défaut
- **`reglementaire`** : Code marchés publics, CCAG, jurisprudences
- **`historique_ao`** : Résultats BOAMP/TED, analyses post-attribution
- **`references_clients`** : Projets détaillés, ROI, retours satisfaction
- **`templates_performants`** : Mémoires gagnants, structures optimales
- **`intelligence_concurrentielle`** : Profils ESN, stratégies, grilles prix

### Métadonnées recommandées
```python
{
    "organisme": "Région Nouvelle-Aquitaine",
    "montant": 750000,
    "secteur": "Territorial",           # État, Territorial, Hospitalier, etc.
    "type_ao": "Ouvert",               # MAPA, Ouvert, Restreint, etc.
    "fourchette_montant": "500k-1M",   # Auto-calculée
    "domaine_technique": "Développement",
    "date_publication": "2024-01-15",
    "zone_geo": "Nouvelle-Aquitaine"
}
```

## 🧪 Tests

### Exécution des tests
```bash
# Tests unitaires
pytest tests/unit/ -v

# Tests avec coverage
pytest tests/unit/ --cov=src --cov-report=html

# Tests spécifiques
pytest tests/unit/test_scorpius_rag_engine.py -v
```

### Tests d'intégration
```bash
# Nécessite ChromaDB actif + clé OpenAI valide
pytest tests/integration/ -v
```

## 📈 Optimisation Coûts

### Cache intelligent
- **Hit rate** : 70-80% en usage normal
- **Économies** : -60% coûts embedding
- **TTL** : 24h par défaut (configurable)

### Estimation coûts
```python
# Estimation avant exécution
cost = await engine.embedding_service.estimate_cost(texts)
print(f"Coût estimé: ${cost:.4f}")

# Suivi en temps réel
stats = engine.get_performance_stats()
total_cost = stats['rag_engine']['total_cost_usd']
```

## 🔧 Configuration Avancée

### Variables d'environnement complètes
```bash
# Performance
EMBEDDING_BATCH_SIZE=100        # Taille batch embeddings
MAX_CONCURRENT_REQUESTS=5       # Concurrence max
OPENAI_RATE_LIMIT_RPM=3000     # Rate limit OpenAI

# Cache
CACHE_TTL_HOURS=24             # Durée vie cache
CACHE_MAX_SIZE_MB=500          # Taille max cache

# Logging
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
ENVIRONMENT=prod               # dev, test, prod
```

### Monitoring production
```python
# Configuration logging production
from src.utils import setup_logger

logger = setup_logger(
    log_level="INFO",
    environment="prod",
    correlation_id="req-123"
)

# Métriques business
business_logger = get_business_logger()
business_logger.info(
    "ao_analysis_completed",
    ao_type="Ouvert",
    sector="Territorial",
    recommendation="GO",
    confidence_score=0.85
)
```

## 🚨 Troubleshooting

### Erreurs courantes

**1. Clé API OpenAI invalide**
```bash
ConfigurationError: OPENAI_API_KEY: Format invalide
```
→ Vérifiez format : `sk-...` ou `sk-proj-...`

**2. ChromaDB inaccessible**
```bash
ChromaDBError: Impossible de se connecter à ChromaDB localhost:8000
```
→ Démarrez ChromaDB : `chroma run --path ./data/chromadb`

**3. Erreur de cache**
```bash
CacheError: Répertoire de cache non accessible
```
→ Vérifiez permissions : `mkdir -p cache/embeddings`

### Mode debug
```bash
# Variables debug
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# Ou via code
engine = await ScorpiusRAGEngine.create_from_env()
health = await engine.health_check()
print(health)  # Diagnostic complet
```

## 📋 Roadmap

### Version 1.1 (Q2 2024)
- [ ] Multi-provider embeddings (Hugging Face, Cohere)
- [ ] Interface Streamlit pour démonstration
- [ ] Export résultats PDF/Word
- [ ] Intégration BOAMP scraping

### Version 1.2 (Q3 2024)
- [ ] Templates mémoires techniques par secteur
- [ ] Scoring prédictif win probability
- [ ] API REST pour intégrations
- [ ] Dashboard métriques avancées

## 🤝 Contribution

1. **Fork** le repository
2. **Branch** feature : `git checkout -b feature/amazing-feature`
3. **Commit** : `git commit -m 'Add amazing feature'`
4. **Push** : `git push origin feature/amazing-feature`
5. **Pull Request**

### Standards de code
- **Formatage** : Black avec `--line-length=88`
- **Type hints** : Obligatoires partout
- **Tests** : Coverage >80% obligatoire
- **Docstrings** : Format Google

## 📄 Licence

Ce projet est sous licence privée. Tous droits réservés.

---

## 🏛️ Contexte Métier

**Scorpius RAG** est spécialement conçu pour le domaine des **appels d'offres publics français**, avec une expertise approfondie de :

- **Réglementation** : Code des marchés publics, CCAG, seuils européens
- **Procédures** : MAPA, Ouverts, Restreints, Dialogue compétitif
- **Secteurs** : État, Territorial, Hospitalier, Éducation, EPA/EPIC
- **Intelligence** : BOAMP, TED, patterns concurrentiels, grilles tarifaires

Le système comprend les nuances métier et optimise automatiquement les recherches selon le contexte AO spécifique.