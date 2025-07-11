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
from utils import update_db, engine

# Configuration de la journalisation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/tgvmax_update.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    """Fonction principale pour mettre à jour la base de données."""
    try:
        logging.info("Début du processus de mise à jour de la base de données")
        
        # Vérifier si le fichier de base de données existe et est accessible en écriture
        db_path = 'tgvmax.db'
        if not os.path.exists(db_path):
            logging.error(f"Fichier de base de données {db_path} introuvable")
            return 1
        
        if not os.access(db_path, os.W_OK):
            logging.error(f"Le fichier de base de données {db_path} n'est pas accessible en écriture")
            return 1
        
        # Mettre à jour la base de données
        update_db(engine)
        
        logging.info("Mise à jour de la base de données terminée avec succès")
        return 0
        
    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour de la base de données : {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 