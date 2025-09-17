"""Point d'entrée principal pour Scorpius RAG."""

import asyncio
import os
import structlog
from .utils.config import Config


def setup_logging():
    """Configure le système de logging."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def main():
    """Fonction principale de l'application."""
    setup_logging()
    logger = structlog.get_logger("ScorpiusRAG")
    
    try:
        # Chargement de la configuration
        config = Config.from_env()
        config.validate()
        
        logger.info(
            "Scorpius RAG démarré",
            environment=config.environment,
            openai_model=config.openai_model,
            cache_enabled=config.cache_enabled
        )
        
        # Pour l'instant, on garde l'application en vie
        logger.info("Application prête, en attente de requêtes...")
        
        # Boucle infinie pour garder l'application en vie
        while True:
            await asyncio.sleep(30)
            logger.debug("Application toujours active...")
            
    except Exception as e:
        logger.error("Erreur critique", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())