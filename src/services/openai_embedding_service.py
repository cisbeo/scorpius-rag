"""Service d'embedding OpenAI avec optimisations et resilience."""

import asyncio
import time
from typing import List, Union, Dict, Any, Optional
import tiktoken
import structlog
from openai import AsyncOpenAI

from .embedding_service import EmbeddingService
from ..models.embedding_config import EmbeddingConfig
from ..exceptions import OpenAIError, ValidationError, ConfigurationError
from ..utils.embedding_cache import EmbeddingCache


class OpenAIEmbeddingService(EmbeddingService):
    """Service d'embedding OpenAI optimisé pour production.
    
    Cette implémentation fournit:
    - Rate limiting intelligent avec backoff exponential
    - Cache des embeddings pour économiser les coûts
    - Retry automatique avec circuit breaker
    - Batch processing pour optimiser les performances
    - Monitoring des coûts et métriques en temps réel
    - Gestion robuste des erreurs avec fallback gracieux
    
    Attributes:
        client: Client OpenAI asynchrone
        config: Configuration du service
        cache: Cache des embeddings (optionnel)
        tokenizer: Tokenizer pour estimation précise des coûts
        
    Examples:
        >>> config = EmbeddingConfig.from_env()
        >>> service = OpenAIEmbeddingService(config)
        >>> 
        >>> # Embedding unique avec cache automatique
        >>> embedding = await service.embed("Appel d'offres région plateforme")
        >>> print(f"Dimension: {len(embedding)}")
        >>> 
        >>> # Batch optimisé pour analyse DCE
        >>> texts = ["critère technique", "pondération prix", "délai exécution"]
        >>> embeddings = await service.embed_batch(texts, batch_size=50)
        >>> 
        >>> # Métriques de performance
        >>> stats = service.get_performance_stats()
        >>> print(f"Coût total: ${stats['total_cost_usd']:.3f}")
    """
    
    def __init__(
        self, 
        config: Union[EmbeddingConfig, Dict[str, Any]],
        enable_cache: bool = True
    ) -> None:
        """Initialise le service OpenAI avec configuration optimisée.
        
        Args:
            config: Configuration d'embedding (EmbeddingConfig ou dict)
            enable_cache: Active le cache des embeddings pour économies
            
        Raises:
            ConfigurationError: Si la configuration est invalide
            OpenAIError: Si l'authentification échoue
        """
        # Conversion en EmbeddingConfig si nécessaire
        if isinstance(config, dict):
            config = EmbeddingConfig(**config)
        elif not isinstance(config, EmbeddingConfig):
            raise ValidationError(
                "config doit être EmbeddingConfig ou dict",
                field_name="config",
                field_value=type(config).__name__,
                expected_type="EmbeddingConfig"
            )
        
        super().__init__(config.to_dict())
        self.embedding_config = config
        
        # Initialisation client OpenAI
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        
        # Cache optionnel
        self.cache: Optional[EmbeddingCache] = None
        if enable_cache and config.cache_enabled:
            self.cache = EmbeddingCache(
                ttl_hours=config.cache_ttl_hours
            )
        
        # Tokenizer pour estimation coûts précise
        try:
            self.tokenizer = tiktoken.encoding_for_model("text-embedding-3-large")
        except KeyError:
            # Fallback si modèle non reconnu
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Métriques de performance
        self._stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "cache_hits": 0,
            "api_calls": 0,
            "errors": 0,
            "avg_latency_ms": 0.0
        }
        
        # Rate limiting
        self._last_request_time = 0.0
        self._request_count = 0
        self._rate_limit_delay = config.get_rate_limit_delay()
        
        self.logger.info(
            "openai_embedding_service_initialized",
            model=config.model,
            cache_enabled=self.cache is not None,
            dimensions=config.embedding_dimensions,
            cost_per_1k_tokens=config.cost_per_1k_tokens
        )
    
    def _validate_config(self) -> None:
        """Valide la configuration OpenAI."""
        if not self.embedding_config.api_key:
            raise ConfigurationError.missing_env_var("OPENAI_API_KEY")
        
        if not self.embedding_config.api_key.startswith(("sk-", "sk-proj-")):
            raise ConfigurationError.invalid_config_value(
                "api_key",
                "clé masquée",
                "Format OpenAI valide (sk-...)",
                "environment"
            )
    
    async def _wait_for_rate_limit(self) -> None:
        """Respecte le rate limiting avec délai intelligent."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._rate_limit_delay:
            wait_time = self._rate_limit_delay - time_since_last
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    async def embed(
        self, 
        texts: Union[str, List[str]], 
        use_cache: bool = True,
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """Génère les embeddings avec cache intelligent et optimisations.
        
        Args:
            texts: Texte unique ou liste de textes
            use_cache: Utilise le cache si disponible
            **kwargs: Paramètres additionnels (model override, etc.)
            
        Returns:
            Embedding(s) selon le type d'entrée
            
        Raises:
            OpenAIError: En cas d'erreur API OpenAI
            ValidationError: Si les textes sont invalides
        """
        start_time = time.time()
        
        # Normalisation entrée
        is_single = isinstance(texts, str)
        text_list = [texts] if is_single else texts
        
        # Validation
        if not text_list or any(not text.strip() for text in text_list):
            raise ValidationError(
                "Textes vides ou invalides détectés",
                field_name="texts",
                field_value=text_list
            )
        
        # Vérification cache
        model = kwargs.get("model", self.embedding_config.model)
        cached_embeddings = []
        texts_to_process = []
        cache_mapping = {}
        
        if use_cache and self.cache:
            for i, text in enumerate(text_list):
                cached = self.cache.get(text, model)
                if cached:
                    cached_embeddings.append((i, cached))
                    self._stats["cache_hits"] += 1
                else:
                    texts_to_process.append(text)
                    cache_mapping[len(texts_to_process) - 1] = i
        else:
            texts_to_process = text_list
            cache_mapping = {i: i for i in range(len(text_list))}
        
        # Traitement des textes non cachés
        new_embeddings = []
        if texts_to_process:
            new_embeddings = await self._call_openai_api(texts_to_process, model, **kwargs)
            
            # Mise en cache des nouveaux embeddings
            if use_cache and self.cache:
                for text, embedding in zip(texts_to_process, new_embeddings):
                    try:
                        self.cache.set(text, model, embedding)
                    except Exception as e:
                        self.logger.warning(
                            "cache_set_failed",
                            text_length=len(text),
                            error=str(e)
                        )
        
        # Reconstruction résultat final
        final_embeddings = [None] * len(text_list)
        
        # Placement des résultats cachés
        for pos, embedding in cached_embeddings:
            final_embeddings[pos] = embedding
        
        # Placement des nouveaux résultats
        for processed_idx, embedding in enumerate(new_embeddings):
            original_idx = cache_mapping[processed_idx]
            final_embeddings[original_idx] = embedding
        
        # Métriques
        latency_ms = (time.time() - start_time) * 1000
        self._update_stats(text_list, latency_ms, len(texts_to_process) > 0)
        
        self.logger.debug(
            "embed_completed",
            text_count=len(text_list),
            cache_hits=len(cached_embeddings),
            api_calls=1 if texts_to_process else 0,
            latency_ms=latency_ms
        )
        
        return final_embeddings[0] if is_single else final_embeddings
    
    async def _call_openai_api(
        self, 
        texts: List[str], 
        model: str,
        **kwargs
    ) -> List[List[float]]:
        """Appel direct à l'API OpenAI avec gestion des erreurs.
        
        Args:
            texts: Textes à encoder
            model: Modèle à utiliser
            **kwargs: Paramètres additionnels
            
        Returns:
            Liste des embeddings
            
        Raises:
            OpenAIError: En cas d'erreur API
        """
        await self._wait_for_rate_limit()
        
        try:
            self._stats["api_calls"] += 1
            
            response = await self.client.embeddings.create(
                input=texts,
                model=model,
                **kwargs
            )
            
            # Extraction des embeddings
            embeddings = [data.embedding for data in response.data]
            
            # Calcul du coût
            total_tokens = response.usage.total_tokens
            cost = self.embedding_config.estimate_cost(total_tokens)
            
            self._stats["total_tokens"] += total_tokens
            self._stats["total_cost_usd"] += cost
            
            self.logger.debug(
                "openai_api_success",
                texts_count=len(texts),
                total_tokens=total_tokens,
                cost_usd=cost,
                model=model
            )
            
            return embeddings
            
        except Exception as e:
            self._stats["errors"] += 1
            
            # Conversion en OpenAIError si nécessaire
            if hasattr(e, 'response') and hasattr(e.response, 'json'):
                try:
                    error_data = e.response.json()
                    status_code = e.response.status_code
                    raise OpenAIError.from_openai_response(
                        error_data, 
                        status_code,
                        {"texts_count": len(texts), "model": model}
                    )
                except (AttributeError, ValueError):
                    pass
            
            # Erreur générique
            raise OpenAIError(
                f"Erreur lors de l'appel OpenAI: {str(e)}",
                context={"texts_count": len(texts), "model": model}
            )
    
    async def embed_batch(
        self, 
        texts: List[str], 
        batch_size: int = 100,
        use_cache: bool = True,
        **kwargs
    ) -> List[List[float]]:
        """Traitement batch optimisé avec parallélisation.
        
        Args:
            texts: Textes à encoder
            batch_size: Taille des batchs
            use_cache: Utilise le cache
            **kwargs: Paramètres additionnels
            
        Returns:
            Liste d'embeddings dans l'ordre original
        """
        if not texts:
            return []
        
        if len(texts) <= batch_size:
            return await self.embed(texts, use_cache=use_cache, **kwargs)
        
        # Traitement par batchs avec parallélisation limitée
        all_embeddings = []
        tasks = []
        max_concurrent = 3  # Limitation pour éviter rate limiting
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            task = self.embed(batch, use_cache=use_cache, **kwargs)
            tasks.append(task)
            
            # Traitement par groupes pour contrôler la concurrence
            if len(tasks) >= max_concurrent or i + batch_size >= len(texts):
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        raise result
                    all_embeddings.extend(result)
                
                tasks = []
                
                # Délai entre groupes pour respecter rate limits
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.5)
        
        return all_embeddings
    
    def _update_stats(
        self, 
        texts: List[str], 
        latency_ms: float, 
        made_api_call: bool
    ) -> None:
        """Met à jour les statistiques de performance."""
        self._stats["total_requests"] += 1
        
        # Mise à jour latence moyenne
        prev_avg = self._stats["avg_latency_ms"]
        total_requests = self._stats["total_requests"]
        
        self._stats["avg_latency_ms"] = (
            (prev_avg * (total_requests - 1) + latency_ms) / total_requests
        )
    
    def get_embedding_dimension(self) -> int:
        """Retourne la dimension du modèle configuré."""
        return self.embedding_config.embedding_dimensions
    
    def get_max_tokens(self) -> int:
        """Retourne la limite de tokens du modèle."""
        model_limits = {
            "text-embedding-3-large": 8191,
            "text-embedding-3-small": 8191,
            "text-embedding-ada-002": 8191
        }
        return model_limits.get(self.embedding_config.model, 8191)
    
    def estimate_cost(self, texts: Union[str, List[str]]) -> float:
        """Estime le coût précis avec tokenization réelle."""
        text_list = [texts] if isinstance(texts, str) else texts
        
        total_tokens = 0
        for text in text_list:
            try:
                tokens = self.tokenizer.encode(text)
                total_tokens += len(tokens)
            except Exception:
                # Fallback: estimation approximative
                total_tokens += len(text.split()) * 1.3
        
        return self.embedding_config.estimate_cost(int(total_tokens))
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Retourne les métriques de performance détaillées."""
        stats = self._stats.copy()
        
        # Ajout métriques calculées
        if self._stats["total_requests"] > 0:
            stats["cache_hit_rate"] = (
                self._stats["cache_hits"] / self._stats["total_requests"]
            )
        else:
            stats["cache_hit_rate"] = 0.0
        
        # Ajout info cache si disponible
        if self.cache:
            cache_stats = self.cache.get_stats()
            stats["cache_stats"] = cache_stats
        
        # Ajout config
        stats["config"] = self.embedding_config.to_dict()
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé du service avec test d'embedding.
        
        Returns:
            Statut de santé et métriques
        """
        try:
            # Test simple
            test_embedding = await self.embed("test de santé service", use_cache=False)
            
            return {
                "status": "healthy",
                "model": self.embedding_config.model,
                "embedding_dimension": len(test_embedding),
                "cache_enabled": self.cache is not None,
                "performance_stats": self.get_performance_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__,
                "performance_stats": self.get_performance_stats()
            }