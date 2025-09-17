#!/bin/bash

# Script de démarrage pour Scorpius RAG
# Gestion des signaux et initialisation propre

set -euo pipefail

# Configuration des logs
exec 1> >(tee -a /app/logs/app.log)
exec 2> >(tee -a /app/logs/error.log >&2)

echo "🚀 Démarrage Scorpius RAG - $(date)"

# Fonction de nettoyage pour arrêt propre
cleanup() {
    echo "🛑 Arrêt de Scorpius RAG - $(date)"
    # Arrêt des processus enfants
    if [[ -n "${APP_PID:-}" ]]; then
        kill -TERM "$APP_PID" 2>/dev/null || true
        wait "$APP_PID" 2>/dev/null || true
    fi
    echo "✅ Arrêt terminé - $(date)"
    exit 0
}

# Capture des signaux pour arrêt propre
trap cleanup SIGTERM SIGINT SIGQUIT

# Validation des variables d'environnement obligatoires
check_env_vars() {
    echo "🔍 Validation des variables d'environnement..."
    
    local required_vars=(
        "OPENAI_API_KEY"
        "CHROMA_HOST"
        "ENVIRONMENT"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo "❌ Variables d'environnement manquantes: ${missing_vars[*]}"
        exit 1
    fi
    
    echo "✅ Variables d'environnement validées"
}

# Attente des services dépendants
wait_for_services() {
    echo "⏳ Attente des services dépendants..."
    
    # Attente ChromaDB
    local chroma_url="http://${CHROMA_HOST}:${CHROMA_PORT:-8000}/api/v2/version"
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$chroma_url" >/dev/null 2>&1; then
            echo "✅ ChromaDB disponible"
            break
        fi
        echo "⏳ ChromaDB non disponible (tentative $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        echo "❌ ChromaDB non disponible après $max_attempts tentatives"
        exit 1
    fi
    
    # Attente Redis si configuré
    if [[ -n "${REDIS_HOST:-}" ]]; then
        local redis_host="${REDIS_HOST}"
        local redis_port="${REDIS_PORT:-6379}"
        
        attempt=1
        while [[ $attempt -le $max_attempts ]]; do
            # Test avec timeout intégré si nc n'est pas disponible
            if command -v nc >/dev/null 2>&1; then
                if nc -z "$redis_host" "$redis_port" 2>/dev/null; then
                    echo "✅ Redis disponible"
                    break
                fi
            else
                # Alternative avec timeout pour test de connexion
                if timeout 2 bash -c "</dev/tcp/$redis_host/$redis_port" 2>/dev/null; then
                    echo "✅ Redis disponible"
                    break
                fi
            fi
            echo "⏳ Redis non disponible (tentative $attempt/$max_attempts)"
            sleep 1
            ((attempt++))
        done
        
        if [[ $attempt -gt $max_attempts ]]; then
            echo "❌ Redis non disponible après $max_attempts tentatives"
            exit 1
        fi
    fi
}

# Initialisation des répertoires
init_directories() {
    echo "📁 Initialisation des répertoires..."
    
    local directories=(
        "/app/data/chromadb"
        "/app/cache/embeddings"
        "/app/logs"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            echo "✅ Répertoire créé: $dir"
        fi
    done
}

# Migration des données si nécessaire
run_migrations() {
    echo "🔄 Vérification des migrations..."
    
    # Exemple de migration (à adapter selon les besoins)
    if [[ -f "/app/src/migrations/migrate.py" ]]; then
        echo "🔄 Exécution des migrations..."
        python -m src.migrations.migrate
        echo "✅ Migrations terminées"
    else
        echo "ℹ️ Aucune migration à exécuter"
    fi
}

# Validation de la configuration
validate_config() {
    echo "🔧 Validation de la configuration..."
    
    python -c "
from src.utils.config import Config
try:
    config = Config.from_env()
    config.validate()
    print('✅ Configuration valide')
except Exception as e:
    print(f'❌ Configuration invalide: {e}')
    exit(1)
"
}

# Health check interne
health_check() {
    echo "🏥 Vérification de l'état de santé..."
    
    # Test basique de l'API
    if [[ -f "/app/src/health.py" ]]; then
        python -m src.health
    else
        echo "ℹ️ Pas de health check spécifique"
    fi
}

# Fonction principale
main() {
    echo "🔧 Configuration de l'environnement: ${ENVIRONMENT:-dev}"
    echo "🌍 Mode debug: ${DEBUG_MODE:-false}"
    echo "📊 Niveau de log: ${LOG_LEVEL:-INFO}"
    
    # Vérifications pré-démarrage
    check_env_vars
    init_directories
    wait_for_services
    validate_config
    run_migrations
    health_check
    
    echo "🎯 Démarrage de l'application..."
    echo "📋 Commande: $*"
    
    # Lancement de l'application en arrière-plan
    "$@" &
    APP_PID=$!
    
    echo "🚀 Application démarrée (PID: $APP_PID)"
    
    # Attente infinie avec gestion des signaux
    while true; do
        if ! kill -0 "$APP_PID" 2>/dev/null; then
            echo "❌ Application terminée de manière inattendue"
            exit 1
        fi
        sleep 5
    done
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi