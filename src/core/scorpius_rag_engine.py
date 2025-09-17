"""Moteur RAG principal de Scorpius pour analyse d'appels d'offres publics français."""

import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import structlog

import chromadb
from chromadb.config import Settings

from ..models import SearchResult, AOContext, EmbeddingConfig
from ..services import OpenAIEmbeddingService
from ..utils import Config, setup_logger, PerformanceMetrics
from ..exceptions import (
    ScorpiusError, ChromaDBError, OpenAIError, 
    ValidationError, ConfigurationError
)


class ScorpiusRAGEngine:
    """Moteur RAG spécialisé pour l'analyse d'appels d'offres publics français.
    
    Cette classe orchestre l'ensemble du pipeline RAG optimisé pour le domaine
    des marchés publics français:
    
    - Embedding intelligent avec cache automatique
    - Recherche vectorielle contextuelle par secteur/type AO
    - Enrichissement métadonnées spécifiques (montant, procédure, organisme)
    - Collections thématiques (réglementaire, historique, templates, concurrence)
    - Scoring de pertinence adapté au contexte AO
    - Métriques de performance et coûts en temps réel
    
    Architecture:
    - ChromaDB: Base vectorielle persistante avec métadonnées enrichies
    - OpenAI: Service d'embeddings avec rate limiting et cache
    - Configuration: Variables d'environnement avec validation
    - Logging: Structuré avec métriques business et techniques
    
    Collections RAG par défaut:
    - "reglementaire": Code marchés publics, CCAG, jurisprudences
    - "historique_ao": Résultats BOAMP/TED, analyses post-attribution  
    - "references_clients": Projets détaillés, ROI, retours satisfaction
    - "templates_performants": Mémoires gagnants, structures optimales
    - "intelligence_concurrentielle": Profils ESN, stratégies, grilles prix
    
    Examples:
        >>> # Initialisation avec configuration auto
        >>> engine = await ScorpiusRAGEngine.create_from_env()
        >>> 
        >>> # Recherche contextuelle pour AO territorial
        >>> context = AOContext(
        ...     ao_type=AOType.OUVERT,
        ...     sector=Sector.TERRITORIAL,
        ...     estimated_amount=500000,
        ...     technical_domains=[TechnicalDomain.DEVELOPPEMENT]
        ... )
        >>> results = await engine.search(
        ...     "plateforme e-services citoyens digitalisation", 
        ...     context=context,
        ...     limit=5
        ... )
        >>> 
        >>> # Ajout de documents avec métadonnées enrichies
        >>> await engine.add_documents(
        ...     collection="historique_ao",
        ...     documents=["AO région plateforme..."],
        ...     metadatas=[{
        ...         "organisme": "Région Nouvelle-Aquitaine",
        ...         "montant": 750000,
        ...         "secteur": "Territorial",
        ...         "date_attribution": "2024-01-15"
        ...     }]
        ... )
        >>> 
        >>> # Métriques de performance
        >>> stats = engine.get_performance_stats()
        >>> print(f"Hit rate cache: {stats['cache_hit_rate']:.2%}")
        >>> print(f"Coût total: ${stats['total_cost_usd']:.3f}")
    """
    
    DEFAULT_COLLECTIONS = {
        "reglementaire": {
            "description": "Code des marchés publics, CCAG, jurisprudences, normes sectorielles",
            "embedding_function": None  # Utilise la fonction par défaut
        },
        "historique_ao": {
            "description": "Résultats BOAMP/TED, analyses post-attribution, patterns sectoriels",
            "embedding_function": None
        },
        "references_clients": {
            "description": "Projets détaillés, ROI quantifiés, retours satisfaction",
            "embedding_function": None
        },
        "templates_performants": {
            "description": "Mémoires techniques gagnants, structures optimales par secteur",
            "embedding_function": None
        },
        "intelligence_concurrentielle": {
            "description": "Profils détaillés ESN/consultants, stratégies, grilles prix",
            "embedding_function": None
        }
    }
    
    def __init__(
        self,
        config: Config,
        embedding_service: OpenAIEmbeddingService,
        chroma_client: chromadb.ClientAPI
    ) -> None:
        """Initialise le moteur RAG avec services configurés.
        
        Args:
            config: Configuration système validée
            embedding_service: Service d'embeddings OpenAI configuré
            chroma_client: Client ChromaDB connecté
            
        Note:
            Utilisez plutôt ScorpiusRAGEngine.create_from_env() pour
            l'initialisation automatique depuis les variables d'environnement.
        """
        self.config = config
        self.embedding_service = embedding_service
        self.chroma_client = chroma_client
        
        # Logging spécialisé
        self.logger = structlog.get_logger(self.__class__.__name__)
        self.perf_logger = structlog.get_logger("performance")
        self.business_logger = structlog.get_logger("business")
        
        # Collections ChromaDB (lazy loading)
        self._collections: Dict[str, chromadb.Collection] = {}
        
        # Métriques de performance
        self._stats = {
            "total_searches": 0,
            "total_documents_added": 0,
            "total_embeddings_generated": 0,
            "cache_hit_rate": 0.0,
            "avg_search_time_ms": 0.0,
            "total_cost_usd": 0.0,
            "collections_created": 0
        }
        
        self.logger.info(
            "scorpius_rag_engine_initialized",
            embedding_model=config.openai_model,
            chroma_host=config.chroma_host,
            cache_enabled=config.cache_enabled,
            default_collections=list(self.DEFAULT_COLLECTIONS.keys())
        )
    
    @classmethod
    async def create_from_env(cls) -> "ScorpiusRAGEngine":
        """Factory method pour créer le moteur depuis les variables d'environnement.
        
        Cette méthode est le point d'entrée recommandé pour initialiser
        Scorpius RAG avec configuration automatique et validation complète.
        
        Returns:
            Instance ScorpiusRAGEngine prête à l'emploi
            
        Raises:
            ConfigurationError: Si configuration invalide ou incomplète
            ChromaDBError: Si impossible de se connecter à ChromaDB
            OpenAIError: Si authentification OpenAI échoue
            
        Examples:
            >>> engine = await ScorpiusRAGEngine.create_from_env()
            >>> # Engine prêt avec toutes collections initialisées
        """
        # Chargement et validation configuration
        config = Config.from_env()
        config.validate()
        
        # Setup logging global
        setup_logger(
            log_level=config.log_level,
            environment=config.environment,
            additional_context={"component": "scorpius-rag-engine"}
        )
        
        logger = structlog.get_logger("ScorpiusRAGEngine.Factory")
        
        try:
            # Initialisation service d'embedding
            embedding_config = EmbeddingConfig.from_env()
            embedding_service = OpenAIEmbeddingService(
                embedding_config, 
                enable_cache=config.cache_enabled
            )
            
            # Test de connectivité OpenAI
            health_check = await embedding_service.health_check()
            if health_check["status"] != "healthy":
                raise OpenAIError(
                    f"Service OpenAI non disponible: {health_check.get('error')}",
                    error_code="OPENAI_HEALTH_CHECK_FAILED"
                )
            
            logger.info("openai_service_ready", model=embedding_config.model)
            
            # Initialisation ChromaDB
            chroma_settings = Settings(
                chroma_api_impl="chromadb.api.fastapi.FastAPI",
                chroma_server_host=config.chroma_host,
                chroma_server_http_port=config.chroma_port,
                persist_directory=config.chroma_persistent_path
            )
            
            try:
                chroma_client = chromadb.Client(chroma_settings)
                # Test de connectivité
                chroma_client.heartbeat()
                logger.info("chromadb_connected", host=config.chroma_host, port=config.chroma_port)
                
            except Exception as e:
                raise ChromaDBError.connection_failed(config.chroma_host, config.chroma_port)
            
            # Création de l'instance
            engine = cls(config, embedding_service, chroma_client)
            
            # Initialisation des collections par défaut
            await engine._initialize_default_collections()
            
            logger.info(
                "scorpius_rag_engine_created",
                collections_count=len(engine._collections),
                embedding_dimensions=embedding_service.get_embedding_dimension()
            )
            
            return engine
            
        except Exception as e:
            logger.error(
                "engine_creation_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def _initialize_default_collections(self) -> None:
        """Initialise les collections ChromaDB par défaut si nécessaires."""
        for collection_name, collection_info in self.DEFAULT_COLLECTIONS.items():
            try:
                await self._get_or_create_collection(collection_name)
                self.logger.debug(
                    "collection_initialized",
                    collection=collection_name,
                    description=collection_info["description"]
                )
            except Exception as e:
                self.logger.warning(
                    "collection_init_failed",
                    collection=collection_name,
                    error=str(e)
                )
    
    async def _get_or_create_collection(self, collection_name: str) -> chromadb.Collection:
        """Récupère ou crée une collection ChromaDB avec embedding function.
        
        Args:
            collection_name: Nom de la collection
            
        Returns:
            Collection ChromaDB prête à l'emploi
            
        Raises:
            ChromaDBError: Si erreur de création/accès collection
        """
        if collection_name in self._collections:
            return self._collections[collection_name]
        
        try:
            # Tentative de récupération collection existante
            try:
                collection = self.chroma_client.get_collection(
                    name=collection_name,
                    embedding_function=self._create_embedding_function()
                )
                self.logger.debug("collection_retrieved", collection=collection_name)
                
            except ValueError:
                # Collection n'existe pas, création
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    embedding_function=self._create_embedding_function(),
                    metadata={
                        "description": self.DEFAULT_COLLECTIONS.get(collection_name, {}).get("description", ""),
                        "created_at": datetime.utcnow().isoformat(),
                        "scorpius_version": "1.0.0"
                    }
                )
                self._stats["collections_created"] += 1
                self.logger.info("collection_created", collection=collection_name)
            
            self._collections[collection_name] = collection
            return collection
            
        except Exception as e:
            raise ChromaDBError(
                f"Erreur accès collection '{collection_name}': {str(e)}",
                error_code="COLLECTION_ACCESS_FAILED",
                context={"collection_name": collection_name}
            )
    
    def _create_embedding_function(self):
        """Crée une fonction d'embedding compatible ChromaDB."""
        class ScorpiusEmbeddingFunction:
            def __init__(self, embedding_service: OpenAIEmbeddingService):
                self.embedding_service = embedding_service
            
            def __call__(self, input: List[str]) -> List[List[float]]:
                # Note: ChromaDB n'est pas async, on utilise run_until_complete
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si on est déjà dans une boucle async, on crée une nouvelle tâche
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(self.embedding_service.embed_batch(input))
                        )
                        return future.result()
                else:
                    return asyncio.run(self.embedding_service.embed_batch(input))
        
        return ScorpiusEmbeddingFunction(self.embedding_service)
    
    async def search(
        self,
        query: str,
        collection: str = "historique_ao",
        limit: int = 5,
        context: Optional[AOContext] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity_score: float = 0.5
    ) -> List[SearchResult]:
        """Recherche vectorielle contextuelle optimisée pour les AO publics.
        
        Cette méthode effectue une recherche RAG intelligente en:
        1. Enrichissant la requête avec le contexte AO (secteur, montant, etc.)
        2. Appliquant des filtres métadonnées appropriés
        3. Calculant des embeddings avec cache automatique
        4. Effectuant la recherche vectorielle avec scoring contextuel
        5. Post-traitant les résultats avec enrichissement métadonnées
        
        Args:
            query: Requête de recherche (texte libre)
            collection: Collection à interroger
            limit: Nombre maximum de résultats
            context: Contexte AO pour optimiser la recherche
            filters: Filtres métadonnées additionnels
            min_similarity_score: Score minimum de similarité
            
        Returns:
            Liste de résultats ordonnés par pertinence
            
        Raises:
            ValidationError: Si paramètres invalides
            ChromaDBError: Si erreur de recherche vectorielle
            OpenAIError: Si erreur de génération d'embedding
            
        Examples:
            >>> # Recherche basique
            >>> results = await engine.search(
            ...     "développement plateforme e-services",
            ...     collection="historique_ao",
            ...     limit=5
            ... )
            >>> 
            >>> # Recherche contextuelle avec filtres
            >>> context = AOContext(
            ...     ao_type=AOType.OUVERT,
            ...     sector=Sector.TERRITORIAL,
            ...     estimated_amount=500000
            ... )
            >>> results = await engine.search(
            ...     "plateforme digitale citoyens",
            ...     context=context,
            ...     filters={"organisme": {"$like": "%région%"}},
            ...     min_similarity_score=0.7
            ... )
        """
        start_time = datetime.utcnow()
        
        # Validation des paramètres
        if not query or not query.strip():
            raise ValidationError(
                "Requête vide ou invalide",
                field_name="query",
                field_value=query
            )
        
        if limit <= 0 or limit > 100:
            raise ValidationError.value_out_of_range(
                "limit", limit, min_value=1, max_value=100
            )
        
        if not 0.0 <= min_similarity_score <= 1.0:
            raise ValidationError.value_out_of_range(
                "min_similarity_score", min_similarity_score, 
                min_value=0.0, max_value=1.0
            )
        
        try:
            with PerformanceMetrics("rag_search", self.perf_logger) as metrics:
                # Enrichissement requête avec contexte
                enriched_query = self._enrich_query_with_context(query, context)
                metrics.add_metric("original_query_length", len(query))
                metrics.add_metric("enriched_query_length", len(enriched_query))
                
                # Génération embedding avec cache
                query_embedding = await self.embedding_service.embed(
                    enriched_query, 
                    use_cache=True
                )
                metrics.add_metric("embedding_from_cache", True)  # TODO: récupérer vraie info
                
                # Récupération collection
                chroma_collection = await self._get_or_create_collection(collection)
                
                # Construction filtres métadonnées
                combined_filters = self._build_metadata_filters(context, filters)
                metrics.add_metric("filters_applied", len(combined_filters) if combined_filters else 0)
                
                # Recherche vectorielle
                search_results = chroma_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit * 2,  # Sur-échantillonnage pour filtrage post-traitement
                    where=combined_filters,
                    include=["documents", "metadatas", "distances"]
                )
                
                # Post-traitement et enrichissement résultats
                processed_results = self._process_search_results(
                    search_results, 
                    collection,
                    min_similarity_score,
                    context,
                    limit
                )
                
                # Métriques et logging
                search_duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._update_search_stats(search_duration, len(processed_results))
                
                metrics.add_metric("results_found", len(processed_results))
                metrics.add_metric("collection", collection)
                metrics.add_metric("final_score_avg", 
                    sum(r.similarity_score for r in processed_results) / len(processed_results)
                    if processed_results else 0.0
                )
                
                self.business_logger.info(
                    "ao_search_completed",
                    query_hash=hash(query),
                    collection=collection,
                    results_count=len(processed_results),
                    avg_similarity=metrics.metrics.get("final_score_avg", 0.0),
                    context_provided=context is not None,
                    ao_type=context.ao_type.value if context else None,
                    sector=context.sector.value if context else None
                )
                
                return processed_results
                
        except Exception as e:
            self._stats["total_searches"] += 1  # Compter même les échecs
            
            self.logger.error(
                "search_failed",
                query_hash=hash(query),
                collection=collection,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Re-raise avec contexte enrichi si pas déjà une exception Scorpius
            if not isinstance(e, ScorpiusError):
                raise ScorpiusError(
                    f"Erreur lors de la recherche RAG: {str(e)}",
                    error_code="RAG_SEARCH_FAILED",
                    context={
                        "query_length": len(query),
                        "collection": collection,
                        "limit": limit
                    }
                )
            raise
    
    def _enrich_query_with_context(self, query: str, context: Optional[AOContext]) -> str:
        """Enrichit la requête avec le contexte AO pour améliorer la pertinence.
        
        Args:
            query: Requête originale
            context: Contexte AO optionnel
            
        Returns:
            Requête enrichie avec mots-clés contextuels
        """
        if not context:
            return query
        
        # Construction du contexte sémantique
        context_parts = [query]
        
        # Ajout type AO et secteur
        context_parts.append(f"appel offres {context.ao_type.value}")
        context_parts.append(f"secteur {context.sector.value}")
        
        # Ajout fourchette montant
        if context.estimated_amount:
            amount_range = context.get_amount_range()
            context_parts.append(f"montant {amount_range}")
        
        # Ajout domaines techniques
        if context.technical_domains:
            domains = " ".join([d.value for d in context.technical_domains])
            context_parts.append(f"technologies {domains}")
        
        # Ajout organisme si spécifié
        if context.organisme:
            context_parts.append(f"organisme {context.organisme}")
        
        return " - ".join(context_parts)
    
    def _build_metadata_filters(
        self, 
        context: Optional[AOContext], 
        additional_filters: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Construit les filtres métadonnées pour ChromaDB.
        
        Args:
            context: Contexte AO pour filtres automatiques
            additional_filters: Filtres additionnels explicites
            
        Returns:
            Dictionnaire de filtres ChromaDB ou None
        """
        filters = {}
        
        # Filtres depuis contexte AO
        if context:
            if context.sector:
                filters["secteur"] = context.sector.value
            
            if context.ao_type:
                filters["type_ao"] = context.ao_type.value
            
            if context.estimated_amount:
                # Filtre par fourchette de montant
                amount_range = context.get_amount_range()
                filters["fourchette_montant"] = amount_range
            
            if context.technical_domains:
                # Filtre par domaines techniques (OR logic)
                domain_values = [d.value for d in context.technical_domains]
                filters["domaine_technique"] = {"$in": domain_values}
        
        # Ajout filtres additionnels
        if additional_filters:
            filters.update(additional_filters)
        
        return filters if filters else None
    
    def _process_search_results(
        self,
        raw_results: Dict[str, List],
        collection: str,
        min_similarity_score: float,
        context: Optional[AOContext],
        limit: int
    ) -> List[SearchResult]:
        """Post-traite les résultats bruts de ChromaDB en SearchResult enrichis.
        
        Args:
            raw_results: Résultats bruts ChromaDB
            collection: Nom de la collection source
            min_similarity_score: Score minimum requis
            context: Contexte AO pour scoring additionnel
            limit: Nombre maximum de résultats finaux
            
        Returns:
            Liste de SearchResult triés et enrichis
        """
        if not raw_results.get("documents") or not raw_results["documents"][0]:
            return []
        
        processed_results = []
        
        # Traitement de chaque résultat
        for i in range(len(raw_results["documents"][0])):
            document = raw_results["documents"][0][i]
            metadata = raw_results["metadatas"][0][i] or {}
            distance = raw_results["distances"][0][i]
            
            # Conversion distance -> similarité (ChromaDB utilise distance euclidienne)
            similarity_score = max(0.0, 1.0 - distance)
            
            # Filtrage par score minimum
            if similarity_score < min_similarity_score:
                continue
            
            # Calcul score de pertinence contextuelle
            relevance_score = self._calculate_contextual_relevance(
                metadata, context, similarity_score
            )
            
            # Création SearchResult enrichi
            result = SearchResult(
                content=document,
                metadata=metadata,
                similarity_score=similarity_score,
                collection=collection,
                ao_type=metadata.get("type_ao"),
                sector=metadata.get("secteur"),
                amount_range=metadata.get("fourchette_montant"),
                relevance_score=relevance_score
            )
            
            processed_results.append(result)
        
        # Tri par score de pertinence (combinaison similarité + contexte)
        processed_results.sort(
            key=lambda r: (r.relevance_score or r.similarity_score), 
            reverse=True
        )
        
        return processed_results[:limit]
    
    def _calculate_contextual_relevance(
        self,
        metadata: Dict[str, Any],
        context: Optional[AOContext],
        base_similarity: float
    ) -> float:
        """Calcule un score de pertinence contextuelle enrichi.
        
        Args:
            metadata: Métadonnées du document
            context: Contexte AO de la requête
            base_similarity: Score de similarité vectorielle de base
            
        Returns:
            Score de pertinence contextuelle [0.0, 1.0]
        """
        if not context:
            return base_similarity
        
        relevance_bonus = 0.0
        
        # Bonus secteur exact
        if context.sector and metadata.get("secteur") == context.sector.value:
            relevance_bonus += 0.1
        
        # Bonus type AO exact
        if context.ao_type and metadata.get("type_ao") == context.ao_type.value:
            relevance_bonus += 0.1
        
        # Bonus fourchette montant
        if context.estimated_amount and metadata.get("fourchette_montant"):
            context_range = context.get_amount_range()
            if metadata.get("fourchette_montant") == context_range:
                relevance_bonus += 0.08
        
        # Bonus organisme similaire (même type)
        if context.organisme and metadata.get("organisme"):
            context_org = context.organisme.lower()
            meta_org = metadata.get("organisme", "").lower()
            
            # Détection type organisme (région, département, ministère, etc.)
            org_types = ["région", "département", "ministère", "chu", "université"]
            for org_type in org_types:
                if org_type in context_org and org_type in meta_org:
                    relevance_bonus += 0.05
                    break
        
        # Application bonus avec plafond
        final_score = min(1.0, base_similarity + relevance_bonus)
        return final_score
    
    def _update_search_stats(self, duration_ms: float, results_count: int) -> None:
        """Met à jour les statistiques de recherche."""
        self._stats["total_searches"] += 1
        
        # Mise à jour moyenne temps de recherche
        total_searches = self._stats["total_searches"]
        prev_avg = self._stats["avg_search_time_ms"]
        
        self._stats["avg_search_time_ms"] = (
            (prev_avg * (total_searches - 1) + duration_ms) / total_searches
        )
        
        # Récupération stats embedding service
        embedding_stats = self.embedding_service.get_performance_stats()
        self._stats["cache_hit_rate"] = embedding_stats.get("cache_hit_rate", 0.0)
        self._stats["total_cost_usd"] = embedding_stats.get("total_cost_usd", 0.0)
    
    async def add_documents(
        self,
        collection: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Ajoute des documents à une collection avec embeddings automatiques.
        
        Args:
            collection: Nom de la collection cible
            documents: Liste des documents à ajouter
            metadatas: Métadonnées associées (optionnel)
            ids: IDs personnalisés (optionnel, auto-générés sinon)
            
        Returns:
            Statistiques d'ajout (nombre docs, coût, temps)
            
        Raises:
            ValidationError: Si paramètres invalides
            ChromaDBError: Si erreur d'ajout à la collection
            
        Examples:
            >>> # Ajout simple
            >>> await engine.add_documents(
            ...     collection="historique_ao",
            ...     documents=["AO région plateforme e-services..."]
            ... )
            >>> 
            >>> # Ajout avec métadonnées enrichies
            >>> await engine.add_documents(
            ...     collection="historique_ao",
            ...     documents=["Cahier charges plateforme..."],
            ...     metadatas=[{
            ...         "organisme": "Région Nouvelle-Aquitaine",
            ...         "montant": 750000,
            ...         "secteur": "Territorial",
            ...         "type_ao": "Ouvert",
            ...         "fourchette_montant": "500k-1M",
            ...         "date_publication": "2024-01-15",
            ...         "domaine_technique": "Développement"
            ...     }]
            ... )
        """
        start_time = datetime.utcnow()
        
        # Validation
        if not documents or not all(doc.strip() for doc in documents):
            raise ValidationError(
                "Liste de documents vide ou contient des documents vides",
                field_name="documents",
                field_value=f"{len(documents)} documents"
            )
        
        if metadatas and len(metadatas) != len(documents):
            raise ValidationError(
                f"Nombre métadonnées ({len(metadatas)}) != nombre documents ({len(documents)})",
                field_name="metadatas"
            )
        
        if ids and len(ids) != len(documents):
            raise ValidationError(
                f"Nombre IDs ({len(ids)}) != nombre documents ({len(documents)})",
                field_name="ids"
            )
        
        try:
            with PerformanceMetrics("add_documents", self.perf_logger) as metrics:
                # Récupération collection
                chroma_collection = await self._get_or_create_collection(collection)
                
                # Génération IDs si nécessaires
                if not ids:
                    timestamp = int(datetime.utcnow().timestamp() * 1000)
                    ids = [f"{collection}_{timestamp}_{i}" for i in range(len(documents))]
                
                # Enrichissement métadonnées par défaut
                if not metadatas:
                    metadatas = [{} for _ in documents]
                
                enriched_metadatas = []
                for i, metadata in enumerate(metadatas):
                    enriched = metadata.copy()
                    enriched.update({
                        "added_at": datetime.utcnow().isoformat(),
                        "collection": collection,
                        "document_length": len(documents[i]),
                        "scorpius_version": "1.0.0"
                    })
                    enriched_metadatas.append(enriched)
                
                # Ajout à ChromaDB (embeddings générés automatiquement)
                chroma_collection.add(
                    documents=documents,
                    metadatas=enriched_metadatas,
                    ids=ids
                )
                
                # Calcul métriques
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                total_chars = sum(len(doc) for doc in documents)
                estimated_cost = self.embedding_service.estimate_cost(documents)
                
                # Mise à jour stats
                self._stats["total_documents_added"] += len(documents)
                self._stats["total_embeddings_generated"] += len(documents)
                
                metrics.add_metric("documents_count", len(documents))
                metrics.add_metric("total_characters", total_chars)
                metrics.add_metric("estimated_cost_usd", estimated_cost)
                metrics.add_metric("collection", collection)
                
                self.business_logger.info(
                    "documents_added_to_collection",
                    collection=collection,
                    documents_count=len(documents),
                    total_characters=total_chars,
                    estimated_cost_usd=estimated_cost
                )
                
                return {
                    "documents_added": len(documents),
                    "collection": collection,
                    "duration_ms": duration,
                    "estimated_cost_usd": estimated_cost,
                    "total_characters": total_chars,
                    "ids_generated": ids
                }
                
        except Exception as e:
            self.logger.error(
                "add_documents_failed",
                collection=collection,
                documents_count=len(documents),
                error=str(e),
                error_type=type(e).__name__
            )
            
            if not isinstance(e, ScorpiusError):
                raise ScorpiusError(
                    f"Erreur lors de l'ajout de documents: {str(e)}",
                    error_code="ADD_DOCUMENTS_FAILED",
                    context={
                        "collection": collection,
                        "documents_count": len(documents)
                    }
                )
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de performance détaillées du moteur RAG.
        
        Returns:
            Dictionnaire avec métriques techniques et business
        """
        # Stats du service d'embedding
        embedding_stats = self.embedding_service.get_performance_stats()
        
        # Stats des collections
        collections_info = {}
        for name, collection in self._collections.items():
            try:
                count = collection.count()
                collections_info[name] = {
                    "document_count": count,
                    "description": self.DEFAULT_COLLECTIONS.get(name, {}).get("description", "")
                }
            except Exception:
                collections_info[name] = {"document_count": "error", "description": ""}
        
        return {
            # Stats moteur RAG
            "rag_engine": self._stats,
            
            # Stats service embedding
            "embedding_service": embedding_stats,
            
            # Stats collections
            "collections": collections_info,
            
            # Configuration
            "config": {
                "embedding_model": self.config.openai_model,
                "cache_enabled": self.config.cache_enabled,
                "chroma_host": self.config.chroma_host,
                "environment": self.config.environment
            },
            
            # Métriques calculées
            "computed_metrics": {
                "avg_cost_per_search": (
                    self._stats["total_cost_usd"] / max(1, self._stats["total_searches"])
                ),
                "docs_per_collection": (
                    self._stats["total_documents_added"] / max(1, len(self._collections))
                ),
                "cache_effectiveness": embedding_stats.get("cache_hit_rate", 0.0)
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Effectue un diagnostic complet de santé du moteur RAG.
        
        Returns:
            Rapport de santé avec statut de chaque composant
        """
        health_report = {
            "overall_status": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        try:
            # Test service embedding
            embedding_health = await self.embedding_service.health_check()
            health_report["components"]["embedding_service"] = embedding_health
            
            # Test ChromaDB
            try:
                heartbeat = self.chroma_client.heartbeat()
                health_report["components"]["chromadb"] = {
                    "status": "healthy",
                    "heartbeat_ns": heartbeat,
                    "collections_count": len(self._collections)
                }
            except Exception as e:
                health_report["components"]["chromadb"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
            
            # Test recherche simple
            try:
                test_results = await self.search(
                    "test de santé moteur rag",
                    limit=1,
                    min_similarity_score=0.0
                )
                health_report["components"]["rag_search"] = {
                    "status": "healthy",
                    "test_results_count": len(test_results)
                }
            except Exception as e:
                health_report["components"]["rag_search"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
            
            # Statut global
            all_healthy = all(
                comp.get("status") == "healthy" 
                for comp in health_report["components"].values()
            )
            health_report["overall_status"] = "healthy" if all_healthy else "unhealthy"
            
            # Ajout métriques performance
            health_report["performance_summary"] = {
                "total_searches": self._stats["total_searches"],
                "avg_search_time_ms": self._stats["avg_search_time_ms"],
                "cache_hit_rate": self._stats["cache_hit_rate"],
                "total_cost_usd": self._stats["total_cost_usd"]
            }
            
        except Exception as e:
            health_report["overall_status"] = "error"
            health_report["error"] = str(e)
        
        return health_report