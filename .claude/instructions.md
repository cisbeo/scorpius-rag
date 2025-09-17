# INSTRUCTIONS CLAUDE POUR SCORPIUS RAG

## 🎯 DIRECTIVES GÉNÉRALES

Vous êtes l'assistant IA principal du projet **Scorpius RAG**, système spécialisé dans l'analyse d'appels d'offres publics français. Votre rôle est d'accélérer le développement en générant du code production-ready, des tests, et de la documentation de haute qualité.

## 📝 STANDARDS DE CODE

### Style & Formatage

- **Langage** : Python 3.9+ exclusivement
- **Style guide** : Google Python Style Guide
- **Formatage** : Black avec `--line-length=88`  
- **Import sorting** : isort avec profil Black
- **Type hints** : Obligatoires pour tous arguments/retours
- **Docstrings** : Format Google, obligatoires classes/fonctions publiques

### Architecture & Patterns

- **Modularité** : Single Responsibility Principle strict
- **Dependency Injection** : Pour toutes dépendances externes (APIs, DB)
- **Error Handling** : Comprehensive avec logging structuré
- **Async/Await** : Pour toutes opérations I/O (API calls, DB queries)
- **Configuration** : Variables environnement + fichiers YAML
- **Testing** : Test-driven development, coverage >80%

### Exemple Code Style

```python
from typing import Dict, List, Optional, Union
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class SearchResult:
    """Résultat de recherche RAG avec métadonnées.
    
    Attributes:
        content: Contenu du document trouvé
        metadata: Métadonnées associées (source, date, etc.)
        similarity_score: Score de similarité [0.0, 1.0]
        collection: Collection source du résultat
    """
    content: str
    metadata: Dict[str, Union[str, int, float]]
    similarity_score: float
    collection: str

class BaseRAGService(ABC):
    """Interface abstraite pour services RAG."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialise le service avec configuration.
        
        Args:
            config: Configuration du service
            
        Raises:
            ValueError: Si configuration invalide
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_config()
    
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Recherche documents pertinents.
        
        Args:
            query: Requête de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des résultats de recherche ordonnés par pertinence
            
        Raises:
            APIError: En cas d'erreur API
            ValidationError: Si query invalide
        """
        pass
    
    def _validate_config(self) -> None:
        """Valide la configuration du service."""
        required_keys = ["api_key", "base_url"]
        missing = [key for key in required_keys if key not in self.config]
        if missing:
            raise ValueError(f"Configuration manquante: {missing}")
```

## 🏗️ ARCHITECTURE COMPONANTS

### Structure Attendue

```
src/
├── core/           # Business logic principal
├── services/       # Services externes (APIs, DB)  
├── models/         # Modèles de données (dataclasses)
├── utils/          # Utilitaires transverses
├── api/           # Endpoints API REST (future)
└── exceptions/     # Exceptions métier personnalisées
```

### Patterns Obligatoires

#### 1. Factory Pattern pour Services

```python
class ServiceFactory:
    """Factory pour création services avec configuration."""
    
    @staticmethod
    def create_embedding_service(provider: str) -> EmbeddingService:
        if provider == "openrouter":
            return OpenRouterEmbeddingService(config)
        elif provider == "openai":
            return OpenAIEmbeddingService(config)
        else:
            raise ValueError(f"Provider non supporté: {provider}")
```

#### 2. Strategy Pattern pour Secteurs

```python
class SectorAnalysisStrategy(ABC):
    """Stratégie d'analyse par secteur public."""
    
    @abstractmethod
    def analyze_compliance(self, dcr_text: str) -> ComplianceResult:
        pass

class HospitalSectorStrategy(SectorAnalysisStrategy):
    """Stratégie secteur hospitalier (HDS, interop DMP, etc.)."""
    
    def analyze_compliance(self, dcr_text: str) -> ComplianceResult:
        # Logique spécifique secteur hospitalier
        pass
```

#### 3. Observer Pattern pour Métriques

```python
class MetricsObserver:
    """Observateur pour collecte métriques."""
    
    def on_search_performed(self, query: str, results_count: int, duration: float):
        # Log métrique recherche
        pass
    
    def on_analysis_completed(self, ao_type: str, score: float, duration: float):
        # Log métrique analyse
        pass
```

## 🧪 STANDARDS TESTING

### Structure Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.rag_engine import ScorpiusRAGEngine

class TestScorpiusRAGEngine:
    """Tests unitaires pour ScorpiusRAGEngine."""
    
    @pytest.fixture
    def mock_config(self):
        return {
            "openrouter_api_key": "test-key",
            "embedding_model": "voyage-large-2-instruct"
        }
    
    @pytest.fixture  
    def rag_engine(self, mock_config):
        return ScorpiusRAGEngine(mock_config)
    
    @pytest.mark.asyncio
    async def test_search_returns_relevant_results(self, rag_engine):
        """Test que la recherche retourne des résultats pertinents."""
        # Given
        query = "AO région plateforme e-services"
        
        # When
        results = await rag_engine.search(query, limit=3)
        
        # Then  
        assert len(results) <= 3
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.similarity_score >= 0.0 for r in results)
    
    @pytest.mark.asyncio
    async def test_search_handles_api_error_gracefully(self, rag_engine, monkeypatch):
        """Test gestion gracieuse erreurs API."""
        # Given
        async def mock_api_error(*args, **kwargs):
            raise APIError("Service temporarily unavailable")
        
        monkeypatch.setattr(rag_engine.embedding_service, "embed", mock_api_error)
        
        # When/Then
        with pytest.raises(APIError) as exc_info:
            await rag_engine.search("test query")
        
        assert "temporarily unavailable" in str(exc_info.value)
```

### Coverage & Performance

- **Coverage minimum** : 80% sur `src/`
- **Tests d'intégration** : API calls avec mocks
- **Tests de performance** : Benchmarks temps réponse
- **Tests end-to-end** : Workflows complets utilisateur

## 📊 LOGGING & MONITORING

### Configuration Logging

```python
import logging
import structlog
from datetime import datetime

# Configuration logging structuré
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage dans classes
class ScorpiusRAGEngine:
    def __init__(self):
        self.logger = structlog.get_logger(self.__class__.__name__)
    
    async def search(self, query: str) -> List[SearchResult]:
        self.logger.info(
            "search_started",
            query=query[:100],  # Truncate pour privacy
            timestamp=datetime.utcnow().isoformat()
        )
        
        try:
            results = await self._perform_search(query)
            self.logger.info(
                "search_completed",
                query_hash=hash(query),  # Hash pour privacy
                results_count=len(results),
                duration=duration
            )
            return results
        except Exception as e:
            self.logger.error(
                "search_failed", 
                query_hash=hash(query),
                error=str(e),
                error_type=type(e).__name__
            )
            raise
```

### Métriques Business

```python
from dataclasses import dataclass
from enum import Enum

class AnalysisType(Enum):
    QUALIFICATION = "qualification"
    DCR_ANALYSIS = "dcr_analysis"  
    COMPETITIVE_INTEL = "competitive_intel"
    TEMPLATE_GENERATION = "template_generation"

@dataclass
class AnalysisMetrics:
    """Métriques d'une analyse AO."""
    analysis_id: str
    analysis_type: AnalysisType
    duration_seconds: float
    tokens_used: int
    cost_usd: float
    user_satisfaction: Optional[int]  # 1-5 si fourni
    business_outcome: Optional[str]  # "won", "lost", "pending"
```

## 🔒 SÉCURITÉ & CONFIDENTIALITÉ

### Gestion Secrets

```python
import os
from typing import Optional

class SecureConfig:
    """Configuration sécurisée avec gestion secrets."""
    
    @staticmethod
    def get_api_key(service: str) -> Optional[str]:
        """Récupère clé API depuis variables environnement."""
        key = os.getenv(f"{service.upper()}_API_KEY")
        if not key:
            logger.warning(f"API key manquante pour {service}")
        return key
    
    @staticmethod  
    def validate_api_key(key: str, service: str) -> bool:
        """Valide format clé API."""
        patterns = {
            "openrouter": r"^sk-or-v1-[a-zA-Z0-9]{64}$",
            "openai": r"^sk-[a-zA-Z0-9]{48}$"
        }
        
        pattern = patterns.get(service)
        if not pattern:
            return False
            
        return re.match(pattern, key) is not None
```

### Anonymisation Données

```python
import hashlib
from typing import Any, Dict

def anonymize_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Anonymise données utilisateur pour logs/métriques."""
    sensitive_fields = ["email", "company", "project_name", "client_name"]
    
    anonymized = data.copy()
    for field in sensitive_fields:
        if field in anonymized:
            # Hash avec salt pour anonymisation
            salt = os.getenv("ANONYMIZATION_SALT", "default_salt")
            raw_value = f"{anonymized[field]}{salt}"
            anonymized[field] = hashlib.sha256(raw_value.encode()).hexdigest()[:16]
    
    return anonymized
```

## 🚀 OPTIMISATION PERFORMANCE

### Async/Await Patterns

```python
import asyncio
from typing import List, Coroutine

class AsyncBatchProcessor:
    """Traitement batch asynchrone pour optimisation performance."""
    
    async def process_batch(self, items: List[str], batch_size: int = 10) -> List[Any]:
        """Traite items par batch pour éviter rate limiting."""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Traitement concurrent du batch
            tasks = [self._process_single_item(item) for item in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Gestion erreurs
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error("batch_item_failed", error=str(result))
                else:
                    results.append(result)
            
            # Rate limiting respectueux
            await asyncio.sleep(0.1)
        
        return results
```

### Caching Strategy

```python
from functools import lru_cache
import pickle
import os
from typing import Optional

class EmbeddingCache:
    """Cache persistant pour embeddings."""
    
    def __init__(self, cache_dir: str = "./cache/embeddings"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """Génère clé cache unique."""
        content = f"{text}{model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Récupère embedding depuis cache."""
        key = self._get_cache_key(text, model)
        cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning("cache_read_failed", key=key, error=str(e))
        
        return None
    
    def set(self, text: str, model: str, embedding: List[float]) -> None:
        """Sauvegarde embedding en cache."""
        key = self._get_cache_key(text, model)
        cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
        
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(embedding, f)
        except Exception as e:
            self.logger.error("cache_write_failed", key=key, error=str(e))
```

## 📚 GÉNÉRATION DOCUMENTATION

### Docstrings Auto-Description

- **Classes** : Description rôle + exemple usage
- **Méthodes publiques** : Args, Returns, Raises détaillés
- **Modules** : Vue d'ensemble + architecture
- **Exemples code** : Cas d'usage réalistes dans docstrings

### README.md Structure

1. **Description projet** + objectifs business
2. **Installation** : requirements + setup complet  
3. **Usage rapide** : exemples concrets d'utilisation
4. **Architecture** : diagrammes + composants principaux
5. **Configuration** : variables environnement + options
6. **Développement** : setup dev + contribution guidelines
7. **Déploiement** : Docker + production setup
8. **FAQ** : problèmes courants + solutions

## ⚡ OPTIMISATIONS CLAUDE CODE

### Prompts Efficaces

- **Contexte complet** : Toujours inclure contexte métier AO publiques
- **Spécifications précises** : Type retour, gestion erreurs, performance attendue
- **Exemples concrets** : Cas d'usage réels du domaine
- **Standards qualité** : Mentionner coverage, logging, documentation

### Workflow Recommandé

1. **Architecture** : Définir interfaces avant implémentation
2. **TDD** : Tests avant code pour chaque composant
3. **Intégration** : Tests d'intégration après tests unitaires
4. **Documentation** : Génération auto après code validé
5. **Optimisation** : Profiling + benchmarks après fonctionnalités core

---

## 🎯 RÉSUMÉ DIRECTIVES

**TOUJOURS** :
✅ Code production-ready avec type hints + docstrings  
✅ Gestion erreurs comprehensive + logging structuré
✅ Tests unitaires + intégration avec >80% coverage
✅ Async/await pour opérations I/O  
✅ Configuration externalisée + validation
✅ Documentation auto-générée + exemples

**JAMAIS** :
❌ Hardcoded secrets ou configuration
❌ Code synchrone pour API calls  
❌ Exceptions non gérées
❌ Logs avec données sensibles
❌ Code sans tests ou documentation
❌ Architecture monolithique

**Focus spécial domaine AO publiques français** : Toujours contextualiser selon réglementations, secteurs, et processus métier spécifiques aux marchés publics.
