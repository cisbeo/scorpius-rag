#!/bin/bash

# Script de démarrage Docker pour Scorpius RAG
# Gestion simplifiée des environnements et services

set -euo pipefail

# Configuration par défaut
ENVIRONMENT="production"
SERVICES="all"
DETACHED=true
MONITORING=false
JUPYTER=false
REBUILD=false
VERBOSE=false

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'aide
usage() {
    cat << EOF
🚀 Script de démarrage Docker pour Scorpius RAG

Usage: $0 [OPTIONS] [COMMAND]

Commands:
    start       Démarre les services (défaut)
    stop        Arrête les services
    restart     Redémarre les services
    logs        Affiche les logs
    status      Affiche l'état des services
    clean       Nettoie les volumes et images

Options:
    -e, --env ENV           Environnement (dev|prod) [défaut: prod]
    -s, --services SERVICES Services à démarrer (all|core|monitoring) [défaut: all]
    -f, --foreground        Mode premier plan (non détaché)
    -m, --monitoring        Active les services de monitoring
    -j, --jupyter           Active Jupyter Lab (dev uniquement)
    -r, --rebuild           Force le rebuild des images
    -v, --verbose           Mode verbeux
    -h, --help              Affiche cette aide

Exemples:
    $0                                      # Démarre en production
    $0 -e dev -j                           # Démarre en dev avec Jupyter
    $0 -e prod -m                          # Démarre en prod avec monitoring
    $0 -s core -f                          # Démarre uniquement les services core
    $0 stop                                 # Arrête tous les services
    $0 logs                                 # Affiche les logs

EOF
}

# Parse des arguments
COMMAND="start"
while [[ $# -gt 0 ]]; do
    case $1 in
        start|stop|restart|logs|status|clean)
            COMMAND="$1"
            shift
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -s|--services)
            SERVICES="$2"
            shift 2
            ;;
        -f|--foreground)
            DETACHED=false
            shift
            ;;
        -m|--monitoring)
            MONITORING=true
            shift
            ;;
        -j|--jupyter)
            JUPYTER=true
            shift
            ;;
        -r|--rebuild)
            REBUILD=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Option inconnue: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Validation des paramètres
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    echo -e "${RED}❌ Environnement invalide: $ENVIRONMENT (doit être 'dev' ou 'prod')${NC}"
    exit 1
fi

# Fonction de logging
log() {
    local level=$1
    shift
    case $level in
        "INFO")
            echo -e "${BLUE}ℹ️  $*${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}✅ $*${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $*${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $*${NC}"
            ;;
    esac
}

# Détermination des fichiers compose
get_compose_files() {
    local files=()
    
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        files+=("-f" "docker-compose.dev.yml")
    else
        files+=("-f" "docker-compose.yml")
    fi
    
    echo "${files[@]}"
}

# Détermination des profiles
get_profiles() {
    local profiles=()
    
    if [[ "$MONITORING" == "true" ]]; then
        profiles+=("--profile" "monitoring")
    fi
    
    if [[ "$JUPYTER" == "true" && "$ENVIRONMENT" == "dev" ]]; then
        profiles+=("--profile" "jupyter")
    fi
    
    echo "${profiles[@]}"
}

# Vérification des prérequis
check_prerequisites() {
    log "INFO" "Vérification des prérequis..."
    
    # Docker et Docker Compose
    if ! command -v docker &> /dev/null; then
        log "ERROR" "Docker n'est pas installé"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        log "ERROR" "Docker Compose n'est pas disponible"
        exit 1
    fi
    
    # Fichier d'environnement
    local env_file
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        env_file=".env"
    else
        env_file=".env.docker"
    fi
    
    if [[ ! -f "$env_file" ]]; then
        log "WARNING" "Fichier $env_file introuvable"
        if [[ -f ".env.example" ]]; then
            log "INFO" "Copie de .env.example vers $env_file"
            cp .env.example "$env_file"
        else
            log "ERROR" "Aucun fichier d'environnement disponible"
            exit 1
        fi
    fi
    
    log "SUCCESS" "Prérequis validés"
}

# Commande start
cmd_start() {
    log "INFO" "Démarrage de Scorpius RAG..."
    log "INFO" "Environnement: $ENVIRONMENT"
    log "INFO" "Services: $SERVICES"
    
    local compose_files
    local profiles
    compose_files=($(get_compose_files))
    profiles=($(get_profiles))
    
    # Rebuild si demandé
    if [[ "$REBUILD" == "true" ]]; then
        log "INFO" "Rebuild des images..."
        docker compose "${compose_files[@]}" build --no-cache
    fi
    
    # Construction de la commande
    local cmd=(docker compose "${compose_files[@]}" "${profiles[@]}")
    
    # Sélection des services
    case "$SERVICES" in
        "core")
            if [[ "$ENVIRONMENT" == "dev" ]]; then
                cmd+=(up scorpius-rag-dev chromadb-dev)
            else
                cmd+=(up scorpius-rag chromadb redis)
            fi
            ;;
        "monitoring")
            cmd+=(up prometheus grafana)
            ;;
        "all")
            cmd+=(up)
            ;;
        *)
            log "ERROR" "Services invalides: $SERVICES"
            exit 1
            ;;
    esac
    
    # Mode détaché ou premier plan
    if [[ "$DETACHED" == "true" ]]; then
        cmd+=(-d)
    fi
    
    # Exécution
    log "INFO" "Commande: ${cmd[*]}"
    "${cmd[@]}"
    
    if [[ "$DETACHED" == "true" ]]; then
        log "SUCCESS" "Services démarrés en arrière-plan"
        cmd_status
    fi
}

# Commande stop
cmd_stop() {
    log "INFO" "Arrêt des services..."
    
    local compose_files
    compose_files=($(get_compose_files))
    
    docker compose "${compose_files[@]}" down
    log "SUCCESS" "Services arrêtés"
}

# Commande restart
cmd_restart() {
    log "INFO" "Redémarrage des services..."
    cmd_stop
    sleep 2
    cmd_start
}

# Commande logs
cmd_logs() {
    log "INFO" "Affichage des logs..."
    
    local compose_files
    compose_files=($(get_compose_files))
    
    docker compose "${compose_files[@]}" logs -f --tail=100
}

# Commande status
cmd_status() {
    log "INFO" "État des services:"
    
    local compose_files
    compose_files=($(get_compose_files))
    
    docker compose "${compose_files[@]}" ps
    
    echo ""
    log "INFO" "Services exposés:"
    
    if [[ "$ENVIRONMENT" == "dev" ]]; then
        echo "  🚀 Scorpius RAG (dev): http://localhost:8000"
        echo "  🗄️  ChromaDB:          http://localhost:8001"
        if [[ "$JUPYTER" == "true" ]]; then
            echo "  📓 Jupyter Lab:       http://localhost:8889"
        fi
    else
        echo "  🚀 Scorpius RAG:       http://localhost:8000"
        echo "  🗄️  ChromaDB:          http://localhost:8001"
        echo "  🔴 Redis:              localhost:6379"
        if [[ "$MONITORING" == "true" ]]; then
            echo "  📊 Prometheus:        http://localhost:9090"
            echo "  📈 Grafana:           http://localhost:3000"
        fi
    fi
}

# Commande clean
cmd_clean() {
    log "WARNING" "Nettoyage des volumes et images..."
    
    read -p "Êtes-vous sûr de vouloir nettoyer? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "INFO" "Nettoyage annulé"
        return
    fi
    
    local compose_files
    compose_files=($(get_compose_files))
    
    # Arrêt et suppression
    docker compose "${compose_files[@]}" down -v --remove-orphans
    
    # Nettoyage des images
    docker system prune -f
    docker volume prune -f
    
    log "SUCCESS" "Nettoyage terminé"
}

# Fonction principale
main() {
    echo -e "${BLUE}"
    echo "🚀 =================================="
    echo "   Scorpius RAG Docker Runner"
    echo "==================================${NC}"
    echo ""
    
    check_prerequisites
    
    case "$COMMAND" in
        "start")
            cmd_start
            ;;
        "stop")
            cmd_stop
            ;;
        "restart")
            cmd_restart
            ;;
        "logs")
            cmd_logs
            ;;
        "status")
            cmd_status
            ;;
        "clean")
            cmd_clean
            ;;
        *)
            log "ERROR" "Commande inconnue: $COMMAND"
            usage
            exit 1
            ;;
    esac
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi