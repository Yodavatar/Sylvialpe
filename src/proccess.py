import os
import csv
import requests
import rasterio
import cv2
import numpy as np
import pandas as pd # Ajout pour faciliter la gestion de l'index
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager

# On importe ton moteur de détection
from src.analyse import algo_seuil_couleur_base, algo_hybride_blocs

# Configuration
CSV_OUTPUT = "inventaire_canopee_lyon.csv"
API_URL = "https://data.grandlyon.com/fr/datapusher/ws/grandlyon/ima_gestion_images.imaortho2023tif500m5cmcc46/all.json?maxfeatures=-1"

# Nombre de dalles traitées en simultané
MAX_WORKERS = 16

def charger_index_dalles(chemin_csv):
    """Charge les noms de dalles déjà traitées pour filtrer la liste."""
    if not os.path.exists(chemin_csv):
        return set()
    try:
        # On lit uniquement la colonne 'Nom Dalle' pour aller vite
        df = pd.read_csv(chemin_csv)
        return set(df['Nom Dalle'].astype(str))
    except Exception as e:
        print(f"Attention : impossible de lire l'index existant ({e}). Démarrage à zéro.")
        return set()

def recuperer_catalogue_dalles():
    """Interroge l'API du Grand Lyon pour obtenir la liste de toutes les dalles."""
    print("Connexion à l'API Data Grand Lyon pour récupérer le catalogue...")
    try:
        response = requests.get(API_URL, timeout=30)
        if response.status_code == 200:
            data = response.json()
            dalles = data.get("values", [])
            if not dalles and "features" in data:
                dalles = data["features"]
            return dalles
        return []
    except Exception as e:
        print(f"Erreur catalogue : {e}")
        return []

def extraire_infos_dalle(donnees_dalle):
    """Extrait le nom et l'URL de téléchargement."""
    properties = donnees_dalle.get("properties", donnees_dalle)
    nom = properties.get("nom", properties.get("id"))
    url = properties.get("url", properties.get("url_telechargement"))
    return nom, url

def traiter_une_dalle(item, index, total, verrou_csv, csv_path):
    """Fonction exécutée par un cœur : gère le cycle de vie complet d'une dalle."""
    nom_dalle, url_telechargement = extraire_infos_dalle(item)
    
    if not nom_dalle or not url_telechargement:
        return False
        
    nom_fichier_local = f"tmp_{os.getpid()}_{nom_dalle}.tif"
    
    try:
        # 1. Téléchargement
        res_img = requests.get(url_telechargement, timeout=60)
        if res_img.status_code != 200:
            return f"[{index}/{total}] {nom_dalle} -> Échec téléchargement (HTTP {res_img.status_code})"
            
        with open(nom_fichier_local, "wb") as f_img:
            f_img.write(res_img.content)
        
        # 2. Analyse spatiale
        with rasterio.open(nom_fichier_local) as src:
            r = src.read(1)
            g = src.read(2)
            b = src.read(3)
            img_rgb = np.dstack((r, g, b)).astype(np.uint8)
        
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        masque_vert = algo_seuil_couleur_base(img_bgr)
        masque_hybride = algo_hybride_blocs(img_bgr, masque_vert)
        
        pixels_blancs = np.count_nonzero(masque_hybride)
        pourcentage = (pixels_blancs / 100000000) * 100
        surface_m2 = pixels_blancs * 0.0025
        
        # 3. Écriture sécurisée dans le CSV grâce au Verrou (Lock)
        with verrou_csv:
            with open(csv_path, mode="a", newline="", encoding="utf-8") as f_csv:
                writer = csv.writer(f_csv)
                writer.writerow([nom_dalle, pixels_blancs, f"{pourcentage:.4f}", f"{surface_m2:.2f}"])
                
        return f"✅ Dalle [{index}/{total}] Terminée ! -> {nom_dalle} | Verdure : {pourcentage:.2f}% | Surface : {surface_m2:,.1f} m²"

    except Exception as e:
        return f"[{index}/{total}] Erreur sur {nom_dalle} : {e}"
        
    finally:
        if os.path.exists(nom_fichier_local):
            os.remove(nom_fichier_local)

# --- PROGRAMME PRINCIPAL ---
if __name__ == "__main__":
    # 1. Récupération complète
    lista_dalles_totales = recuperer_catalogue_dalles()
    
    # 2. Création de l'index (Le filtre)
    dalles_deja_traitees = charger_index_dalles(CSV_OUTPUT)
    
    # 3. Filtrage : On ne garde que celles qui ne sont pas dans le CSV
    lista_dalles = [
        dalle for dalle in lista_dalles_totales 
        if extraire_infos_dalle(dalle)[0] not in dalles_deja_traitees
    ]
    
    total_a_traiter = len(lista_dalles)
    
    if total_a_traiter == 0:
        print("Toutes les dalles ont déjà été traitées ! Rien à faire.")
        exit()
        
    print(f"Reprise du travail. {len(dalles_deja_traitees)} dalles déjà faites.")
    print(f"Lancement du traitement pour les {total_a_traiter} dalles restantes sur {MAX_WORKERS} cœurs.")
    
    # 4. Initialisation du CSV uniquement s'il n'existe pas
    if not os.path.exists(CSV_OUTPUT):
        with open(CSV_OUTPUT, mode="w", newline="", encoding="utf-8") as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(["Nom Dalle", "Pixels Blancs (Arbres)", "Pourcentage Verdure (%)", "Surface Arborée (m2)"])

    # Utilisation d'un Manager multiprocessing
    with Manager() as manager:
        verrou = manager.Lock()
        
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(traiter_une_dalle, item, idx, total_a_traiter, verrou, CSV_OUTPUT)
                for idx, item in enumerate(lista_dalles, start=1)
            ]
            
            for future in as_completed(futures):
                resultat_log = future.result()
                if resultat_log:
                    print(resultat_log)

    print(f"\n Analyse terminée ! Tableau complété dans '{CSV_OUTPUT}'.")