"""Tests unitaires pour OpenAIEmbeddingService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from src.services.openai_embedding_service import OpenAIEmbeddingService
from src.models.embedding_config import EmbeddingConfig
from src.exceptions import OpenAIError, ValidationError, ConfigurationError


class TestOpenAIEmbeddingService:
    """Tests unitaires pour OpenAIEmbeddingService."""
    
    @pytest.fixture
    def valid_config(self) -> EmbeddingConfig:
        """Configuration valide pour tests."""
        return EmbeddingConfig(
            api_key="sk-test-1234567890abcdef1234567890abcdef1234567890abcdef",
            model="text-embedding-3-large",
            timeout=30,
            max_retries=3,
            batch_size=50,
            cache_enabled=True
        )
    
    @pytest.fixture
    def mock_openai_client(self):
        """Client OpenAI mocké."""
        client = AsyncMock()
        
        # Mock response embeddings
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536)
        ]
        mock_response.usage.total_tokens = 10
        
        client.embeddings.create.return_value = mock_response
        return client
    
    @pytest.fixture
    def mock_cache(self):
        """Cache mocké."""
        cache = MagicMock()
        cache.get.return_value = None  # Par défaut, pas de cache hit
        cache.set = MagicMock()
        cache.get_stats.return_value = {
            "hit_rate": 0.5,
            "total_savings_usd": 0.001
        }
        return cache
    
    def test_init_with_valid_config(self, valid_config: EmbeddingConfig):
        """Test initialisation avec configuration valide."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI') as mock_openai, \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'):
            
            mock_tiktoken.encoding_for_model.return_value = MagicMock()
            
            service = OpenAIEmbeddingService(valid_config)
            
            assert service.embedding_config == valid_config
            assert service.cache is not None
            mock_openai.assert_called_once()
            mock_cache_class.assert_called_once()
    
    def test_init_with_invalid_config(self):
        """Test initialisation avec configuration invalide."""
        with pytest.raises(ValidationError):
            OpenAIEmbeddingService("invalid_config")
    
    def test_validate_config_missing_api_key(self):
        """Test validation avec clé API manquante."""
        config = EmbeddingConfig(api_key="")
        
        with pytest.raises(ConfigurationError):
            OpenAIEmbeddingService(config)
    
    def test_validate_config_invalid_api_key_format(self):
        """Test validation avec format clé API invalide."""
        config = EmbeddingConfig(api_key="invalid-key-format")
        
        with pytest.raises(ConfigurationError):
            OpenAIEmbeddingService(config)
    
    @pytest.mark.asyncio
    async def test_embed_single_text_cache_miss(self, valid_config: EmbeddingConfig):
        """Test embedding texte unique avec cache miss."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI') as mock_openai_class, \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'):
            
            # Setup mocks
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_response.usage.total_tokens = 5
            mock_client.embeddings.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            mock_cache = MagicMock()
            mock_cache.get.return_value = None  # Cache miss
            mock_cache_class.return_value = mock_cache
            
            mock_tiktoken.encoding_for_model.return_value = MagicMock()
            
            # Test
            service = OpenAIEmbeddingService(valid_config)
            result = await service.embed("test text")
            
            # Vérifications
            assert result == [0.1] * 1536
            mock_client.embeddings.create.assert_called_once()
            mock_cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_embed_single_text_cache_hit(self, valid_config: EmbeddingConfig):
        """Test embedding texte unique avec cache hit."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI') as mock_openai_class, \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'):
            
            # Setup mocks
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client
            
            cached_embedding = [0.5] * 1536
            mock_cache = MagicMock()
            mock_cache.get.return_value = cached_embedding  # Cache hit
            mock_cache_class.return_value = mock_cache
            
            mock_tiktoken.encoding_for_model.return_value = MagicMock()
            
            # Test
            service = OpenAIEmbeddingService(valid_config)
            result = await service.embed("test text")
            
            # Vérifications
            assert result == cached_embedding
            mock_client.embeddings.create.assert_not_called()  # Pas d'appel API
            mock_cache.set.assert_not_called()  # Pas de mise en cache
    
    @pytest.mark.asyncio
    async def test_embed_multiple_texts(self, valid_config: EmbeddingConfig):
        """Test embedding textes multiples."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI') as mock_openai_class, \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'):
            
            # Setup mocks
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1] * 1536),
                MagicMock(embedding=[0.2] * 1536)
            ]
            mock_response.usage.total_tokens = 10
            mock_client.embeddings.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            mock_cache = MagicMock()
            mock_cache.get.return_value = None  # Cache miss pour tous
            mock_cache_class.return_value = mock_cache
            
            mock_tiktoken.encoding_for_model.return_value = MagicMock()
            
            # Test
            service = OpenAIEmbeddingService(valid_config)
            texts = ["text 1", "text 2"]
            result = await service.embed(texts)
            
            # Vérifications
            assert len(result) == 2
            assert result[0] == [0.1] * 1536
            assert result[1] == [0.2] * 1536
            mock_client.embeddings.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_embed_empty_text(self, valid_config: EmbeddingConfig):
        """Test embedding avec texte vide."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI'), \
             patch('src.services.openai_embedding_service.EmbeddingCache'), \
             patch('src.services.openai_embedding_service.tiktoken'), \
             patch('src.services.openai_embedding_service.structlog'):
            
            service = OpenAIEmbeddingService(valid_config)
            
            with pytest.raises(ValidationError, match="Textes vides ou invalides"):
                await service.embed("")
    
    @pytest.mark.asyncio
    async def test_embed_batch_success(self, valid_config: EmbeddingConfig):
        """Test embedding batch réussi."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI') as mock_openai_class, \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'):
            
            # Setup mocks
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1] * 1536),
                MagicMock(embedding=[0.2] * 1536),
                MagicMock(embedding=[0.3] * 1536)
            ]
            mock_response.usage.total_tokens = 15
            mock_client.embeddings.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_cache_class.return_value = mock_cache
            
            mock_tiktoken.encoding_for_model.return_value = MagicMock()
            
            # Test
            service = OpenAIEmbeddingService(valid_config)
            texts = ["text 1", "text 2", "text 3"]
            result = await service.embed_batch(texts, batch_size=10)
            
            # Vérifications
            assert len(result) == 3
            assert all(len(emb) == 1536 for emb in result)
    
    @pytest.mark.asyncio
    async def test_openai_api_error_handling(self, valid_config: EmbeddingConfig):
        """Test gestion erreurs API OpenAI."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI') as mock_openai_class, \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'):
            
            # Setup mocks
            mock_client = AsyncMock()
            
            # Mock exception avec response
            mock_exception = Exception("Rate limit exceeded")
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "error": {
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_exceeded",
                    "code": "rate_limit_exceeded"
                }
            }
            mock_response.status_code = 429
            mock_exception.response = mock_response
            
            mock_client.embeddings.create.side_effect = mock_exception
            mock_openai_class.return_value = mock_client
            
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_cache_class.return_value = mock_cache
            
            mock_tiktoken.encoding_for_model.return_value = MagicMock()
            
            # Test
            service = OpenAIEmbeddingService(valid_config)
            
            with pytest.raises(OpenAIError):
                await service._call_openai_api(["test"], "text-embedding-3-large")
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, valid_config: EmbeddingConfig):
        """Test respect du rate limiting."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI') as mock_openai_class, \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'), \
             patch('src.services.openai_embedding_service.time') as mock_time, \
             patch('src.services.openai_embedding_service.asyncio.sleep') as mock_sleep:
            
            # Setup mocks
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_response.usage.total_tokens = 5
            mock_client.embeddings.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_cache_class.return_value = mock_cache
            
            mock_tiktoken.encoding_for_model.return_value = MagicMock()
            
            # Simulation temps
            mock_time.time.side_effect = [1000, 1000.01, 1000.02]  # Appels très rapprochés
            
            # Test
            service = OpenAIEmbeddingService(valid_config)
            service._rate_limit_delay = 0.1  # 100ms entre requêtes
            
            await service._call_openai_api(["test"], "text-embedding-3-large")
            await service._call_openai_api(["test2"], "text-embedding-3-large")
            
            # Vérification que sleep a été appelé pour respecter rate limit
            mock_sleep.assert_called()
    
    def test_get_embedding_dimension(self, valid_config: EmbeddingConfig):
        """Test récupération dimension embeddings."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI'), \
             patch('src.services.openai_embedding_service.EmbeddingCache'), \
             patch('src.services.openai_embedding_service.tiktoken'), \
             patch('src.services.openai_embedding_service.structlog'):
            
            service = OpenAIEmbeddingService(valid_config)
            
            assert service.get_embedding_dimension() == 3072  # text-embedding-3-large
    
    def test_get_max_tokens(self, valid_config: EmbeddingConfig):
        """Test récupération limite tokens."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI'), \
             patch('src.services.openai_embedding_service.EmbeddingCache'), \
             patch('src.services.openai_embedding_service.tiktoken'), \
             patch('src.services.openai_embedding_service.structlog'):
            
            service = OpenAIEmbeddingService(valid_config)
            
            assert service.get_max_tokens() == 8191
    
    def test_estimate_cost(self, valid_config: EmbeddingConfig):
        """Test estimation coût."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI'), \
             patch('src.services.openai_embedding_service.EmbeddingCache'), \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'):
            
            # Mock tokenizer
            mock_tokenizer = MagicMock()
            mock_tokenizer.encode.return_value = [1] * 10  # 10 tokens
            mock_tiktoken.encoding_for_model.return_value = mock_tokenizer
            
            service = OpenAIEmbeddingService(valid_config)
            
            cost = service.estimate_cost("test text")
            
            # Vérification coût calculé (10 tokens * prix par 1k tokens)
            expected_cost = (10 / 1000) * 0.00013  # text-embedding-3-large price
            assert abs(cost - expected_cost) < 0.0001
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, valid_config: EmbeddingConfig):
        """Test health check avec service en bonne santé."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI') as mock_openai_class, \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'):
            
            # Setup mocks pour embed réussi
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_response.usage.total_tokens = 5
            mock_client.embeddings.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_cache_class.return_value = mock_cache
            
            mock_tiktoken.encoding_for_model.return_value = MagicMock()
            
            # Test
            service = OpenAIEmbeddingService(valid_config)
            health = await service.health_check()
            
            # Vérifications
            assert health["status"] == "healthy"
            assert health["model"] == "text-embedding-3-large"
            assert health["embedding_dimension"] == 1536
            assert health["cache_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, valid_config: EmbeddingConfig):
        """Test health check avec service défaillant."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI') as mock_openai_class, \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken') as mock_tiktoken, \
             patch('src.services.openai_embedding_service.structlog'):
            
            # Setup mocks pour échec embed
            mock_client = AsyncMock()
            mock_client.embeddings.create.side_effect = Exception("API Error")
            mock_openai_class.return_value = mock_client
            
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_cache_class.return_value = mock_cache
            
            mock_tiktoken.encoding_for_model.return_value = MagicMock()
            
            # Test
            service = OpenAIEmbeddingService(valid_config)
            health = await service.health_check()
            
            # Vérifications
            assert health["status"] == "unhealthy"
            assert "error" in health
            assert health["error_type"] == "OpenAIError"
    
    def test_get_performance_stats(self, valid_config: EmbeddingConfig):
        """Test récupération statistiques performance."""
        with patch('src.services.openai_embedding_service.AsyncOpenAI'), \
             patch('src.services.openai_embedding_service.EmbeddingCache') as mock_cache_class, \
             patch('src.services.openai_embedding_service.tiktoken'), \
             patch('src.services.openai_embedding_service.structlog'):
            
            # Mock cache avec stats
            mock_cache = MagicMock()
            mock_cache.get_stats.return_value = {"hit_rate": 0.75}
            mock_cache_class.return_value = mock_cache
            
            service = OpenAIEmbeddingService(valid_config)
            
            # Simulation de stats
            service._stats["total_requests"] = 20
            service._stats["cache_hits"] = 15
            
            stats = service.get_performance_stats()
            
            # Vérifications
            assert "cache_hit_rate" in stats
            assert stats["cache_hit_rate"] == 0.75
            assert "cache_stats" in stats
            assert "config" in stats