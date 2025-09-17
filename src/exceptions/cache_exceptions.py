"""Exceptions liées au système de cache."""

from typing import Optional
from .base_exceptions import ScorpiusError


class CacheError(ScorpiusError):
    """Exception pour erreurs du système de cache des embeddings.
    
    Cette classe gère les erreurs spécifiques au cache des embeddings,
    incluant les problèmes de lecture/écriture, corruption, et expiration.
    
    Attributes:
        cache_key: Clé de cache concernée par l'erreur
        cache_operation: Opération qui a échoué (read, write, delete, etc.)
        cache_path: Chemin du fichier cache si applicable
    """
    
    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        cache_operation: Optional[str] = None,
        cache_path: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialise l'exception de cache.
        
        Args:
            message: Message d'erreur descriptif
            cache_key: Clé de cache concernée
            cache_operation: Type d'opération (read, write, delete, etc.)
            cache_path: Chemin du fichier cache
            **kwargs: Arguments additionnels pour ScorpiusError
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", "CACHE_ERROR"),
            **kwargs
        )
        self.cache_key = cache_key
        self.cache_operation = cache_operation
        self.cache_path = cache_path
        
        # Enrichissement du contexte
        self.context.update({
            "cache_key": self.cache_key,
            "cache_operation": self.cache_operation,
            "cache_path": self.cache_path
        })
    
    @classmethod
    def read_failed(cls, cache_key: str, cache_path: str, cause: str) -> "CacheError":
        """Erreur de lecture du cache.
        
        Args:
            cache_key: Clé de cache
            cache_path: Chemin du fichier
            cause: Cause de l'erreur
            
        Returns:
            Instance CacheError appropriée
        """
        return cls(
            message=f"Impossible de lire le cache pour '{cache_key}': {cause}",
            cache_key=cache_key,
            cache_operation="read",
            cache_path=cache_path,
            error_code="CACHE_READ_FAILED",
            context={"cause": cause}
        )
    
    @classmethod
    def write_failed(cls, cache_key: str, cache_path: str, cause: str) -> "CacheError":
        """Erreur d'écriture du cache.
        
        Args:
            cache_key: Clé de cache
            cache_path: Chemin du fichier
            cause: Cause de l'erreur
            
        Returns:
            Instance CacheError appropriée
        """
        return cls(
            message=f"Impossible d'écrire le cache pour '{cache_key}': {cause}",
            cache_key=cache_key,
            cache_operation="write",
            cache_path=cache_path,
            error_code="CACHE_WRITE_FAILED",
            context={"cause": cause}
        )
    
    @classmethod
    def corrupted_data(cls, cache_key: str, cache_path: str) -> "CacheError":
        """Erreur de données corrompues dans le cache.
        
        Args:
            cache_key: Clé de cache
            cache_path: Chemin du fichier
            
        Returns:
            Instance CacheError appropriée
        """
        return cls(
            message=f"Données corrompues dans le cache pour '{cache_key}'",
            cache_key=cache_key,
            cache_operation="read",
            cache_path=cache_path,
            error_code="CACHE_CORRUPTED_DATA"
        )
    
    @classmethod
    def invalid_key(cls, cache_key: str) -> "CacheError":
        """Erreur de clé de cache invalide.
        
        Args:
            cache_key: Clé invalide
            
        Returns:
            Instance CacheError appropriée
        """
        return cls(
            message=f"Clé de cache invalide: '{cache_key}'",
            cache_key=cache_key,
            cache_operation="validate",
            error_code="CACHE_INVALID_KEY"
        )
    
    @classmethod
    def directory_not_accessible(cls, cache_dir: str, cause: str) -> "CacheError":
        """Erreur d'accès au répertoire de cache.
        
        Args:
            cache_dir: Répertoire de cache
            cause: Cause de l'erreur
            
        Returns:
            Instance CacheError appropriée
        """
        return cls(
            message=f"Répertoire de cache non accessible '{cache_dir}': {cause}",
            cache_path=cache_dir,
            cache_operation="directory_access",
            error_code="CACHE_DIRECTORY_NOT_ACCESSIBLE",
            context={"cause": cause}
        )
    
    @classmethod
    def expired_entry(cls, cache_key: str, expiry_time: str) -> "CacheError":
        """Erreur d'entrée de cache expirée.
        
        Args:
            cache_key: Clé de cache
            expiry_time: Temps d'expiration
            
        Returns:
            Instance CacheError appropriée
        """
        return cls(
            message=f"Entrée de cache expirée pour '{cache_key}' (expirée le: {expiry_time})",
            cache_key=cache_key,
            cache_operation="read",
            error_code="CACHE_EXPIRED_ENTRY",
            context={"expiry_time": expiry_time}
        )
    
    @classmethod
    def size_limit_exceeded(
        cls, 
        cache_key: str, 
        data_size: int, 
        max_size: int
    ) -> "CacheError":
        """Erreur de dépassement de taille limite.
        
        Args:
            cache_key: Clé de cache
            data_size: Taille des données
            max_size: Taille maximale autorisée
            
        Returns:
            Instance CacheError appropriée
        """
        return cls(
            message=f"Taille limite dépassée pour '{cache_key}': {data_size} > {max_size} bytes",
            cache_key=cache_key,
            cache_operation="write",
            error_code="CACHE_SIZE_LIMIT_EXCEEDED",
            context={"data_size": data_size, "max_size": max_size}
        )
    
    @property
    def is_read_error(self) -> bool:
        """Indique si l'erreur est liée à une opération de lecture.
        
        Returns:
            True si erreur de lecture
        """
        return self.cache_operation == "read"
    
    @property
    def is_write_error(self) -> bool:
        """Indique si l'erreur est liée à une opération d'écriture.
        
        Returns:
            True si erreur d'écriture
        """
        return self.cache_operation == "write"
    
    @property
    def is_recoverable(self) -> bool:
        """Indique si l'erreur est récupérable (cache peut être reconstruit).
        
        Returns:
            True si l'erreur est récupérable
        """
        # Erreurs récupérables: corruption, expiration, clé invalide
        recoverable_codes = [
            "CACHE_CORRUPTED_DATA",
            "CACHE_EXPIRED_ENTRY", 
            "CACHE_INVALID_KEY",
            "CACHE_READ_FAILED"
        ]
        return self.error_code in recoverable_codes