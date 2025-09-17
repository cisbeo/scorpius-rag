"""Configuration pour les services d'embedding OpenAI."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import os


@dataclass
class EmbeddingConfig:
    """Configuration pour le service d'embedding OpenAI.
    
    Cette classe centralise tous les paramètres de configuration nécessaires
    pour le service d'embeddings, incluant l'authentification, les modèles,
    et les paramètres de performance.
    
    Attributes:
        api_key: Clé API OpenAI (récupérée depuis env si None)
        model: Modèle d'embedding à utiliser
        base_url: URL de base de l'API OpenAI
        timeout: Timeout des requêtes en secondes
        max_retries: Nombre maximum de tentatives en cas d'erreur
        retry_delay: Délai entre les tentatives en secondes
        batch_size: Taille des batchs pour traitement parallèle
        rate_limit_rpm: Limite de requêtes par minute
        cache_enabled: Activation du cache des embeddings
        cache_ttl_hours: Durée de vie du cache en heures
        
    Examples:
        >>> config = EmbeddingConfig(
        ...     model="text-embedding-3-large",
        ...     batch_size=50,
        ...     cache_enabled=True
        ... )
        >>> print(f"Modèle: {config.model}, Cache: {config.cache_enabled}")
        Modèle: text-embedding-3-large, Cache: True
    """
    api_key: Optional[str] = None
    model: str = "text-embedding-3-large"
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    batch_size: int = 100
    rate_limit_rpm: int = 3000
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    
    def __post_init__(self) -> None:
        """Initialisation et validation de la configuration."""
        # Récupération de la clé API depuis l'environnement si non fournie
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Validation de la clé API
        if not self.api_key:
            raise ValueError(
                "Clé API OpenAI manquante. Définissez OPENAI_API_KEY dans "
                "les variables d'environnement ou passez api_key au constructeur."
            )
        
        # Validation du modèle
        valid_models = [
            "text-embedding-3-large",
            "text-embedding-3-small", 
            "text-embedding-ada-002"
        ]
        if self.model not in valid_models:
            raise ValueError(
                f"Modèle non supporté: {self.model}. "
                f"Modèles valides: {', '.join(valid_models)}"
            )
        
        # Validation des paramètres numériques
        if self.timeout <= 0:
            raise ValueError(f"timeout doit être positif, reçu: {self.timeout}")
        
        if self.max_retries < 0:
            raise ValueError(f"max_retries doit être >= 0, reçu: {self.max_retries}")
        
        if self.retry_delay < 0:
            raise ValueError(f"retry_delay doit être >= 0, reçu: {self.retry_delay}")
        
        if self.batch_size <= 0:
            raise ValueError(f"batch_size doit être positif, reçu: {self.batch_size}")
        
        if self.rate_limit_rpm <= 0:
            raise ValueError(f"rate_limit_rpm doit être positif, reçu: {self.rate_limit_rpm}")
        
        if self.cache_ttl_hours <= 0:
            raise ValueError(f"cache_ttl_hours doit être positif, reçu: {self.cache_ttl_hours}")
    
    @property
    def masked_api_key(self) -> str:
        """Clé API masquée pour l'affichage sécurisé.
        
        Returns:
            Clé API avec seuls les 8 premiers caractères visibles
        """
        if not self.api_key:
            return "Non définie"
        return f"{self.api_key[:8]}...{self.api_key[-4:]}"
    
    @property
    def embedding_dimensions(self) -> int:
        """Nombre de dimensions du modèle d'embedding.
        
        Returns:
            Dimensions selon le modèle configuré
        """
        dimensions_map = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536
        }
        return dimensions_map.get(self.model, 1536)
    
    @property
    def cost_per_1k_tokens(self) -> float:
        """Coût par 1000 tokens selon le modèle.
        
        Returns:
            Coût en USD pour 1000 tokens
        """
        cost_map = {
            "text-embedding-3-large": 0.00013,
            "text-embedding-3-small": 0.00002,
            "text-embedding-ada-002": 0.0001
        }
        return cost_map.get(self.model, 0.0001)
    
    def get_rate_limit_delay(self) -> float:
        """Calcule le délai minimum entre requêtes pour respecter le rate limit.
        
        Returns:
            Délai en secondes entre les requêtes
        """
        return 60.0 / self.rate_limit_rpm
    
    def estimate_cost(self, total_tokens: int) -> float:
        """Estime le coût total pour un nombre de tokens.
        
        Args:
            total_tokens: Nombre total de tokens à traiter
            
        Returns:
            Coût estimé en USD
        """
        return (total_tokens / 1000) * self.cost_per_1k_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour logging/debugging.
        
        Returns:
            Dictionnaire avec configuration (clé API masquée)
        """
        return {
            "api_key": self.masked_api_key,
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "batch_size": self.batch_size,
            "rate_limit_rpm": self.rate_limit_rpm,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_hours": self.cache_ttl_hours,
            "embedding_dimensions": self.embedding_dimensions,
            "cost_per_1k_tokens": self.cost_per_1k_tokens
        }
    
    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        """Crée une configuration à partir des variables d'environnement.
        
        Variables d'environnement supportées:
        - OPENAI_API_KEY: Clé API (obligatoire)
        - OPENAI_EMBEDDING_MODEL: Modèle d'embedding (optionnel)
        - OPENAI_BASE_URL: URL de base (optionnel) 
        - OPENAI_TIMEOUT: Timeout en secondes (optionnel)
        - EMBEDDING_BATCH_SIZE: Taille des batchs (optionnel)
        - EMBEDDING_CACHE_ENABLED: Activation cache (optionnel)
        
        Returns:
            Instance EmbeddingConfig configurée
            
        Examples:
            >>> import os
            >>> os.environ["OPENAI_API_KEY"] = "sk-..."
            >>> config = EmbeddingConfig.from_env()
            >>> print(config.model)
            text-embedding-3-large
        """
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
            batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "100")),
            cache_enabled=os.getenv("EMBEDDING_CACHE_ENABLED", "true").lower() == "true"
        )