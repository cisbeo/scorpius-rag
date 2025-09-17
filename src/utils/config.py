"""Configuration centralisée pour Scorpius RAG via variables d'environnement."""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import structlog

from ..exceptions import ConfigurationError


@dataclass
class Config:
    """Configuration centralisée du système Scorpius RAG.
    
    Cette classe centralise toute la configuration système en récupérant
    les valeurs depuis les variables d'environnement avec validation
    et valeurs par défaut appropriées.
    
    Attributes:
        # OpenAI Configuration
        openai_api_key: Clé API OpenAI
        openai_model: Modèle d'embedding à utiliser
        openai_base_url: URL de base API OpenAI
        openai_timeout: Timeout des requêtes en secondes
        openai_max_retries: Nombre maximum de tentatives
        
        # ChromaDB Configuration  
        chroma_host: Host ChromaDB
        chroma_port: Port ChromaDB
        chroma_persistent_path: Chemin persistance ChromaDB
        
        # Cache Configuration
        cache_enabled: Activation du cache embeddings
        cache_dir: Répertoire de stockage cache
        cache_ttl_hours: Durée de vie cache en heures
        cache_max_size_mb: Taille maximale cache en MB
        
        # Application Configuration
        log_level: Niveau de logging
        environment: Environnement (dev, prod, test)
        debug_mode: Mode debug activé
        
    Examples:
        >>> config = Config.from_env()
        >>> print(f"Modèle: {config.openai_model}")
        >>> print(f"Cache activé: {config.cache_enabled}")
        >>> 
        >>> # Validation
        >>> config.validate()
        >>> 
        >>> # Export pour services
        >>> openai_config = config.get_openai_config()
        >>> chroma_config = config.get_chromadb_config()
    """
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "text-embedding-3-large"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout: int = 30
    openai_max_retries: int = 3
    openai_rate_limit_rpm: int = 3000
    
    # ChromaDB Configuration
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_persistent_path: str = "./data/chromadb"
    
    # Cache Configuration
    cache_enabled: bool = True
    cache_dir: str = "./cache/embeddings"
    cache_ttl_hours: int = 24
    cache_max_size_mb: int = 500
    
    # Application Configuration
    log_level: str = "INFO"
    environment: str = "dev"
    debug_mode: bool = False
    
    # Performance Configuration
    embedding_batch_size: int = 100
    max_concurrent_requests: int = 5
    
    @classmethod
    def from_env(cls) -> "Config":
        """Crée la configuration à partir des variables d'environnement.
        
        Variables d'environnement supportées:
        
        OpenAI:
        - OPENAI_API_KEY (obligatoire)
        - OPENAI_EMBEDDING_MODEL
        - OPENAI_BASE_URL
        - OPENAI_TIMEOUT
        - OPENAI_MAX_RETRIES
        - OPENAI_RATE_LIMIT_RPM
        
        ChromaDB:
        - CHROMA_HOST
        - CHROMA_PORT
        - CHROMA_PERSISTENT_PATH
        
        Cache:
        - CACHE_ENABLED
        - CACHE_DIR
        - CACHE_TTL_HOURS
        - CACHE_MAX_SIZE_MB
        
        Application:
        - LOG_LEVEL
        - ENVIRONMENT
        - DEBUG_MODE
        
        Performance:
        - EMBEDDING_BATCH_SIZE
        - MAX_CONCURRENT_REQUESTS
        
        Returns:
            Instance Config configurée
            
        Raises:
            ConfigurationError: Si configuration obligatoire manquante
            
        Examples:
            >>> import os
            >>> os.environ["OPENAI_API_KEY"] = "sk-..."
            >>> config = Config.from_env()
        """
        logger = structlog.get_logger("Config")
        
        # Récupération OpenAI (obligatoire)
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ConfigurationError.missing_env_var("OPENAI_API_KEY")
        
        # Récupération et conversion des autres variables
        try:
            config = cls(
                # OpenAI
                openai_api_key=openai_api_key,
                openai_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
                openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                openai_timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
                openai_max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
                openai_rate_limit_rpm=int(os.getenv("OPENAI_RATE_LIMIT_RPM", "3000")),
                
                # ChromaDB
                chroma_host=os.getenv("CHROMA_HOST", "localhost"),
                chroma_port=int(os.getenv("CHROMA_PORT", "8000")),
                chroma_persistent_path=os.getenv("CHROMA_PERSISTENT_PATH", "./data/chromadb"),
                
                # Cache
                cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
                cache_dir=os.getenv("CACHE_DIR", "./cache/embeddings"),
                cache_ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24")),
                cache_max_size_mb=int(os.getenv("CACHE_MAX_SIZE_MB", "500")),
                
                # Application
                log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
                environment=os.getenv("ENVIRONMENT", "dev").lower(),
                debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
                
                # Performance
                embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "100")),
                max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
            )
            
            logger.info(
                "config_loaded_from_env",
                environment=config.environment,
                openai_model=config.openai_model,
                cache_enabled=config.cache_enabled,
                chroma_host=config.chroma_host
            )
            
            return config
            
        except ValueError as e:
            raise ConfigurationError(
                f"Erreur de conversion des variables d'environnement: {e}",
                error_code="ENV_VAR_CONVERSION_ERROR"
            )
    
    def validate(self) -> None:
        """Valide la cohérence de la configuration.
        
        Raises:
            ConfigurationError: Si la configuration est incohérente
        """
        errors = []
        
        # Validation OpenAI
        if not self.openai_api_key.startswith(("sk-", "sk-proj-")):
            errors.append("OPENAI_API_KEY: Format invalide (doit commencer par sk-)")
        
        valid_models = ["text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"]
        if self.openai_model not in valid_models:
            errors.append(f"OPENAI_EMBEDDING_MODEL: Modèle non supporté (valides: {valid_models})")
        
        if self.openai_timeout <= 0:
            errors.append("OPENAI_TIMEOUT: Doit être positif")
        
        if self.openai_max_retries < 0:
            errors.append("OPENAI_MAX_RETRIES: Doit être >= 0")
        
        if self.openai_rate_limit_rpm <= 0:
            errors.append("OPENAI_RATE_LIMIT_RPM: Doit être positif")
        
        # Validation ChromaDB
        if not 1 <= self.chroma_port <= 65535:
            errors.append("CHROMA_PORT: Doit être entre 1 et 65535")
        
        # Validation Cache
        if self.cache_ttl_hours <= 0:
            errors.append("CACHE_TTL_HOURS: Doit être positif")
        
        if self.cache_max_size_mb <= 0:
            errors.append("CACHE_MAX_SIZE_MB: Doit être positif")
        
        # Validation Application
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            errors.append(f"LOG_LEVEL: Niveau invalide (valides: {valid_log_levels})")
        
        valid_environments = ["dev", "test", "staging", "prod"]
        if self.environment not in valid_environments:
            errors.append(f"ENVIRONMENT: Environnement invalide (valides: {valid_environments})")
        
        # Validation Performance
        if self.embedding_batch_size <= 0:
            errors.append("EMBEDDING_BATCH_SIZE: Doit être positif")
        
        if self.max_concurrent_requests <= 0:
            errors.append("MAX_CONCURRENT_REQUESTS: Doit être positif")
        
        # Lever erreur si problèmes détectés
        if errors:
            raise ConfigurationError(
                f"Configuration invalide: {'; '.join(errors)}",
                error_code="CONFIG_VALIDATION_FAILED",
                context={"validation_errors": errors}
            )
    
    def get_openai_config(self) -> Dict[str, Any]:
        """Extrait la configuration OpenAI pour le service d'embedding.
        
        Returns:
            Dictionnaire avec paramètres OpenAI
        """
        return {
            "api_key": self.openai_api_key,
            "model": self.openai_model,
            "base_url": self.openai_base_url,
            "timeout": self.openai_timeout,
            "max_retries": self.openai_max_retries,
            "rate_limit_rpm": self.openai_rate_limit_rpm,
            "batch_size": self.embedding_batch_size,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_hours": self.cache_ttl_hours
        }
    
    def get_chromadb_config(self) -> Dict[str, Any]:
        """Extrait la configuration ChromaDB.
        
        Returns:
            Dictionnaire avec paramètres ChromaDB
        """
        return {
            "host": self.chroma_host,
            "port": self.chroma_port,
            "persistent_path": self.chroma_persistent_path
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Extrait la configuration du cache.
        
        Returns:
            Dictionnaire avec paramètres cache
        """
        return {
            "enabled": self.cache_enabled,
            "cache_dir": self.cache_dir,
            "ttl_hours": self.cache_ttl_hours,
            "max_size_mb": self.cache_max_size_mb
        }
    
    def is_production(self) -> bool:
        """Indique si on est en environnement de production.
        
        Returns:
            True si environnement de production
        """
        return self.environment == "prod"
    
    def is_development(self) -> bool:
        """Indique si on est en environnement de développement.
        
        Returns:
            True si environnement de développement
        """
        return self.environment == "dev"
    
    def get_masked_config(self) -> Dict[str, Any]:
        """Retourne la configuration avec valeurs sensibles masquées.
        
        Utile pour logging et debugging sans exposer les secrets.
        
        Returns:
            Configuration avec clés API masquées
        """
        config_dict = {
            # OpenAI (masqué)
            "openai_api_key": f"{self.openai_api_key[:8]}...{self.openai_api_key[-4:]}",
            "openai_model": self.openai_model,
            "openai_base_url": self.openai_base_url,
            "openai_timeout": self.openai_timeout,
            "openai_max_retries": self.openai_max_retries,
            "openai_rate_limit_rpm": self.openai_rate_limit_rpm,
            
            # ChromaDB
            "chroma_host": self.chroma_host,
            "chroma_port": self.chroma_port,
            "chroma_persistent_path": self.chroma_persistent_path,
            
            # Cache
            "cache_enabled": self.cache_enabled,
            "cache_dir": self.cache_dir,
            "cache_ttl_hours": self.cache_ttl_hours,
            "cache_max_size_mb": self.cache_max_size_mb,
            
            # Application
            "log_level": self.log_level,
            "environment": self.environment,
            "debug_mode": self.debug_mode,
            
            # Performance
            "embedding_batch_size": self.embedding_batch_size,
            "max_concurrent_requests": self.max_concurrent_requests
        }
        
        return config_dict
    
    def to_env_file(self, file_path: str = ".env") -> None:
        """Génère un fichier .env d'exemple avec la configuration actuelle.
        
        Args:
            file_path: Chemin du fichier .env à générer
            
        Examples:
            >>> config = Config.from_env()
            >>> config.to_env_file(".env.example")
        """
        env_content = f"""# Configuration Scorpius RAG
# Generated on {os.popen('date').read().strip()}

# ===== OpenAI Configuration =====
OPENAI_API_KEY={self.openai_api_key}
OPENAI_EMBEDDING_MODEL={self.openai_model}
OPENAI_BASE_URL={self.openai_base_url}
OPENAI_TIMEOUT={self.openai_timeout}
OPENAI_MAX_RETRIES={self.openai_max_retries}
OPENAI_RATE_LIMIT_RPM={self.openai_rate_limit_rpm}

# ===== ChromaDB Configuration =====
CHROMA_HOST={self.chroma_host}
CHROMA_PORT={self.chroma_port}
CHROMA_PERSISTENT_PATH={self.chroma_persistent_path}

# ===== Cache Configuration =====
CACHE_ENABLED={str(self.cache_enabled).lower()}
CACHE_DIR={self.cache_dir}
CACHE_TTL_HOURS={self.cache_ttl_hours}
CACHE_MAX_SIZE_MB={self.cache_max_size_mb}

# ===== Application Configuration =====
LOG_LEVEL={self.log_level}
ENVIRONMENT={self.environment}
DEBUG_MODE={str(self.debug_mode).lower()}

# ===== Performance Configuration =====
EMBEDDING_BATCH_SIZE={self.embedding_batch_size}
MAX_CONCURRENT_REQUESTS={self.max_concurrent_requests}
"""
        
        with open(file_path, 'w') as f:
            f.write(env_content)
        
        structlog.get_logger("Config").info(
            "env_file_generated",
            file_path=file_path
        )