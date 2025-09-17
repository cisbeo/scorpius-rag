"""Cache persistant pour les embeddings avec optimisation coûts."""

import os
import pickle
import hashlib
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import structlog

from ..exceptions import CacheError


class EmbeddingCache:
    """Cache persistant et optimisé pour les embeddings OpenAI.
    
    Cette classe implémente un système de cache intelligent pour économiser
    les coûts d'API d'embedding en évitant les calculs redondants.
    
    Features:
    - Cache persistant sur disque avec compression
    - Expiration automatique basée sur TTL
    - Validation d'intégrité des données
    - Métriques de performance (hit rate, économies)
    - Nettoyage automatique des entrées expirées
    - Gestion robuste des erreurs avec fallback
    
    Attributes:
        cache_dir: Répertoire de stockage du cache
        ttl_hours: Durée de vie des entrées en heures
        max_cache_size_mb: Taille maximale du cache en MB
        compression_enabled: Activation de la compression pickle
        
    Examples:
        >>> cache = EmbeddingCache(
        ...     cache_dir="./cache/embeddings",
        ...     ttl_hours=24,
        ...     max_cache_size_mb=100
        ... )
        >>> # Tentative de récupération
        >>> embedding = cache.get("text example", "text-embedding-3-large")
        >>> if embedding is None:
        ...     # Calcul et mise en cache
        ...     embedding = openai_client.embed("text example")
        ...     cache.set("text example", "text-embedding-3-large", embedding)
        >>> cache.get_stats()
        {'hit_rate': 0.75, 'total_requests': 1000, 'cache_hits': 750, ...}
    """
    
    def __init__(
        self,
        cache_dir: str = "./cache/embeddings",
        ttl_hours: int = 24,
        max_cache_size_mb: int = 500,
        compression_enabled: bool = True
    ) -> None:
        """Initialise le cache avec configuration personnalisée.
        
        Args:
            cache_dir: Répertoire de stockage du cache
            ttl_hours: Durée de vie des entrées (heures)
            max_cache_size_mb: Taille maximale du cache (MB)
            compression_enabled: Activation compression pickle
            
        Raises:
            CacheError: Si le répertoire n'est pas accessible
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_hours = ttl_hours
        self.max_cache_size_mb = max_cache_size_mb
        self.compression_enabled = compression_enabled
        self.logger = structlog.get_logger(self.__class__.__name__)
        
        # Métriques de performance
        self._stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_errors": 0,
            "total_savings_usd": 0.0,
            "cache_size_mb": 0.0
        }
        
        # Création du répertoire de cache
        self._initialize_cache_directory()
        
        # Nettoyage initial des entrées expirées
        self._cleanup_expired_entries()
        
        self.logger.info(
            "embedding_cache_initialized",
            cache_dir=str(self.cache_dir),
            ttl_hours=self.ttl_hours,
            max_size_mb=self.max_cache_size_mb,
            compression=self.compression_enabled
        )
    
    def _initialize_cache_directory(self) -> None:
        """Initialise le répertoire de cache avec permissions appropriées."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Test d'écriture pour vérifier les permissions
            test_file = self.cache_dir / ".cache_test"
            test_file.write_text("test")
            test_file.unlink()
            
        except (OSError, PermissionError) as e:
            raise CacheError.directory_not_accessible(
                str(self.cache_dir), 
                str(e)
            )
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """Génère une clé de cache unique et sécurisée.
        
        Args:
            text: Texte à encoder
            model: Modèle d'embedding utilisé
            
        Returns:
            Clé de cache hexadécimale unique
        """
        # Normalisation du texte (suppression espaces superflus)
        normalized_text = " ".join(text.split())
        
        # Combinaison texte + modèle pour unicité
        content = f"{normalized_text}|{model}"
        
        # Hash SHA-256 pour éviter les collisions
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Retourne le chemin du fichier cache pour une clé.
        
        Args:
            cache_key: Clé de cache
            
        Returns:
            Chemin du fichier cache
        """
        # Sous-répertoires pour éviter trop de fichiers par dossier
        subdir = cache_key[:2]
        return self.cache_dir / subdir / f"{cache_key}.pkl"
    
    def _is_cache_entry_valid(self, file_path: Path) -> bool:
        """Vérifie si une entrée de cache est encore valide (non expirée).
        
        Args:
            file_path: Chemin du fichier cache
            
        Returns:
            True si l'entrée est valide, False sinon
        """
        try:
            # Vérification de l'existence
            if not file_path.exists():
                return False
            
            # Vérification de l'âge du fichier
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            expiry_time = file_time + timedelta(hours=self.ttl_hours)
            
            return datetime.now() < expiry_time
            
        except (OSError, ValueError):
            return False
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Récupère l'embedding depuis le cache.
        
        Args:
            text: Texte dont on veut l'embedding
            model: Modèle d'embedding utilisé
            
        Returns:
            Liste des valeurs d'embedding ou None si absent/expiré
            
        Examples:
            >>> cache = EmbeddingCache()
            >>> embedding = cache.get("Hello world", "text-embedding-3-large")
            >>> if embedding:
            ...     print(f"Cache hit! Dimension: {len(embedding)}")
            ... else:
            ...     print("Cache miss - calcul nécessaire")
        """
        self._stats["total_requests"] += 1
        
        try:
            cache_key = self._get_cache_key(text, model)
            file_path = self._get_cache_file_path(cache_key)
            
            # Vérification validité
            if not self._is_cache_entry_valid(file_path):
                self._stats["cache_misses"] += 1
                return None
            
            # Lecture du cache
            with open(file_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Validation de l'intégrité
            if not self._validate_cache_data(cache_data, text, model):
                self.logger.warning(
                    "cache_data_invalid",
                    cache_key=cache_key,
                    text_length=len(text),
                    model=model
                )
                file_path.unlink(missing_ok=True)
                self._stats["cache_misses"] += 1
                return None
            
            # Success: cache hit
            embedding = cache_data["embedding"]
            self._stats["cache_hits"] += 1
            
            # Calcul économies (approximatif)
            token_estimate = len(text.split()) * 1.3  # Estimation conservative
            cost_saved = (token_estimate / 1000) * 0.00013  # text-embedding-3-large
            self._stats["total_savings_usd"] += cost_saved
            
            self.logger.debug(
                "cache_hit",
                cache_key=cache_key,
                text_length=len(text),
                model=model,
                embedding_dimension=len(embedding),
                cost_saved_usd=cost_saved
            )
            
            return embedding
            
        except Exception as e:
            self._stats["cache_errors"] += 1
            self.logger.error(
                "cache_read_error",
                text_length=len(text),
                model=model,
                error=str(e),
                error_type=type(e).__name__
            )
            # En cas d'erreur, on continue sans cache (graceful degradation)
            return None
    
    def set(self, text: str, model: str, embedding: List[float]) -> None:
        """Sauvegarde l'embedding en cache.
        
        Args:
            text: Texte source
            model: Modèle d'embedding utilisé
            embedding: Vecteur d'embedding à cacher
            
        Raises:
            CacheError: En cas d'erreur de sauvegarde critique
            
        Examples:
            >>> cache = EmbeddingCache()
            >>> embedding = [0.1, 0.2, 0.3, ...]  # Résultat OpenAI
            >>> cache.set("Hello world", "text-embedding-3-large", embedding)
        """
        try:
            cache_key = self._get_cache_key(text, model)
            file_path = self._get_cache_file_path(cache_key)
            
            # Création du sous-répertoire si nécessaire
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Vérification de la taille limite
            embedding_size = len(pickle.dumps(embedding))
            if embedding_size > 10 * 1024 * 1024:  # 10MB limite par embedding
                raise CacheError.size_limit_exceeded(
                    cache_key, 
                    embedding_size, 
                    10 * 1024 * 1024
                )
            
            # Préparation des données à cacher
            cache_data = {
                "text": text,
                "model": model,
                "embedding": embedding,
                "cached_at": datetime.now().isoformat(),
                "text_hash": hashlib.md5(text.encode()).hexdigest(),
                "embedding_dimension": len(embedding)
            }
            
            # Sauvegarde avec compression si activée
            protocol = pickle.HIGHEST_PROTOCOL if self.compression_enabled else pickle.DEFAULT_PROTOCOL
            with open(file_path, 'wb') as f:
                pickle.dump(cache_data, f, protocol=protocol)
            
            self.logger.debug(
                "cache_write_success",
                cache_key=cache_key,
                text_length=len(text),
                model=model,
                embedding_dimension=len(embedding),
                file_size_bytes=file_path.stat().st_size
            )
            
            # Nettoyage si nécessaire
            self._cleanup_if_needed()
            
        except Exception as e:
            self._stats["cache_errors"] += 1
            
            # Log mais ne pas faire échouer l'opération principale
            self.logger.error(
                "cache_write_error",
                text_length=len(text),
                model=model,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Pour les erreurs critiques, on propage
            if isinstance(e, CacheError):
                raise
    
    def _validate_cache_data(
        self, 
        cache_data: Dict[str, Any], 
        text: str, 
        model: str
    ) -> bool:
        """Valide l'intégrité des données du cache.
        
        Args:
            cache_data: Données lues du cache
            text: Texte original
            model: Modèle attendu
            
        Returns:
            True si les données sont valides
        """
        try:
            # Vérification structure
            required_keys = ["text", "model", "embedding", "text_hash"]
            if not all(key in cache_data for key in required_keys):
                return False
            
            # Vérification modèle
            if cache_data["model"] != model:
                return False
            
            # Vérification hash du texte
            expected_hash = hashlib.md5(text.encode()).hexdigest()
            if cache_data["text_hash"] != expected_hash:
                return False
            
            # Vérification format embedding
            embedding = cache_data["embedding"]
            if not isinstance(embedding, list) or not embedding:
                return False
            
            if not all(isinstance(x, (int, float)) for x in embedding):
                return False
            
            return True
            
        except (KeyError, TypeError, AttributeError):
            return False
    
    def _cleanup_expired_entries(self) -> None:
        """Nettoie les entrées de cache expirées."""
        try:
            cleaned_count = 0
            cleaned_size = 0
            
            for cache_file in self.cache_dir.rglob("*.pkl"):
                if not self._is_cache_entry_valid(cache_file):
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    cleaned_count += 1
                    cleaned_size += file_size
            
            if cleaned_count > 0:
                self.logger.info(
                    "cache_cleanup_completed",
                    cleaned_files=cleaned_count,
                    cleaned_size_mb=cleaned_size / 1024 / 1024
                )
                
        except Exception as e:
            self.logger.error(
                "cache_cleanup_error",
                error=str(e),
                error_type=type(e).__name__
            )
    
    def _cleanup_if_needed(self) -> None:
        """Nettoie le cache si la taille dépasse la limite."""
        try:
            current_size = self._get_cache_size_mb()
            self._stats["cache_size_mb"] = current_size
            
            if current_size > self.max_cache_size_mb:
                self.logger.info(
                    "cache_size_exceeded",
                    current_size_mb=current_size,
                    max_size_mb=self.max_cache_size_mb
                )
                
                # Nettoyage des anciennes entrées en premier
                self._cleanup_oldest_entries(target_size_mb=self.max_cache_size_mb * 0.8)
                
        except Exception as e:
            self.logger.error(
                "cache_size_cleanup_error",
                error=str(e)
            )
    
    def _get_cache_size_mb(self) -> float:
        """Calcule la taille totale du cache en MB."""
        total_size = 0
        for cache_file in self.cache_dir.rglob("*.pkl"):
            try:
                total_size += cache_file.stat().st_size
            except OSError:
                continue
        return total_size / 1024 / 1024
    
    def _cleanup_oldest_entries(self, target_size_mb: float) -> None:
        """Supprime les entrées les plus anciennes pour atteindre la taille cible."""
        cache_files = []
        
        # Collecte des fichiers avec leur âge
        for cache_file in self.cache_dir.rglob("*.pkl"):
            try:
                stat = cache_file.stat()
                cache_files.append((cache_file, stat.st_mtime, stat.st_size))
            except OSError:
                continue
        
        # Tri par âge (plus ancien en premier)
        cache_files.sort(key=lambda x: x[1])
        
        current_size = sum(f[2] for f in cache_files) / 1024 / 1024
        cleaned_count = 0
        
        for cache_file, _, file_size in cache_files:
            if current_size <= target_size_mb:
                break
                
            try:
                cache_file.unlink()
                current_size -= file_size / 1024 / 1024
                cleaned_count += 1
            except OSError:
                continue
        
        if cleaned_count > 0:
            self.logger.info(
                "cache_oldest_cleanup",
                cleaned_files=cleaned_count,
                final_size_mb=current_size
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de performance du cache.
        
        Returns:
            Dictionnaire avec métriques de performance
            
        Examples:
            >>> cache = EmbeddingCache()
            >>> stats = cache.get_stats()
            >>> print(f"Hit rate: {stats['hit_rate']:.2%}")
            >>> print(f"Économies: ${stats['total_savings_usd']:.2f}")
        """
        total_requests = self._stats["total_requests"]
        hit_rate = (
            self._stats["cache_hits"] / total_requests 
            if total_requests > 0 else 0.0
        )
        
        return {
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"],
            "cache_errors": self._stats["cache_errors"],
            "total_savings_usd": self._stats["total_savings_usd"],
            "cache_size_mb": self._get_cache_size_mb(),
            "cache_directory": str(self.cache_dir),
            "ttl_hours": self.ttl_hours,
            "max_size_mb": self.max_cache_size_mb
        }
    
    def clear_cache(self) -> Dict[str, int]:
        """Vide complètement le cache.
        
        Returns:
            Statistiques de nettoyage
            
        Examples:
            >>> cache = EmbeddingCache()
            >>> result = cache.clear_cache()
            >>> print(f"Supprimé {result['files_deleted']} fichiers")
        """
        deleted_files = 0
        deleted_size = 0
        
        try:
            for cache_file in self.cache_dir.rglob("*.pkl"):
                try:
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    deleted_files += 1
                    deleted_size += file_size
                except OSError:
                    continue
            
            # Reset des stats
            self._stats = {
                "total_requests": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "cache_errors": 0,
                "total_savings_usd": 0.0,
                "cache_size_mb": 0.0
            }
            
            self.logger.info(
                "cache_cleared",
                files_deleted=deleted_files,
                size_deleted_mb=deleted_size / 1024 / 1024
            )
            
            return {
                "files_deleted": deleted_files,
                "size_deleted_mb": deleted_size / 1024 / 1024
            }
            
        except Exception as e:
            self.logger.error(
                "cache_clear_error",
                error=str(e)
            )
            raise CacheError(
                f"Erreur lors du nettoyage du cache: {e}",
                error_code="CACHE_CLEAR_FAILED"
            )