#!/usr/bin/env python3
"""Script de configuration rapide pour développement Scorpius RAG."""

import os
import sys
from pathlib import Path


def setup_directories():
    """Crée les répertoires nécessaires."""
    directories = [
        "data/chromadb",
        "cache/embeddings", 
        "logs"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Répertoire créé: {dir_path}")


def check_env_file():
    """Vérifie la configuration .env."""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ Fichier .env manquant")
        return False
    
    # Lecture variables obligatoires
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = []
    
    with open(env_path) as f:
        content = f.read()
        
    for var in required_vars:
        if f"{var}=sk-your-openai-api-key-here-replace-this-value" in content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables à configurer dans .env: {', '.join(missing_vars)}")
        print("   Éditez le fichier .env avec vos vraies valeurs")
        return False
    
    print("✅ Configuration .env valide")
    return True


def test_imports():
    """Teste les imports principaux."""
    try:
        sys.path.insert(0, str(Path.cwd()))
        
        from src.utils import Config
        from src.models import EmbeddingConfig
        from src.exceptions import ScorpiusError
        
        print("✅ Imports principaux OK")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur import: {e}")
        print("   Installez les dépendances: pip install -r requirements.txt")
        return False


def test_config():
    """Teste la configuration."""
    try:
        sys.path.insert(0, str(Path.cwd()))
        from src.utils import Config
        
        config = Config.from_env()
        config.validate()
        
        print("✅ Configuration système valide")
        return True
        
    except Exception as e:
        print(f"❌ Erreur configuration: {e}")
        return False


def show_next_steps():
    """Affiche les prochaines étapes."""
    print("\n🚀 Prochaines étapes:")
    print("1. Démarrez ChromaDB:")
    print("   chroma run --path ./data/chromadb --port 8000")
    print()
    print("2. Testez le moteur RAG:")
    print("   python -c \"import asyncio; from src.core import ScorpiusRAGEngine; print('Test:', asyncio.run(ScorpiusRAGEngine.create_from_env()))\"")
    print()
    print("3. Lancez les tests:")
    print("   pytest tests/unit/ -v")


def main():
    """Script principal de setup."""
    print("🏛️  Configuration Scorpius RAG - Environnement de développement")
    print("=" * 60)
    
    # Étapes de configuration
    steps = [
        ("Création répertoires", setup_directories),
        ("Vérification .env", check_env_file),
        ("Test imports", test_imports),
        ("Test configuration", test_config)
    ]
    
    all_success = True
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        try:
            success = step_func()
            if not success:
                all_success = False
        except Exception as e:
            print(f"❌ Erreur {step_name}: {e}")
            all_success = False
    
    print("\n" + "=" * 60)
    
    if all_success:
        print("✅ Configuration terminée avec succès!")
        show_next_steps()
    else:
        print("❌ Configuration incomplète - corrigez les erreurs ci-dessus")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())