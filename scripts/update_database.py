#!/usr/bin/env python3
"""
Script de mise à jour de la base de données pour le Planificateur TGV Max
Ce script met à jour la base de données avec des données fraîches de l'API SNCF.
Conçu pour être exécuté par cron toutes les 12 heures.
"""

import os
import sys
import logging
from datetime import datetime
# Add the parent directory to the Python path so we can import src modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import update_db, engine
from src.logging_config import setup_logging

setup_logging(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'tgvmax_update.log'))
logger = logging.getLogger(__name__)

def main():
    """Fonction principale pour mettre à jour la base de données."""
    try:
        logger.info("Début du processus de mise à jour de la base de données")
        
        # Vérifier si le fichier de base de données existe et est accessible en écriture
        db_path = 'tgvmax.db'
        if not os.path.exists(db_path):
            logger.error("Fichier de base de données %s introuvable", db_path)
            return 1

        if not os.access(db_path, os.W_OK):
            logger.error("Le fichier de base de données %s n'est pas accessible en écriture", db_path)
            return 1
        
        # Mettre à jour la base de données
        update_db(engine)

        logger.info("Mise à jour de la base de données terminée avec succès")
        return 0
        
    except Exception:
        logger.exception("Erreur lors de la mise à jour de la base de données")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 
