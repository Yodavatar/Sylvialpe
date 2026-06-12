import os
import requests
import rasterio

# On prend directement l'URL d'une dalle valide de ta liste
URL_DALLE = "https://data.grandlyon.com/files/grandlyon/imagerie/ortho2023/ortho/tiff/500m_5cm_cc46/18310_51760_5cm_CC46.tif"
NOM_FICHIER = "18310_51760_5cm_CC46.tif"

# 1. Téléchargement direct du fichier GeoTIFF
if not os.path.exists(NOM_FICHIER):
    print(f"Téléchargement direct de la dalle {NOM_FICHIER}...")
    print("Format 5cm/pixel, le fichier peut faire plusieurs dizaines de Mo, patience...")
    
    response = requests.get(URL_DALLE)
    
    if response.status_code == 200:
        with open(NOM_FICHIER, "wb") as f:
            f.write(response.content)
        print("Téléchargement réussi avec succès !")
    else:
        print(f"Erreur de téléchargement. Code HTTP : {response.status_code}")
        exit()
else:
    print(f"Le fichier {NOM_FICHIER} est déjà présent localement.")

# 2. Vérification de la lecture de l'image avec rasterio
print("\nOuverture du fichier avec Rasterio...")
try:
    with rasterio.open(NOM_FICHIER) as src:
        print("\n=== PROPRIÉTÉS DE L'IMAGE LUE ===")
        print(f"Dimensions : {src.width} x {src.height} pixels")
        print(f"Nombre de bandes (couleurs) : {src.count}")
        print(f"Système de coordonnées (CRS) : {src.crs}")
        print("=================================")
    print("\nParfait ! Ton image est prête pour le traitement de données.")
except Exception as e:
    print(f"Erreur lors de la lecture du GeoTIFF : {e}")