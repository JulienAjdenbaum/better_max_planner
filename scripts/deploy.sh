#!/bin/bash

# Script de Déploiement Docker du Planificateur TGV Max
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🚄 Déploiement du Planificateur TGV Max..."

# Create necessary directories
echo "📁 Création des répertoires..."
mkdir -p data logs

# Create empty database file if it doesn't exist
if [ ! -f "data/tgvmax.db" ]; then
    touch data/tgvmax.db
    echo "📄 Fichier de base de données créé"
fi

# Build and start with docker compose
echo "🐳 Construction et démarrage avec Docker Compose..."
docker compose down 2>/dev/null || true
docker compose up -d --build

if [ $? -eq 0 ]; then
    echo "✅ Conteneur démarré avec succès !"
    
    # Wait for container to be ready
    echo "⏳ Attente du démarrage du conteneur..."
    sleep 5
    
    # Initialize database if empty
    DB_SIZE=$(stat -f%z "data/tgvmax.db" 2>/dev/null || stat -c%s "data/tgvmax.db" 2>/dev/null || echo "0")
    if [ "$DB_SIZE" -lt 1000 ]; then
        echo "📥 Initialisation de la base de données..."
        docker exec tgvmax-planner python -c "from src.utils import update_db, engine; update_db(engine)"
        echo "✅ Base de données initialisée"
    fi
    
    # Install cron jobs
    echo "⏰ Installation des tâches cron..."
    
    # Generate crontab with correct paths
    CRONTAB_TEMPLATE="$PROJECT_DIR/config/crontab_entry"
    CRONTAB_GENERATED="/tmp/tgvmax_crontab"
    sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" "$CRONTAB_TEMPLATE" > "$CRONTAB_GENERATED"
    
    # Install crontab
    crontab "$CRONTAB_GENERATED"
    rm "$CRONTAB_GENERATED"
    echo "✅ Tâches cron installées"
    
    echo ""
    echo "🎉 Déploiement terminé avec succès !"
    echo "🌐 Accédez à l'application à : http://localhost:5163"
    echo ""
    echo "📊 Statut du conteneur :"
    docker ps --filter name=tgvmax-planner
    echo ""
    echo "⏰ Tâches cron configurées :"
    crontab -l
else
    echo "❌ Échec du démarrage du conteneur"
    exit 1
fi