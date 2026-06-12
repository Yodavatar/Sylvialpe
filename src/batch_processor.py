import os
import csv
import requests
import rasterio
import cv2
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager

# On importe ton moteur de détection
from src.analyse import algo_seuil_couleur_base, algo_hybride_blocs

# Configuration
CSV_OUTPUT = "inventaire_canopee_lyon.csv"
API_URL = "https://data.grandlyon.com/fr/datapusher/ws/grandlyon/ima_gestion_images.imaortho2023tif500m5cmcc46/all.json?maxfeatures=-1"

# Nombre de dalles traitées en simultané (Adapte selon tes cœurs, ex: 4, 8, 12...)
MAX_WORKERS = 16

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
        
    # On ajoute le PID (identifiant du processus) pour éviter que deux dalles n'entrent en conflit
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
        # 4. Nettoyage immédiat
        if os.path.exists(nom_fichier_local):
            os.remove(nom_fichier_local)

# --- PROGRAMME PRINCIPAL ---
if __name__ == "__main__":
    lista_dalles = recuperer_catalogue_dalles()
    total_dalles = len(lista_dalles)
    
    if total_dalles == 0:
        print("Catalogue vide. Vérifie l'URL de l'API.")
        exit()
        
    print(f"Succès ! {total_dalles} dalles trouvées.")
    print(f"Lancement du traitement parallèle sur {MAX_WORKERS} cœurs simultanés.\n")
    
    # Initialisation du fichier CSV proprement (mode écriture pour écraser l'ancien s'il existe)
    with open(CSV_OUTPUT, mode="w", newline="", encoding="utf-8") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(["Nom Dalle", "Pixels Blancs (Arbres)", "Pourcentage Verdure (%)", "Surface Arborée (m2)"])

    # Utilisation d'un Manager multiprocessing pour partager le Verrou entre les cœurs
    with Manager() as manager:
        verrou = manager.Lock()
        
        # On lance le pool de cœurs de ton processeur
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # On prépare toutes les tâches
            futures = [
                executor.submit(traiter_une_dalle, item, idx, total_dalles, verrou, CSV_OUTPUT)
                for idx, item in enumerate(lista_dalles, start=1)
            ]
            
            # Récupération des résultats au fur et à mesure de leur complétion
            for future in as_completed(futures):
                resultat_log = future.result()
                if resultat_log:
                    print(resultat_log)

    print(f"\n Analyse multi-cœurs terminée ! Tableau complet dispo dans '{CSV_OUTPUT}'.")