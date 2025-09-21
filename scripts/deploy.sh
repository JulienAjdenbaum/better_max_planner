#!/bin/bash

# Script de Déploiement Docker du Planificateur TGV Max

echo "🚄 Construction de l'image Docker du Planificateur TGV Max..."

# Construire l'image Docker
docker build -t tgvmax-planner .

if [ $? -eq 0 ]; then
    echo "✅ Image Docker construite avec succès !"
    
    echo "🚀 Démarrage du conteneur Planificateur TGV Max..."
    
    # Arrêter le conteneur existant s'il fonctionne
    docker stop tgvmax-planner 2>/dev/null || true
    docker rm tgvmax-planner 2>/dev/null || true
    
    # Exécuter le conteneur
    docker run -d \
        --name tgvmax-planner \
        -p 5163:5163 \
        -v $(pwd)/data/tgvmax.db:/app/data/tgvmax.db \
        --restart unless-stopped \
        tgvmax-planner
    
    if [ $? -eq 0 ]; then
        echo "✅ Le Planificateur TGV Max fonctionne maintenant !"
        echo "🌐 Accédez à l'application à : http://localhost:5163"
        echo ""
        echo "📊 Statut du conteneur :"
        docker ps --filter name=tgvmax-planner
    else
        echo "❌ Échec du démarrage du conteneur"
        exit 1
    fi
else
    echo "❌ Échec de la construction de l'image Docker"
    exit 1
fi 