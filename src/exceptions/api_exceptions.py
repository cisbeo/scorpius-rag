"""Exceptions liées aux APIs externes (OpenAI, ChromaDB)."""

from typing import Optional, Dict, Any
from .base_exceptions import ScorpiusError


class APIError(ScorpiusError):
    """Exception de base pour toutes les erreurs d'API externe.
    
    Cette classe encapsule les erreurs provenant des services externes
    avec des informations spécifiques aux APIs (status codes, headers, etc.).
    
    Attributes:
        status_code: Code de statut HTTP si applicable
        response_data: Données de réponse de l'API
        request_data: Données de la requête qui a échoué
        api_provider: Nom du fournisseur d'API (OpenAI, ChromaDB, etc.)
        retry_after: Délai suggéré avant nouvelle tentative (en secondes)
    """
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        request_data: Optional[Dict[str, Any]] = None,
        api_provider: Optional[str] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ) -> None:
        """Initialise l'exception API avec métadonnées spécifiques.
        
        Args:
            message: Message d'erreur descriptif
            status_code: Code de statut HTTP
            response_data: Réponse complète de l'API
            request_data: Données de la requête (sans secrets)
            api_provider: Nom du fournisseur d'API
            retry_after: Délai recommandé avant retry
            **kwargs: Arguments additionnels pour ScorpiusError
        """
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_data = response_data or {}
        self.request_data = request_data or {}
        self.api_provider = api_provider or "Unknown"
        self.retry_after = retry_after
        
        # Enrichissement du contexte avec infos API
        self.context.update({
            "api_provider": self.api_provider,
            "status_code": self.status_code,
            "retry_after": self.retry_after,
            "response_size": len(str(self.response_data)) if self.response_data else 0
        })
    
    @property
    def is_retryable(self) -> bool:
        """Indique si l'erreur peut justifier une nouvelle tentative.
        
        Returns:
            True pour erreurs temporaires (5xx, rate limiting, timeout)
        """
        if self.status_code:
            # Erreurs serveur ou rate limiting
            return self.status_code >= 500 or self.status_code == 429
        return False
    
    @property
    def is_authentication_error(self) -> bool:
        """Indique si l'erreur est liée à l'authentification.
        
        Returns:
            True pour erreurs 401/403
        """
        return self.status_code in [401, 403]
    
    @property
    def is_rate_limited(self) -> bool:
        """Indique si l'erreur est due au rate limiting.
        
        Returns:
            True pour erreur 429
        """
        return self.status_code == 429


class OpenAIError(APIError):
    """Exception spécifique aux erreurs OpenAI.
    
    Cette classe gère les erreurs spécifiques à l'API OpenAI avec
    des codes d'erreur et patterns de retry appropriés.
    """
    
    def __init__(self, message: str, **kwargs) -> None:
        """Initialise l'exception OpenAI.
        
        Args:
            message: Message d'erreur
            **kwargs: Arguments pour APIError
        """
        super().__init__(
            message,
            api_provider="OpenAI",
            error_code=kwargs.pop("error_code", "OPENAI_ERROR"),
            **kwargs
        )
    
    @classmethod
    def from_openai_response(
        cls,
        response_data: Dict[str, Any],
        status_code: int,
        request_data: Optional[Dict[str, Any]] = None
    ) -> "OpenAIError":
        """Crée une exception à partir d'une réponse d'erreur OpenAI.
        
        Args:
            response_data: Réponse JSON de l'API OpenAI
            status_code: Code de statut HTTP
            request_data: Données de la requête (optionnel)
            
        Returns:
            Instance OpenAIError appropriée
        """
        error_info = response_data.get("error", {})
        message = error_info.get("message", "Erreur OpenAI inconnue")
        error_type = error_info.get("type", "unknown")
        error_code = error_info.get("code", "unknown")
        
        # Mapping des codes d'erreur OpenAI vers nos codes
        code_mapping = {
            "insufficient_quota": "OPENAI_QUOTA_EXCEEDED",
            "rate_limit_exceeded": "OPENAI_RATE_LIMIT",
            "invalid_api_key": "OPENAI_AUTH_ERROR",
            "model_not_found": "OPENAI_MODEL_ERROR",
            "context_length_exceeded": "OPENAI_CONTEXT_ERROR"
        }
        
        scorpius_error_code = code_mapping.get(error_code, f"OPENAI_{error_type.upper()}")
        
        return cls(
            message=f"OpenAI API Error: {message}",
            status_code=status_code,
            response_data=response_data,
            request_data=request_data,
            error_code=scorpius_error_code
        )
    
    @property
    def is_quota_exceeded(self) -> bool:
        """Indique si l'erreur est due au dépassement de quota.
        
        Returns:
            True si quota dépassé
        """
        return self.error_code == "OPENAI_QUOTA_EXCEEDED"
    
    @property
    def is_context_too_long(self) -> bool:
        """Indique si l'erreur est due à un contexte trop long.
        
        Returns:
            True si contexte dépasse la limite
        """
        return self.error_code == "OPENAI_CONTEXT_ERROR"


class ChromaDBError(APIError):
    """Exception spécifique aux erreurs ChromaDB.
    
    Cette classe gère les erreurs spécifiques à ChromaDB avec
    des patterns de retry et recovery appropriés.
    """
    
    def __init__(self, message: str, **kwargs) -> None:
        """Initialise l'exception ChromaDB.
        
        Args:
            message: Message d'erreur
            **kwargs: Arguments pour APIError
        """
        super().__init__(
            message,
            api_provider="ChromaDB",
            error_code=kwargs.pop("error_code", "CHROMA_ERROR"),
            **kwargs
        )
    
    @classmethod
    def collection_not_found(cls, collection_name: str) -> "ChromaDBError":
        """Erreur de collection introuvable.
        
        Args:
            collection_name: Nom de la collection
            
        Returns:
            Instance ChromaDBError appropriée
        """
        return cls(
            message=f"Collection ChromaDB '{collection_name}' introuvable",
            error_code="CHROMA_COLLECTION_NOT_FOUND",
            context={"collection_name": collection_name}
        )
    
    @classmethod
    def connection_failed(cls, host: str, port: int) -> "ChromaDBError":
        """Erreur de connexion à ChromaDB.
        
        Args:
            host: Host ChromaDB
            port: Port ChromaDB
            
        Returns:
            Instance ChromaDBError appropriée
        """
        return cls(
            message=f"Impossible de se connecter à ChromaDB {host}:{port}",
            error_code="CHROMA_CONNECTION_FAILED",
            context={"host": host, "port": port}
        )
    
    @classmethod
    def invalid_embedding_dimension(
        cls, 
        expected: int, 
        received: int
    ) -> "ChromaDBError":
        """Erreur de dimension d'embedding invalide.
        
        Args:
            expected: Dimension attendue
            received: Dimension reçue
            
        Returns:
            Instance ChromaDBError appropriée
        """
        return cls(
            message=f"Dimension embedding invalide: attendu {expected}, reçu {received}",
            error_code="CHROMA_INVALID_DIMENSION",
            context={"expected_dimension": expected, "received_dimension": received}
        )
    
    @property
    def is_connection_error(self) -> bool:
        """Indique si l'erreur est liée à la connexion.
        
        Returns:
            True si erreur de connexion
        """
        return self.error_code == "CHROMA_CONNECTION_FAILED"
    
    @property
    def is_collection_error(self) -> bool:
        """Indique si l'erreur est liée aux collections.
        
        Returns:
            True si erreur de collection
        """
        return self.error_code.startswith("CHROMA_COLLECTION")