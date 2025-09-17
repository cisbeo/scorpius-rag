"""Exceptions de base pour Scorpius RAG."""

from typing import Optional, Dict, Any
import traceback
from datetime import datetime


class ScorpiusError(Exception):
    """Exception de base pour toutes les erreurs Scorpius RAG.
    
    Cette classe fournit une base commune pour toutes les exceptions du système,
    avec des fonctionnalités de logging enrichi et de traçabilité des erreurs.
    
    Attributes:
        message: Message d'erreur principal
        error_code: Code d'erreur pour catégorisation
        context: Contexte additionnel (métadonnées, params, etc.)
        timestamp: Horodatage de l'erreur
        correlation_id: ID de corrélation pour traçabilité
        
    Examples:
        >>> try:
        ...     raise ScorpiusError(
        ...         "Erreur de traitement",
        ...         error_code="PROC_001",
        ...         context={"operation": "search", "query": "test"}
        ...     )
        ... except ScorpiusError as e:
        ...     print(f"Erreur {e.error_code}: {e}")
        Erreur PROC_001: Erreur de traitement
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Initialise l'exception avec métadonnées enrichies.
        
        Args:
            message: Message d'erreur descriptif
            error_code: Code d'erreur pour catégorisation/routing
            context: Dictionnaire avec contexte additionnel
            correlation_id: ID pour traçabilité inter-services
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN"
        self.context = context or {}
        self.correlation_id = correlation_id
        self.timestamp = datetime.utcnow()
        self.traceback_info = traceback.format_exc()
    
    def __str__(self) -> str:
        """Représentation string enrichie de l'erreur."""
        base_msg = f"[{self.error_code}] {self.message}"
        if self.correlation_id:
            base_msg += f" (ID: {self.correlation_id})"
        return base_msg
    
    def __repr__(self) -> str:
        """Représentation détaillée pour debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code='{self.error_code}', "
            f"timestamp='{self.timestamp.isoformat()}'"
            f")"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise l'exception en dictionnaire pour logging structuré.
        
        Returns:
            Dictionnaire avec toutes les métadonnées de l'erreur
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback_info
        }
    
    def add_context(self, key: str, value: Any) -> "ScorpiusError":
        """Ajoute du contexte à l'exception existante.
        
        Args:
            key: Clé du contexte
            value: Valeur du contexte
            
        Returns:
            Self pour chaînage fluent
        """
        self.context[key] = value
        return self
    
    def with_correlation_id(self, correlation_id: str) -> "ScorpiusError":
        """Définit l'ID de corrélation.
        
        Args:
            correlation_id: ID de corrélation pour traçabilité
            
        Returns:
            Self pour chaînage fluent
        """
        self.correlation_id = correlation_id
        return self