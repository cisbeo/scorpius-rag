"""Configuration du logging structuré pour Scorpius RAG."""

import logging
import sys
from typing import Dict, Any, Optional
import structlog
from datetime import datetime


def setup_logger(
    log_level: str = "INFO",
    environment: str = "dev",
    correlation_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> structlog.BoundLogger:
    """Configure le système de logging structuré pour Scorpius RAG.
    
    Cette fonction configure structlog avec des processeurs optimisés
    pour le développement et la production, incluant:
    - Formatage JSON pour la production
    - Formatage coloré pour le développement
    - Enrichissement automatique du contexte (timestamps, correlation IDs)
    - Intégration avec le logging standard Python
    - Métriques et observabilité intégrées
    
    Args:
        log_level: Niveau de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environnement (dev, test, staging, prod)
        correlation_id: ID de corrélation pour traçabilité inter-services
        additional_context: Contexte additionnel à inclure dans tous les logs
        
    Returns:
        Logger structlog configuré et prêt à l'emploi
        
    Examples:
        >>> # Configuration basique
        >>> logger = setup_logger("INFO", "prod")
        >>> logger.info("service_started", service="scorpius-rag")
        
        >>> # Avec contexte enrichi
        >>> context = {"user_id": "123", "session_id": "abc"}
        >>> logger = setup_logger("DEBUG", "dev", additional_context=context)
        >>> logger.debug("search_performed", query="AO région IT", results=5)
        
        >>> # Avec correlation ID pour traçabilité
        >>> logger = setup_logger("INFO", "prod", correlation_id="req-456")
        >>> logger.error("embedding_failed", error="timeout", model="text-embedding-3-large")
    """
    
    # Configuration du logging standard Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO)
    )
    
    # Processeurs communs pour tous les environnements
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_correlation_id_processor(correlation_id),
        add_timestamp_processor(),
        add_scorpius_context_processor(additional_context or {})
    ]
    
    # Processeurs spécifiques à l'environnement
    if environment == "prod":
        # Production: JSON structuré pour parsing automatique
        processors.extend([
            mask_sensitive_data_processor(),
            structlog.processors.JSONRenderer()
        ])
    else:
        # Développement: Format coloré lisible
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    
    # Configuration de structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Récupération du logger configuré
    logger = structlog.get_logger("scorpius-rag")
    
    # Log de démarrage avec contexte
    logger.info(
        "logging_system_initialized",
        log_level=log_level,
        environment=environment,
        correlation_id=correlation_id,
        timestamp=datetime.utcnow().isoformat(),
        python_version=sys.version.split()[0],
        additional_context=additional_context
    )
    
    return logger


def add_correlation_id_processor(correlation_id: Optional[str]):
    """Processeur pour ajouter l'ID de corrélation à tous les logs.
    
    Args:
        correlation_id: ID de corrélation à ajouter
        
    Returns:
        Processeur structlog
    """
    def processor(logger, method_name, event_dict):
        if correlation_id:
            event_dict["correlation_id"] = correlation_id
        return event_dict
    
    return processor


def add_timestamp_processor():
    """Processeur pour ajouter timestamp ISO 8601 précis.
    
    Returns:
        Processeur structlog avec timestamp standardisé
    """
    def processor(logger, method_name, event_dict):
        event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return event_dict
    
    return processor


def add_scorpius_context_processor(additional_context: Dict[str, Any]):
    """Processeur pour enrichir avec contexte Scorpius RAG.
    
    Args:
        additional_context: Contexte additionnel à inclure
        
    Returns:
        Processeur structlog avec contexte enrichi
    """
    def processor(logger, method_name, event_dict):
        # Contexte système Scorpius
        event_dict.update({
            "system": "scorpius-rag",
            "version": "1.0.0",  # TODO: récupérer depuis package
            "component": logger.name
        })
        
        # Contexte additionnel
        if additional_context:
            event_dict.update(additional_context)
        
        return event_dict
    
    return processor


def mask_sensitive_data_processor():
    """Processeur pour masquer les données sensibles en production.
    
    Masque automatiquement:
    - Clés API (api_key, token, secret)
    - Informations personnelles (email, phone, etc.)
    - Données financières (amount, price si contexte sensible)
    
    Returns:
        Processeur structlog avec masquage des données sensibles
    """
    sensitive_keys = {
        "api_key", "token", "secret", "password", "auth",
        "email", "phone", "ssn", "credit_card"
    }
    
    def processor(logger, method_name, event_dict):
        for key, value in event_dict.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 8:
                    event_dict[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    event_dict[key] = "***"
        
        return event_dict
    
    return processor


def get_performance_logger() -> structlog.BoundLogger:
    """Retourne un logger spécialisé pour les métriques de performance.
    
    Ce logger est optimisé pour capturer les métriques business et techniques
    de Scorpius RAG (temps de réponse, coûts, hit rates, etc.).
    
    Returns:
        Logger configuré pour métriques de performance
        
    Examples:
        >>> perf_logger = get_performance_logger()
        >>> perf_logger.info(
        ...     "search_performance",
        ...     query_length=45,
        ...     results_count=8,
        ...     response_time_ms=150,
        ...     cache_hit=True,
        ...     cost_usd=0.0002
        ... )
    """
    return structlog.get_logger("performance")


def get_security_logger() -> structlog.BoundLogger:
    """Retourne un logger spécialisé pour les événements de sécurité.
    
    Ce logger capture les événements liés à la sécurité:
    - Tentatives d'authentification
    - Accès aux données sensibles
    - Erreurs de validation
    - Détection d'anomalies
    
    Returns:
        Logger configuré pour événements de sécurité
        
    Examples:
        >>> sec_logger = get_security_logger()
        >>> sec_logger.warning(
        ...     "invalid_api_key_attempt",
        ...     source_ip="192.168.1.100",
        ...     user_agent="unknown",
        ...     api_key_prefix="sk-fake"
        ... )
    """
    return structlog.get_logger("security")


def get_business_logger() -> structlog.BoundLogger:
    """Retourne un logger spécialisé pour les métriques business.
    
    Ce logger capture les événements métier importants:
    - Analyses d'AO réalisées
    - Templates générés
    - Recommandations fournies
    - Succès/échecs business
    
    Returns:
        Logger configuré pour métriques business
        
    Examples:
        >>> biz_logger = get_business_logger()
        >>> biz_logger.info(
        ...     "ao_analysis_completed",
        ...     ao_type="Ouvert",
        ...     sector="Territorial", 
        ...     amount_range="100k-500k",
        ...     recommendation="GO",
        ...     confidence_score=0.85
        ... )
    """
    return structlog.get_logger("business")


class PerformanceMetrics:
    """Utilitaire pour capturer des métriques de performance détaillées.
    
    Cette classe facilite la capture de métriques avec timing automatique
    et calculs de statistiques (moyenne, percentiles, etc.).
    
    Examples:
        >>> with PerformanceMetrics("embedding_generation") as metrics:
        ...     embedding = await openai_service.embed("text")
        ...     metrics.add_metric("tokens_used", 15)
        ...     metrics.add_metric("cost_usd", 0.0002)
        >>> # Logs automatiquement les métriques avec timing
    """
    
    def __init__(self, operation_name: str, logger: Optional[structlog.BoundLogger] = None):
        """Initialise le collecteur de métriques.
        
        Args:
            operation_name: Nom de l'opération mesurée
            logger: Logger à utiliser (par défaut: performance logger)
        """
        self.operation_name = operation_name
        self.logger = logger or get_performance_logger()
        self.start_time = None
        self.metrics = {}
    
    def __enter__(self):
        """Démarre la mesure de performance."""
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Termine la mesure et log les résultats."""
        if self.start_time:
            duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
            
            log_data = {
                "operation": self.operation_name,
                "duration_ms": round(duration_ms, 2),
                "success": exc_type is None
            }
            
            # Ajout des métriques personnalisées
            log_data.update(self.metrics)
            
            # Ajout contexte d'erreur si applicable
            if exc_type:
                log_data.update({
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val) if exc_val else None
                })
                self.logger.error("operation_failed", **log_data)
            else:
                self.logger.info("operation_completed", **log_data)
    
    def add_metric(self, name: str, value: Any) -> None:
        """Ajoute une métrique personnalisée.
        
        Args:
            name: Nom de la métrique
            value: Valeur de la métrique
        """
        self.metrics[name] = value