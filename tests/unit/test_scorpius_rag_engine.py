"""Tests unitaires pour ScorpiusRAGEngine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
from typing import List, Dict, Any

from src.core.scorpius_rag_engine import ScorpiusRAGEngine
from src.models import SearchResult, AOContext, EmbeddingConfig
from src.models.ao_context import AOType, Sector, TechnicalDomain
from src.services import OpenAIEmbeddingService
from src.utils import Config
from src.exceptions import ValidationError, ChromaDBError, OpenAIError


class TestScorpiusRAGEngine:
    """Tests unitaires pour la classe ScorpiusRAGEngine."""
    
    @pytest.fixture
    def mock_config(self) -> Config:
        """Configuration de test."""
        return Config(
            openai_api_key="sk-test-key-1234567890",
            openai_model="text-embedding-3-large",
            chroma_host="localhost",
            chroma_port=8000,
            cache_enabled=True,
            environment="test"
        )
    
    @pytest.fixture
    def mock_embedding_service(self) -> AsyncMock:
        """Service d'embedding mocké."""
        service = AsyncMock(spec=OpenAIEmbeddingService)
        service.embed.return_value = [0.1] * 1536  # Mock embedding 1536D
        service.embed_batch.return_value = [[0.1] * 1536, [0.2] * 1536]
        service.get_embedding_dimension.return_value = 1536
        service.get_max_tokens.return_value = 8191
        service.estimate_cost.return_value = 0.0001
        service.get_performance_stats.return_value = {
            "total_requests": 10,
            "cache_hits": 5,
            "cache_hit_rate": 0.5,
            "total_cost_usd": 0.001
        }
        service.health_check.return_value = {"status": "healthy"}
        return service
    
    @pytest.fixture
    def mock_chroma_client(self) -> MagicMock:
        """Client ChromaDB mocké."""
        client = MagicMock()
        client.heartbeat.return_value = 123456789
        
        # Mock collection
        mock_collection = MagicMock()
        mock_collection.count.return_value = 100
        mock_collection.query.return_value = {
            "documents": [["Document test AO région plateforme"]],
            "metadatas": [[{
                "organisme": "Région Test",
                "montant": 500000,
                "secteur": "Territorial",
                "type_ao": "Ouvert"
            }]],
            "distances": [[0.2]]  # Distance faible = similarité haute
        }
        mock_collection.add = MagicMock()
        
        client.get_collection.return_value = mock_collection
        client.create_collection.return_value = mock_collection
        
        return client
    
    @pytest.fixture
    def rag_engine(
        self, 
        mock_config: Config, 
        mock_embedding_service: AsyncMock,
        mock_chroma_client: MagicMock
    ) -> ScorpiusRAGEngine:
        """Instance ScorpiusRAGEngine pour tests."""
        with patch('src.core.scorpius_rag_engine.structlog') as mock_structlog:
            mock_logger = MagicMock()
            mock_structlog.get_logger.return_value = mock_logger
            
            engine = ScorpiusRAGEngine(
                config=mock_config,
                embedding_service=mock_embedding_service,
                chroma_client=mock_chroma_client
            )
            return engine
    
    @pytest.mark.asyncio
    async def test_create_from_env_success(self, mock_config: Config):
        """Test création réussie depuis variables d'environnement."""
        with patch.multiple(
            'src.core.scorpius_rag_engine',
            Config=MagicMock(return_value=mock_config),
            setup_logger=MagicMock(),
            EmbeddingConfig=MagicMock(),
            OpenAIEmbeddingService=AsyncMock(),
            chromadb=MagicMock(),
            structlog=MagicMock()
        ) as mocks:
            # Configuration mocks
            mocks['Config'].from_env.return_value = mock_config
            mock_config.validate = MagicMock()
            
            # Mock service embedding
            mock_embedding_service = AsyncMock()
            mock_embedding_service.health_check.return_value = {"status": "healthy"}
            mocks['OpenAIEmbeddingService'].return_value = mock_embedding_service
            
            # Mock ChromaDB
            mock_chroma_client = MagicMock()
            mock_chroma_client.heartbeat.return_value = 123456789
            mocks['chromadb'].Client.return_value = mock_chroma_client
            
            # Test création
            engine = await ScorpiusRAGEngine.create_from_env()
            
            assert engine is not None
            assert engine.config == mock_config
            mocks['Config'].from_env.assert_called_once()
            mock_config.validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_from_env_openai_unhealthy(self, mock_config: Config):
        """Test échec création si OpenAI non disponible."""
        with patch.multiple(
            'src.core.scorpius_rag_engine',
            Config=MagicMock(return_value=mock_config),
            setup_logger=MagicMock(),
            EmbeddingConfig=MagicMock(),
            OpenAIEmbeddingService=AsyncMock(),
            chromadb=MagicMock(),
            structlog=MagicMock()
        ) as mocks:
            # Configuration
            mocks['Config'].from_env.return_value = mock_config
            mock_config.validate = MagicMock()
            
            # Service embedding unhealthy
            mock_embedding_service = AsyncMock()
            mock_embedding_service.health_check.return_value = {
                "status": "unhealthy", 
                "error": "API key invalid"
            }
            mocks['OpenAIEmbeddingService'].return_value = mock_embedding_service
            
            # Test échec
            with pytest.raises(OpenAIError, match="Service OpenAI non disponible"):
                await ScorpiusRAGEngine.create_from_env()
    
    @pytest.mark.asyncio
    async def test_search_success(self, rag_engine: ScorpiusRAGEngine):
        """Test recherche réussie avec résultats."""
        # Préparation contexte AO
        context = AOContext(
            ao_type=AOType.OUVERT,
            sector=Sector.TERRITORIAL,
            estimated_amount=500000,
            technical_domains=[TechnicalDomain.DEVELOPPEMENT]
        )
        
        # Exécution recherche
        results = await rag_engine.search(
            query="plateforme e-services citoyens",
            collection="historique_ao",
            context=context,
            limit=3
        )
        
        # Vérifications
        assert isinstance(results, list)
        assert len(results) <= 3
        
        if results:
            result = results[0]
            assert isinstance(result, SearchResult)
            assert result.content == "Document test AO région plateforme"
            assert result.collection == "historique_ao"
            assert 0.0 <= result.similarity_score <= 1.0
            assert result.metadata["secteur"] == "Territorial"
        
        # Vérification appels services
        rag_engine.embedding_service.embed.assert_called_once()
        rag_engine.chroma_client.get_collection.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, rag_engine: ScorpiusRAGEngine):
        """Test recherche avec requête vide."""
        with pytest.raises(ValidationError, match="Requête vide ou invalide"):
            await rag_engine.search("")
    
    @pytest.mark.asyncio
    async def test_search_invalid_limit(self, rag_engine: ScorpiusRAGEngine):
        """Test recherche avec limite invalide."""
        with pytest.raises(ValidationError, match="limit.*value.*out.*range"):
            await rag_engine.search("test", limit=0)
        
        with pytest.raises(ValidationError, match="limit.*value.*out.*range"):
            await rag_engine.search("test", limit=101)
    
    @pytest.mark.asyncio
    async def test_search_invalid_similarity_score(self, rag_engine: ScorpiusRAGEngine):
        """Test recherche avec score similarité invalide."""
        with pytest.raises(ValidationError):
            await rag_engine.search("test", min_similarity_score=-0.1)
        
        with pytest.raises(ValidationError):
            await rag_engine.search("test", min_similarity_score=1.1)
    
    def test_enrich_query_with_context(self, rag_engine: ScorpiusRAGEngine):
        """Test enrichissement requête avec contexte AO."""
        context = AOContext(
            ao_type=AOType.OUVERT,
            sector=Sector.TERRITORIAL,
            estimated_amount=750000,
            technical_domains=[TechnicalDomain.DEVELOPPEMENT, TechnicalDomain.INFRA_CLOUD],
            organisme="Région Nouvelle-Aquitaine"
        )
        
        enriched = rag_engine._enrich_query_with_context("plateforme digitale", context)
        
        assert "plateforme digitale" in enriched
        assert "appel offres Ouvert" in enriched
        assert "secteur Territorial" in enriched
        assert "montant 500k-1M" in enriched
        assert "technologies Développement Infrastructure/Cloud" in enriched
        assert "organisme Région Nouvelle-Aquitaine" in enriched
    
    def test_enrich_query_without_context(self, rag_engine: ScorpiusRAGEngine):
        """Test enrichissement requête sans contexte."""
        original_query = "plateforme digitale"
        enriched = rag_engine._enrich_query_with_context(original_query, None)
        
        assert enriched == original_query
    
    def test_build_metadata_filters_with_context(self, rag_engine: ScorpiusRAGEngine):
        """Test construction filtres métadonnées avec contexte."""
        context = AOContext(
            ao_type=AOType.OUVERT,
            sector=Sector.TERRITORIAL,
            estimated_amount=500000,
            technical_domains=[TechnicalDomain.DEVELOPPEMENT]
        )
        
        filters = rag_engine._build_metadata_filters(context, None)
        
        assert filters["secteur"] == "Territorial"
        assert filters["type_ao"] == "Ouvert"
        assert filters["fourchette_montant"] == "500k-1M"
        assert filters["domaine_technique"] == {"$in": ["Développement"]}
    
    def test_build_metadata_filters_additional(self, rag_engine: ScorpiusRAGEngine):
        """Test construction filtres avec filtres additionnels."""
        additional_filters = {"organisme": {"$like": "%région%"}}
        
        filters = rag_engine._build_metadata_filters(None, additional_filters)
        
        assert filters == additional_filters
    
    def test_calculate_contextual_relevance(self, rag_engine: ScorpiusRAGEngine):
        """Test calcul score pertinence contextuelle."""
        metadata = {
            "secteur": "Territorial",
            "type_ao": "Ouvert",
            "fourchette_montant": "500k-1M",
            "organisme": "Région Test"
        }
        
        context = AOContext(
            ao_type=AOType.OUVERT,
            sector=Sector.TERRITORIAL,
            estimated_amount=750000,
            organisme="Région Nouvelle-Aquitaine"
        )
        
        relevance = rag_engine._calculate_contextual_relevance(metadata, context, 0.8)
        
        # Score de base + bonus secteur + bonus type AO + bonus montant + bonus organisme
        # 0.8 + 0.1 + 0.1 + 0.08 + 0.05 = 1.13 mais plafonné à 1.0
        assert relevance == 1.0
    
    def test_calculate_contextual_relevance_no_context(self, rag_engine: ScorpiusRAGEngine):
        """Test calcul pertinence sans contexte."""
        metadata = {"secteur": "Territorial"}
        base_score = 0.75
        
        relevance = rag_engine._calculate_contextual_relevance(metadata, None, base_score)
        
        assert relevance == base_score
    
    @pytest.mark.asyncio
    async def test_add_documents_success(self, rag_engine: ScorpiusRAGEngine):
        """Test ajout documents réussi."""
        documents = ["Document AO test 1", "Document AO test 2"]
        metadatas = [
            {"organisme": "Test 1", "montant": 100000},
            {"organisme": "Test 2", "montant": 200000}
        ]
        
        result = await rag_engine.add_documents(
            collection="test_collection",
            documents=documents,
            metadatas=metadatas
        )
        
        # Vérifications
        assert result["documents_added"] == 2
        assert result["collection"] == "test_collection"
        assert "duration_ms" in result
        assert "estimated_cost_usd" in result
        assert len(result["ids_generated"]) == 2
        
        # Vérification appel ChromaDB
        rag_engine.chroma_client.get_collection.assert_called()
    
    @pytest.mark.asyncio
    async def test_add_documents_empty_list(self, rag_engine: ScorpiusRAGEngine):
        """Test ajout liste documents vide."""
        with pytest.raises(ValidationError, match="Liste de documents vide"):
            await rag_engine.add_documents("test", [])
    
    @pytest.mark.asyncio
    async def test_add_documents_metadata_mismatch(self, rag_engine: ScorpiusRAGEngine):
        """Test ajout avec métadonnées mal dimensionnées."""
        documents = ["Doc 1", "Doc 2"]
        metadatas = [{"test": "data"}]  # Une seule métadonnée pour 2 docs
        
        with pytest.raises(ValidationError, match="Nombre métadonnées.*nombre documents"):
            await rag_engine.add_documents("test", documents, metadatas)
    
    def test_get_performance_stats(self, rag_engine: ScorpiusRAGEngine):
        """Test récupération statistiques performance."""
        # Simulation de données stats
        rag_engine._stats["total_searches"] = 10
        rag_engine._stats["total_cost_usd"] = 0.05
        
        stats = rag_engine.get_performance_stats()
        
        # Vérifications structure
        assert "rag_engine" in stats
        assert "embedding_service" in stats
        assert "collections" in stats
        assert "config" in stats
        assert "computed_metrics" in stats
        
        # Vérifications contenu
        assert stats["rag_engine"]["total_searches"] == 10
        assert stats["config"]["embedding_model"] == "text-embedding-3-large"
        assert "avg_cost_per_search" in stats["computed_metrics"]
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, rag_engine: ScorpiusRAGEngine):
        """Test diagnostic santé avec tous composants OK."""
        # Mock recherche test réussie
        with patch.object(rag_engine, 'search') as mock_search:
            mock_search.return_value = [MagicMock()]
            
            health = await rag_engine.health_check()
            
            assert health["overall_status"] == "healthy"
            assert "components" in health
            assert health["components"]["embedding_service"]["status"] == "healthy"
            assert health["components"]["chromadb"]["status"] == "healthy"
            assert health["components"]["rag_search"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_chromadb_unhealthy(self, rag_engine: ScorpiusRAGEngine):
        """Test diagnostic avec ChromaDB défaillant."""
        # Mock ChromaDB qui lève exception
        rag_engine.chroma_client.heartbeat.side_effect = Exception("Connection failed")
        
        health = await rag_engine.health_check()
        
        assert health["overall_status"] == "unhealthy"
        assert health["components"]["chromadb"]["status"] == "unhealthy"
        assert "Connection failed" in health["components"]["chromadb"]["error"]


class TestScorpiusRAGEngineIntegration:
    """Tests d'intégration pour ScorpiusRAGEngine."""
    
    @pytest.mark.asyncio
    async def test_full_search_workflow(self):
        """Test workflow complet de recherche."""
        # Ce test nécessiterait des vraies instances ChromaDB et OpenAI
        # Pour l'instant, on se contente d'un placeholder
        pass
    
    @pytest.mark.asyncio  
    async def test_full_add_documents_workflow(self):
        """Test workflow complet d'ajout documents."""
        # Ce test nécessiterait des vraies instances ChromaDB et OpenAI
        # Pour l'instant, on se contente d'un placeholder
        pass


# Fixtures partagées pour tous les tests
@pytest.fixture(scope="session")
def test_config():
    """Configuration de test partagée."""
    return {
        "openai_api_key": "sk-test-key",
        "openai_model": "text-embedding-3-large",
        "cache_enabled": True,
        "environment": "test"
    }


@pytest.fixture
def sample_ao_context():
    """Contexte AO d'exemple pour tests."""
    return AOContext(
        ao_type=AOType.OUVERT,
        sector=Sector.TERRITORIAL,
        estimated_amount=500000,
        technical_domains=[TechnicalDomain.DEVELOPPEMENT],
        organisme="Région Test",
        geographic_scope="Nouvelle-Aquitaine"
    )


@pytest.fixture
def sample_search_results():
    """Résultats de recherche d'exemple."""
    return [
        SearchResult(
            content="AO développement plateforme e-services citoyens",
            metadata={
                "organisme": "Région Nouvelle-Aquitaine",
                "montant": 750000,
                "secteur": "Territorial",
                "type_ao": "Ouvert"
            },
            similarity_score=0.95,
            collection="historique_ao",
            ao_type="Ouvert",
            sector="Territorial",
            amount_range="500k-1M",
            relevance_score=0.98
        ),
        SearchResult(
            content="Cahier charges plateforme numérique territoriale",
            metadata={
                "organisme": "Département Gironde",
                "montant": 450000,
                "secteur": "Territorial",
                "type_ao": "MAPA"
            },
            similarity_score=0.87,
            collection="historique_ao",
            ao_type="MAPA",
            sector="Territorial",
            amount_range="100k-500k",
            relevance_score=0.89
        )
    ]