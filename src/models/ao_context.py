"""Modèle de contexte d'appel d'offres pour optimisation recherche RAG."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class AOType(Enum):
    """Types d'appels d'offres publics français."""
    MAPA = "MAPA"  # Marché à Procédure Adaptée
    OUVERT = "Ouvert"
    RESTREINT = "Restreint"
    DIALOGUE_COMPETITIF = "Dialogue compétitif"
    PARTENARIAT_INNOVATION = "Partenariat d'innovation"
    CONCOURS = "Concours"


class Sector(Enum):
    """Secteurs publics français."""
    ETAT = "État"
    TERRITORIAL = "Territorial"
    HOSPITALIER = "Hospitalier"
    EDUCATION = "Éducation"
    EPA_EPIC = "EPA/EPIC"
    DEFENSE = "Défense"


class TechnicalDomain(Enum):
    """Domaines techniques pour l'IT public."""
    DEVELOPPEMENT = "Développement"
    INFRA_CLOUD = "Infrastructure/Cloud"
    CYBERSECURITE = "Cybersécurité"
    DATA_IA = "Data/IA"
    CONSEIL = "Conseil"
    INTEGRATION = "Intégration"
    SUPPORT = "Support/Maintenance"


@dataclass
class AOContext:
    """Contexte d'appel d'offres pour optimisation recherche RAG.
    
    Cette classe encapsule toutes les informations contextuelles d'un AO
    pour permettre des recherches vectorielles plus précises et des
    recommandations adaptées au contexte spécifique des marchés publics français.
    
    Attributes:
        ao_type: Type de procédure d'AO
        sector: Secteur public concerné
        estimated_amount: Montant estimé en euros
        technical_domains: Domaines techniques impliqués
        organisme: Organisme acheteur
        geographic_scope: Périmètre géographique (région, département, etc.)
        deadline: Date limite de remise des offres
        criteria_weights: Pondération des critères (prix, technique, etc.)
        mandatory_certifications: Certifications obligatoires
        incumbent_info: Informations sur le titulaire actuel si reconduction
        competition_level: Niveau de concurrence estimé (Faible/Moyen/Fort)
        strategic_importance: Importance stratégique pour l'organisme
        
    Examples:
        >>> context = AOContext(
        ...     ao_type=AOType.OUVERT,
        ...     sector=Sector.TERRITORIAL,
        ...     estimated_amount=500000,
        ...     technical_domains=[TechnicalDomain.DEVELOPPEMENT, TechnicalDomain.INFRA_CLOUD],
        ...     organisme="Métropole de Lyon",
        ...     geographic_scope="Rhône-Alpes",
        ...     criteria_weights={"technique": 60, "prix": 40},
        ...     competition_level="Fort"
        ... )
        >>> print(f"AO {context.ao_type.value} - {context.get_amount_range()}")
        AO Ouvert - 500k-1M
    """
    ao_type: AOType
    sector: Sector
    estimated_amount: Optional[int] = None
    technical_domains: Optional[List[TechnicalDomain]] = None
    organisme: Optional[str] = None
    geographic_scope: Optional[str] = None
    deadline: Optional[datetime] = None
    criteria_weights: Optional[Dict[str, int]] = None
    mandatory_certifications: Optional[List[str]] = None
    incumbent_info: Optional[str] = None
    competition_level: Optional[str] = None
    strategic_importance: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validation et initialisation des valeurs par défaut."""
        if self.technical_domains is None:
            self.technical_domains = []
        
        if self.criteria_weights is None:
            self.criteria_weights = {}
        
        if self.mandatory_certifications is None:
            self.mandatory_certifications = []
        
        # Validation pondération critères
        if self.criteria_weights:
            total_weight = sum(self.criteria_weights.values())
            if total_weight > 100:
                raise ValueError(f"Pondération totale ne peut excéder 100%, reçu: {total_weight}%")
    
    def get_amount_range(self) -> str:
        """Détermine la fourchette de montant pour le benchmarking.
        
        Returns:
            Fourchette sous forme de string (ex: "100k-500k")
        """
        if self.estimated_amount is None:
            return "Non spécifié"
        
        amount = self.estimated_amount
        if amount < 25000:
            return "0-25k"
        elif amount < 100000:
            return "25k-100k"
        elif amount < 500000:
            return "100k-500k"
        elif amount < 1000000:
            return "500k-1M"
        elif amount < 5000000:
            return "1M-5M"
        else:
            return "5M+"
    
    def get_formalism_level(self) -> str:
        """Détermine le niveau de formalisme requis selon type AO et montant.
        
        Returns:
            "Minimum", "Standard" ou "Maximum"
        """
        if self.ao_type == AOType.MAPA:
            return "Minimum"
        elif self.ao_type in [AOType.OUVERT, AOType.RESTREINT]:
            if self.estimated_amount and self.estimated_amount > 1000000:
                return "Maximum"
            else:
                return "Standard"
        else:
            return "Maximum"
    
    def get_price_sensitivity(self) -> float:
        """Calcule la sensibilité au prix basée sur la pondération.
        
        Returns:
            Score de sensibilité prix [0.0, 1.0]
        """
        if not self.criteria_weights:
            return 0.5  # Valeur par défaut
        
        price_weight = self.criteria_weights.get("prix", 50)
        return price_weight / 100.0
    
    def get_technical_complexity(self) -> str:
        """Évalue la complexité technique basée sur les domaines impliqués.
        
        Returns:
            "Faible", "Moyenne" ou "Élevée"
        """
        if not self.technical_domains:
            return "Faible"
        
        nb_domains = len(self.technical_domains)
        complex_domains = [
            TechnicalDomain.CYBERSECURITE,
            TechnicalDomain.DATA_IA,
            TechnicalDomain.INTEGRATION
        ]
        
        has_complex = any(domain in complex_domains for domain in self.technical_domains)
        
        if nb_domains >= 3 or has_complex:
            return "Élevée"
        elif nb_domains == 2:
            return "Moyenne"
        else:
            return "Faible"
    
    def get_search_keywords(self) -> List[str]:
        """Génère des mots-clés pour optimiser la recherche vectorielle.
        
        Returns:
            Liste de mots-clés pertinents pour la recherche
        """
        keywords = []
        
        # Type AO et secteur
        keywords.extend([self.ao_type.value, self.sector.value])
        
        # Domaines techniques
        if self.technical_domains:
            keywords.extend([domain.value for domain in self.technical_domains])
        
        # Fourchette montant
        keywords.append(self.get_amount_range())
        
        # Organisme si spécifié
        if self.organisme:
            keywords.append(self.organisme)
        
        # Scope géographique
        if self.geographic_scope:
            keywords.append(self.geographic_scope)
        
        return keywords
    
    def to_search_context(self) -> str:
        """Convertit le contexte en string optimisée pour la recherche vectorielle.
        
        Returns:
            Contexte formaté pour améliorer la pertinence des embeddings
        """
        context_parts = []
        
        context_parts.append(f"Appel d'offres {self.ao_type.value} secteur {self.sector.value}")
        
        if self.estimated_amount:
            context_parts.append(f"montant {self.get_amount_range()}")
        
        if self.technical_domains:
            domains = ", ".join([d.value for d in self.technical_domains])
            context_parts.append(f"domaines techniques: {domains}")
        
        if self.organisme:
            context_parts.append(f"organisme: {self.organisme}")
        
        if self.geographic_scope:
            context_parts.append(f"périmètre: {self.geographic_scope}")
        
        return " - ".join(context_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour sérialisation.
        
        Returns:
            Dictionnaire avec tous les attributs sérialisables
        """
        return {
            "ao_type": self.ao_type.value,
            "sector": self.sector.value,
            "estimated_amount": self.estimated_amount,
            "technical_domains": [d.value for d in self.technical_domains] if self.technical_domains else [],
            "organisme": self.organisme,
            "geographic_scope": self.geographic_scope,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "criteria_weights": self.criteria_weights,
            "mandatory_certifications": self.mandatory_certifications,
            "incumbent_info": self.incumbent_info,
            "competition_level": self.competition_level,
            "strategic_importance": self.strategic_importance,
            "amount_range": self.get_amount_range(),
            "formalism_level": self.get_formalism_level(),
            "price_sensitivity": self.get_price_sensitivity(),
            "technical_complexity": self.get_technical_complexity()
        }