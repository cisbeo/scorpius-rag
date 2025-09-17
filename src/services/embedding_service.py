"""Interface abstraite pour les services d'embedding."""

from abc import ABC, abstractmethod
from typing import List, Union, Dict, Any
import structlog


class EmbeddingService(ABC):
    """Interface abstraite pour tous les services d'embedding.
    
    Cette classe définit le contrat que doivent respecter tous les services
    d'embedding, permettant une architecture modulaire et extensible.
    
    Les implémentations concrètes doivent gérer:
    - L'authentification avec le provider
    - Le rate limiting et retry logic
    - La gestion des erreurs spécifiques au provider
    - L'optimisation des performances (batching, etc.)
    
    Examples:
        >>> service = ConcreteEmbeddingService(config)
        >>> embeddings = await service.embed(["text1", "text2"])
        >>> single_embedding = await service.embed("single text")
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialise le service d'embedding.
        
        Args:
            config: Configuration du service (clés API, modèles, etc.)
            
        Raises:
            ValidationError: Si la configuration est invalide
            ConfigurationError: Si des paramètres obligatoires manquent
        """
        self.config = config
        self.logger = structlog.get_logger(self.__class__.__name__)
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Valide la configuration spécifique au service.
        
        Raises:
            ValidationError: Si la configuration est invalide
            ConfigurationError: Si des paramètres obligatoires manquent
        """
        pass
    
    @abstractmethod
    async def embed(
        self, 
        texts: Union[str, List[str]], 
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """Génère les embeddings pour un ou plusieurs textes.
        
        Args:
            texts: Texte unique ou liste de textes à encoder
            **kwargs: Paramètres spécifiques au provider
            
        Returns:
            Embedding unique (List[float]) si texte unique,
            Liste d'embeddings (List[List[float]]) si liste de textes
            
        Raises:
            APIError: En cas d'erreur du service externe
            ValidationError: Si les textes sont invalides
            
        Examples:
            >>> # Embedding unique
            >>> embedding = await service.embed("Hello world")
            >>> len(embedding)  # 1536 pour text-embedding-3-small
            1536
            
            >>> # Embeddings multiples
            >>> embeddings = await service.embed(["text1", "text2"])
            >>> len(embeddings)
            2
        """
        pass
    
    @abstractmethod
    async def embed_batch(
        self, 
        texts: List[str], 
        batch_size: int = 100,
        **kwargs
    ) -> List[List[float]]:
        """Génère les embeddings en mode batch optimisé.
        
        Args:
            texts: Liste de textes à encoder
            batch_size: Taille des batchs pour traitement parallèle
            **kwargs: Paramètres spécifiques au provider
            
        Returns:
            Liste d'embeddings dans le même ordre que les textes
            
        Raises:
            APIError: En cas d'erreur du service externe
            ValidationError: Si les paramètres sont invalides
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Retourne la dimension des embeddings du modèle configuré.
        
        Returns:
            Nombre de dimensions des vecteurs d'embedding
        """
        pass
    
    @abstractmethod
    def get_max_tokens(self) -> int:
        """Retourne le nombre maximum de tokens supporté par le modèle.
        
        Returns:
            Limite de tokens en entrée
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, texts: Union[str, List[str]]) -> float:
        """Estime le coût en USD pour encoder les textes donnés.
        
        Args:
            texts: Texte(s) pour estimation du coût
            
        Returns:
            Coût estimé en USD
        """
        pass
    
    def get_service_info(self) -> Dict[str, Any]:
        """Retourne les informations sur le service configuré.
        
        Returns:
            Dictionnaire avec métadonnées du service
        """
        return {
            "service_type": self.__class__.__name__,
            "embedding_dimension": self.get_embedding_dimension(),
            "max_tokens": self.get_max_tokens(),
            "config_keys": list(self.config.keys())
        }