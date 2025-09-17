#!/bin/bash

# Script de build Docker pour Scorpius RAG
# Supporte les builds de développement et production

set -euo pipefail

# Configuration par défaut
TARGET="production"
TAG="latest"
NO_CACHE=false
PUSH=false
REGISTRY=""
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
🐳 Script de build Docker pour Scorpius RAG

Usage: $0 [OPTIONS]

Options:
    -t, --target TARGET      Target de build (development|production) [défaut: production]
    -g, --tag TAG           Tag de l'image [défaut: latest]
    -n, --no-cache          Build sans cache Docker
    -p, --push              Push l'image vers le registry
    -r, --registry REGISTRY Registry Docker (ex: ghcr.io/user/repo)
    -v, --verbose           Mode verbeux
    -h, --help              Affiche cette aide

Exemples:
    $0                                    # Build production avec tag latest
    $0 -t development -g dev              # Build développement avec tag dev
    $0 -t production -g v1.0.0 -p         # Build et push version v1.0.0
    $0 -n -v                              # Build sans cache en mode verbeux

EOF
}

# Parse des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -g|--tag)
            TAG="$2"
            shift 2
            ;;
        -n|--no-cache)
            NO_CACHE=true
            shift
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
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
if [[ "$TARGET" != "development" && "$TARGET" != "production" ]]; then
    echo -e "${RED}❌ Target invalide: $TARGET (doit être 'development' ou 'production')${NC}"
    exit 1
fi

# Détermination du nom de l'image
if [[ -n "$REGISTRY" ]]; then
    IMAGE_NAME="$REGISTRY/scorpius-rag:$TAG"
else
    IMAGE_NAME="scorpius-rag:$TAG"
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

# Vérification des prérequis
check_prerequisites() {
    log "INFO" "Vérification des prérequis..."
    
    # Docker disponible
    if ! command -v docker &> /dev/null; then
        log "ERROR" "Docker n'est pas installé ou accessible"
        exit 1
    fi
    
    # Docker daemon en cours d'exécution
    if ! docker info &> /dev/null; then
        log "ERROR" "Docker daemon n'est pas en cours d'exécution"
        exit 1
    fi
    
    # Dockerfile existe
    if [[ ! -f "Dockerfile" ]]; then
        log "ERROR" "Dockerfile introuvable dans le répertoire courant"
        exit 1
    fi
    
    log "SUCCESS" "Prérequis validés"
}

# Build de l'image
build_image() {
    log "INFO" "Début du build Docker..."
    log "INFO" "Target: $TARGET"
    log "INFO" "Image: $IMAGE_NAME"
    
    # Construction des arguments de build
    local build_args=(
        "build"
        "--target" "$TARGET"
        "--tag" "$IMAGE_NAME"
    )
    
    # Cache
    if [[ "$NO_CACHE" == "true" ]]; then
        build_args+=("--no-cache")
        log "INFO" "Build sans cache activé"
    fi
    
    # Mode verbeux
    if [[ "$VERBOSE" == "true" ]]; then
        build_args+=("--progress=plain")
    fi
    
    # Build args pour le target
    case "$TARGET" in
        "production")
            build_args+=("--build-arg" "ENV=production")
            ;;
        "development")
            build_args+=("--build-arg" "ENV=development")
            ;;
    esac
    
    # Contexte de build
    build_args+=(".")
    
    # Exécution du build
    log "INFO" "Commande: docker ${build_args[*]}"
    
    if docker "${build_args[@]}"; then
        log "SUCCESS" "Build terminé avec succès"
    else
        log "ERROR" "Échec du build Docker"
        exit 1
    fi
}

# Push de l'image
push_image() {
    if [[ "$PUSH" == "true" ]]; then
        if [[ -z "$REGISTRY" ]]; then
            log "WARNING" "Registry non spécifié, push ignoré"
            return
        fi
        
        log "INFO" "Push de l'image vers $REGISTRY..."
        
        if docker push "$IMAGE_NAME"; then
            log "SUCCESS" "Push terminé avec succès"
        else
            log "ERROR" "Échec du push"
            exit 1
        fi
    fi
}

# Affichage des informations sur l'image
show_image_info() {
    log "INFO" "Informations sur l'image buildée:"
    echo ""
    docker images "$IMAGE_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo ""
    
    # Affichage des layers (mode verbeux)
    if [[ "$VERBOSE" == "true" ]]; then
        log "INFO" "Historique des layers:"
        docker history "$IMAGE_NAME" --no-trunc
    fi
}

# Nettoyage optionnel
cleanup() {
    log "INFO" "Nettoyage des images intermédiaires..."
    docker image prune -f
    log "SUCCESS" "Nettoyage terminé"
}

# Fonction principale
main() {
    echo -e "${BLUE}"
    echo "🐳 =================================="
    echo "   Scorpius RAG Docker Build"
    echo "==================================${NC}"
    echo ""
    
    check_prerequisites
    build_image
    push_image
    show_image_info
    
    # Nettoyage si demandé
    read -p "Nettoyer les images intermédiaires? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup
    fi
    
    echo ""
    log "SUCCESS" "Build Docker terminé !"
    log "INFO" "Image disponible: $IMAGE_NAME"
    
    if [[ "$TARGET" == "development" ]]; then
        echo ""
        log "INFO" "Pour démarrer en mode développement:"
        echo "  docker-compose -f docker-compose.dev.yml up -d"
    else
        echo ""
        log "INFO" "Pour démarrer en mode production:"
        echo "  docker-compose up -d"
    fi
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi