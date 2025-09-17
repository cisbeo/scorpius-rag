"""Exceptions de validation et configuration."""

from typing import List, Optional, Dict, Any
from .base_exceptions import ScorpiusError


class ValidationError(ScorpiusError):
    """Exception pour erreurs de validation de données.
    
    Cette classe gère les erreurs de validation des entrées utilisateur,
    des paramètres de requête, et des données métier.
    
    Attributes:
        field_name: Nom du champ en erreur
        field_value: Valeur invalide
        expected_type: Type attendu
        validation_rules: Règles de validation violées
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        expected_type: Optional[str] = None,
        validation_rules: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """Initialise l'exception de validation.
        
        Args:
            message: Message d'erreur descriptif
            field_name: Nom du champ en erreur
            field_value: Valeur qui a causé l'erreur
            expected_type: Type de données attendu
            validation_rules: Liste des règles violées
            **kwargs: Arguments additionnels pour ScorpiusError
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", "VALIDATION_ERROR"),
            **kwargs
        )
        self.field_name = field_name
        self.field_value = field_value
        self.expected_type = expected_type
        self.validation_rules = validation_rules or []
        
        # Enrichissement du contexte
        self.context.update({
            "field_name": self.field_name,
            "field_value": str(self.field_value) if self.field_value is not None else None,
            "expected_type": self.expected_type,
            "validation_rules": self.validation_rules
        })
    
    @classmethod
    def required_field_missing(cls, field_name: str) -> "ValidationError":
        """Erreur de champ obligatoire manquant.
        
        Args:
            field_name: Nom du champ manquant
            
        Returns:
            Instance ValidationError appropriée
        """
        return cls(
            message=f"Champ obligatoire manquant: {field_name}",
            field_name=field_name,
            error_code="REQUIRED_FIELD_MISSING",
            validation_rules=["required"]
        )
    
    @classmethod
    def invalid_type(
        cls, 
        field_name: str, 
        field_value: Any, 
        expected_type: str
    ) -> "ValidationError":
        """Erreur de type invalide.
        
        Args:
            field_name: Nom du champ
            field_value: Valeur invalide
            expected_type: Type attendu
            
        Returns:
            Instance ValidationError appropriée
        """
        return cls(
            message=f"Type invalide pour {field_name}: attendu {expected_type}, reçu {type(field_value).__name__}",
            field_name=field_name,
            field_value=field_value,
            expected_type=expected_type,
            error_code="INVALID_TYPE"
        )
    
    @classmethod
    def value_out_of_range(
        cls,
        field_name: str,
        field_value: Any,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None
    ) -> "ValidationError":
        """Erreur de valeur hors plage.
        
        Args:
            field_name: Nom du champ
            field_value: Valeur hors plage
            min_value: Valeur minimale autorisée
            max_value: Valeur maximale autorisée
            
        Returns:
            Instance ValidationError appropriée
        """
        range_desc = []
        if min_value is not None:
            range_desc.append(f">= {min_value}")
        if max_value is not None:
            range_desc.append(f"<= {max_value}")
        
        range_str = " et ".join(range_desc)
        
        return cls(
            message=f"Valeur hors plage pour {field_name}: {field_value} (attendu: {range_str})",
            field_name=field_name,
            field_value=field_value,
            error_code="VALUE_OUT_OF_RANGE",
            context={"min_value": min_value, "max_value": max_value}
        )
    
    @classmethod
    def invalid_format(
        cls,
        field_name: str,
        field_value: Any,
        expected_format: str
    ) -> "ValidationError":
        """Erreur de format invalide.
        
        Args:
            field_name: Nom du champ
            field_value: Valeur au format invalide
            expected_format: Format attendu
            
        Returns:
            Instance ValidationError appropriée
        """
        return cls(
            message=f"Format invalide pour {field_name}: '{field_value}' (attendu: {expected_format})",
            field_name=field_name,
            field_value=field_value,
            error_code="INVALID_FORMAT",
            context={"expected_format": expected_format}
        )
    
    @classmethod
    def invalid_enum_value(
        cls,
        field_name: str,
        field_value: Any,
        valid_values: List[str]
    ) -> "ValidationError":
        """Erreur de valeur enum invalide.
        
        Args:
            field_name: Nom du champ
            field_value: Valeur invalide
            valid_values: Liste des valeurs valides
            
        Returns:
            Instance ValidationError appropriée
        """
        return cls(
            message=f"Valeur invalide pour {field_name}: '{field_value}' (valeurs valides: {', '.join(valid_values)})",
            field_name=field_name,
            field_value=field_value,
            error_code="INVALID_ENUM_VALUE",
            context={"valid_values": valid_values}
        )


class ConfigurationError(ScorpiusError):
    """Exception pour erreurs de configuration système.
    
    Cette classe gère les erreurs liées à la configuration de l'application,
    variables d'environnement, fichiers de config, etc.
    
    Attributes:
        config_key: Clé de configuration en erreur
        config_value: Valeur de configuration problématique
        config_source: Source de la configuration (env, file, etc.)
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[str] = None,
        config_source: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialise l'exception de configuration.
        
        Args:
            message: Message d'erreur descriptif
            config_key: Clé de configuration concernée
            config_value: Valeur problématique (masquée si sensible)
            config_source: Source de la configuration
            **kwargs: Arguments additionnels pour ScorpiusError
        """
        super().__init__(
            message,
            error_code=kwargs.pop("error_code", "CONFIGURATION_ERROR"),
            **kwargs
        )
        self.config_key = config_key
        self.config_value = config_value
        self.config_source = config_source
        
        # Enrichissement du contexte (avec masquage des valeurs sensibles)
        self.context.update({
            "config_key": self.config_key,
            "config_value": self._mask_sensitive_value(config_value),
            "config_source": self.config_source
        })
    
    def _mask_sensitive_value(self, value: Optional[str]) -> Optional[str]:
        """Masque les valeurs sensibles pour le logging.
        
        Args:
            value: Valeur à potentiellement masquer
            
        Returns:
            Valeur masquée si sensible, originale sinon
        """
        if not value or not self.config_key:
            return value
        
        sensitive_keys = ["api_key", "secret", "password", "token", "key"]
        if any(sensitive in self.config_key.lower() for sensitive in sensitive_keys):
            if len(value) > 8:
                return f"{value[:4]}...{value[-4:]}"
            else:
                return "***"
        
        return value
    
    @classmethod
    def missing_env_var(cls, var_name: str) -> "ConfigurationError":
        """Erreur de variable d'environnement manquante.
        
        Args:
            var_name: Nom de la variable manquante
            
        Returns:
            Instance ConfigurationError appropriée
        """
        return cls(
            message=f"Variable d'environnement manquante: {var_name}",
            config_key=var_name,
            config_source="environment",
            error_code="MISSING_ENV_VAR"
        )
    
    @classmethod
    def invalid_config_value(
        cls,
        config_key: str,
        config_value: str,
        expected_format: str,
        config_source: str = "unknown"
    ) -> "ConfigurationError":
        """Erreur de valeur de configuration invalide.
        
        Args:
            config_key: Clé de configuration
            config_value: Valeur invalide
            expected_format: Format attendu
            config_source: Source de la configuration
            
        Returns:
            Instance ConfigurationError appropriée
        """
        return cls(
            message=f"Valeur de configuration invalide pour {config_key}: {expected_format}",
            config_key=config_key,
            config_value=config_value,
            config_source=config_source,
            error_code="INVALID_CONFIG_VALUE",
            context={"expected_format": expected_format}
        )
    
    @classmethod
    def config_file_not_found(cls, file_path: str) -> "ConfigurationError":
        """Erreur de fichier de configuration introuvable.
        
        Args:
            file_path: Chemin du fichier manquant
            
        Returns:
            Instance ConfigurationError appropriée
        """
        return cls(
            message=f"Fichier de configuration introuvable: {file_path}",
            config_source="file",
            error_code="CONFIG_FILE_NOT_FOUND",
            context={"file_path": file_path}
        )
    
    @property
    def is_authentication_config(self) -> bool:
        """Indique si l'erreur concerne une configuration d'authentification.
        
        Returns:
            True si lié à l'authentification
        """
        if not self.config_key:
            return False
        
        auth_keys = ["api_key", "secret", "token", "password", "auth"]
        return any(key in self.config_key.lower() for key in auth_keys)