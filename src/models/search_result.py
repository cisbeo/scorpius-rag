"""Modèle de résultat de recherche RAG pour appels d'offres publics."""

from dataclasses import dataclass
from typing import Dict, Union, Optional
from datetime import datetime


@dataclass
class SearchResult:
    """Résultat de recherche RAG avec métadonnées spécifiques aux AO publics.
    
    Cette classe encapsule un résultat de recherche vectorielle avec toutes
    les métadonnées nécessaires pour l'analyse d'appels d'offres publics français.
    
    Attributes:
        content: Contenu textuel du document trouvé
        metadata: Métadonnées enrichies (secteur, montant, procédure, etc.)
        similarity_score: Score de similarité vectorielle [0.0, 1.0]
        collection: Collection ChromaDB source du résultat
        ao_type: Type d'appel d'offres (MAPA, Ouvert, Restreint, etc.)
        sector: Secteur public (État, Territorial, Hospitalier, etc.)
        amount_range: Fourchette de montant pour benchmarking
        relevance_score: Score de pertinence contextuelle [0.0, 1.0]
        
    Examples:
        >>> result = SearchResult(
        ...     content="Développement plateforme e-services citoyens...",
        ...     metadata={
        ...         "source": "BOAMP",
        ...         "date_publication": "2024-01-15",
        ...         "organisme": "Région Nouvelle-Aquitaine",
        ...         "montant": 250000
        ...     },
        ...     similarity_score=0.85,
        ...     collection="historique_ao",
        ...     ao_type="Ouvert",
        ...     sector="Territorial",
        ...     amount_range="100k-500k",
        ...     relevance_score=0.92
        ... )
        >>> print(f"AO {result.ao_type} - Score: {result.similarity_score:.2f}")
        AO Ouvert - Score: 0.85
    """
    content: str
    metadata: Dict[str, Union[str, int, float, datetime]]
    similarity_score: float
    collection: str
    ao_type: Optional[str] = None
    sector: Optional[str] = None
    amount_range: Optional[str] = None
    relevance_score: Optional[float] = None
    
    def __post_init__(self) -> None:
        """Validation des données après initialisation.
        
        Raises:
            ValueError: Si les scores ne sont pas dans [0.0, 1.0]
        """
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(
                f"similarity_score doit être entre 0.0 et 1.0, reçu: {self.similarity_score}"
            )
        
        if self.relevance_score is not None and not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError(
                f"relevance_score doit être entre 0.0 et 1.0, reçu: {self.relevance_score}"
            )
    
    @property
    def is_highly_relevant(self) -> bool:
        """Indique si le résultat est hautement pertinent (score > 0.8).
        
        Returns:
            True si similarity_score > 0.8, False sinon
        """
        return self.similarity_score > 0.8
    
    @property
    def confidence_level(self) -> str:
        """Niveau de confiance basé sur le score de similarité.
        
        Returns:
            "Haute", "Moyenne" ou "Faible" selon le score
        """
        if self.similarity_score > 0.8:
            return "Haute"
        elif self.similarity_score > 0.6:
            return "Moyenne"
        else:
            return "Faible"
    
    def get_display_summary(self, max_content_length: int = 200) -> str:
        """Résumé formaté pour affichage utilisateur.
        
        Args:
            max_content_length: Longueur maximale du contenu affiché
            
        Returns:
            Résumé formaté avec métadonnées principales
        """
        content_preview = (
            self.content[:max_content_length] + "..."
            if len(self.content) > max_content_length
            else self.content
        )
        
        organisme = self.metadata.get("organisme", "Non spécifié")
        montant = self.metadata.get("montant", "Non spécifié")
        
        return (
            f"[{self.confidence_level}] {self.ao_type or 'AO'} - {organisme}\n"
            f"Montant: {montant} € | Score: {self.similarity_score:.2f}\n"
            f"Extrait: {content_preview}"
        )
    
    def to_dict(self) -> Dict[str, Union[str, int, float, None]]:
        """Conversion en dictionnaire pour sérialisation.
        
        Returns:
            Dictionnaire avec tous les attributs
        """
        return {
            "content": self.content,
            "metadata": self.metadata,
            "similarity_score": self.similarity_score,
            "collection": self.collection,
            "ao_type": self.ao_type,
            "sector": self.sector,
            "amount_range": self.amount_range,
            "relevance_score": self.relevance_score,
            "confidence_level": self.confidence_level,
            "is_highly_relevant": self.is_highly_relevant
        }