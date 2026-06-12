import os
import cv2
import numpy as np
import rasterio

NOM_FICHIER = "18310_51760_5cm_CC46.tif"

def charger_image_geotiff(chemin_fichier):
    """Charge l'image GeoTIFF et la convertit au format BGR pour OpenCV."""
    print("Lecture des bandes RGB de l'image haute résolution...")
    with rasterio.open(chemin_fichier) as src:
        r = src.read(1)
        g = src.read(2)
        b = src.read(3)
        img_rgb = np.dstack((r, g, b)).astype(np.uint8)
    
    # Conversion en BGR pour OpenCV
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

def algo_seuil_couleur_base(img_bgr):
    """Version originale : Détection uniquement basée sur la couleur verte HSV."""
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    # Plage de vert
    vert_bas = np.array([35, 40, 40])
    vert_haut = np.array([85, 255, 255])
    
    masque = cv2.inRange(img_hsv, vert_bas, vert_haut)
    return masque

def algo_filtrage_morphologique(masque_base):
    """
    ALGO 1 : Filtrage par taille et forme.
    Utilise l'ouverture morphologique pour supprimer les herbes fines et isolées,
    et détacher les arbres des grandes surfaces lisses.
    """
    print("Exécution de l'algorithme 1 : Filtrage Morphologique...")
    # On crée un élément structurant circulaire (ellipse) de 9x9 pixels
    # Plus le noyau est grand, plus on élimine les grandes surfaces de pelouse continues
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    
    # L'ouverture (MORPH_OPEN) est une érosion suivie d'une dilatation
    masque_nettoye = cv2.morphologyEx(masque_base, cv2.MORPH_OPEN, kernel)
    return masque_nettoye

def algo_analyse_texture(img_bgr, masque_base):
    """
    ALGO 2 : Analyse de texture (Contours/Gradients).
    Les herbes/champs sont lisses (peu de contours), les arbres ont du relief (beaucoup de contours).
    """
    print("Exécution de l'algorithme 2 : Analyse de Texture (Canny)...")
    # 1. Passage en niveaux de gris
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # 2. Détection des contours avec Canny (seuils à ajuster si besoin)
    contours = cv2.Canny(img_gray, 40, 150)
    
    # 3. On dilate les lignes de contours pour créer des "zones texturées" épaisses
    kernel = np.ones((5, 5), np.uint8)
    masque_texture = cv2.dilate(contours, kernel, iterations=2)
    
    # 4. On combine : le pixel doit être VERT (masque_base) ET avoir du RELIEF (masque_texture)
    masque_final = cv2.bitwise_and(masque_base, masque_texture)
    return masque_final

def algo_hybride_blocs(img_bgr, masque_base):
    """
    ALGO 4 : L'approche Hybride (Penser en Blocs).
    Prend la précision de la texture (Canny) et regroupe les pixels proches
    pour former des "blocs" de végétation stables, comme des îlots de fraîcheur.
    """
    print("Exécution de l'algorithme 4 : Approche Hybride par Blocs...")
    
    # 1. On récupère la texture fine (comme ton Algo 2)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    contours = cv2.Canny(img_gray, 40, 150)
    kernel_texture = np.ones((5, 5), np.uint8)
    masque_texture = cv2.dilate(contours, kernel_texture, iterations=2)
    texture_fine = cv2.bitwise_and(masque_base, masque_texture)
    
    # 2. On transforme le résultat en "blocs" (Morphologie)
    # Noyau pour connecter les pixels proches (Fermeture)
    kernel_bloc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    
    # Étape A : On bouche les trous à l'intérieur des arbres (Fermeture)
    masque_blocs = cv2.morphologyEx(texture_fine, cv2.MORPH_CLOSE, kernel_bloc)
    
    # Étape B : On élimine les petits blocs isolés/bruit du sol (Ouverture)
    masque_final = cv2.morphologyEx(masque_blocs, cv2.MORPH_OPEN, kernel_bloc)
    
    return masque_final


def generer_statistiques(nom_algo, masque):
    """Calcule le taux de couverture et la surface réelle en m²."""
    total_pixels = masque.size
    pixels_blancs = np.count_nonzero(masque)
    pourcentage = (pixels_blancs / total_pixels) * 100
    
    # Calcul de la surface réelle : chaque pixel vaut 0.0025 m²
    surface_m2 = pixels_blancs * 0.0025
    
    print(f"[{nom_algo}]")
    print(f"  -> Taux de couverture : {pourcentage:.2f} %")
    print(f"  -> Surface arborée    : {surface_m2:,.2f} m² (sur 250,000 m² au total)")
    print(f"  -> Pixels blancs      : {pixels_blancs:,}\n")

if __name__ == "__main__":
    if not os.path.exists(NOM_FICHIER):
        print(f"Erreur : Le fichier {NOM_FICHIER} est introuvable. Exécute d'abord le script de téléchargement.")
        exit()

    img_bgr = charger_image_geotiff(NOM_FICHIER)
    
    masque_vert_base = algo_seuil_couleur_base(img_bgr)
    
    masque_morpho = algo_filtrage_morphologique(masque_vert_base)
    masque_texture = algo_analyse_texture(img_bgr, masque_vert_base)
    masque_hybride = algo_hybride_blocs(img_bgr, masque_vert_base)
    masque_inverse = algo_filtrage_morphologique(masque_vert_base)
    
    # Affichage des statistiques comparatives
    print("\n=== COMPARAISON DES ALGORITHMES ===")
    generer_statistiques("Base (Vert uniquement)", masque_vert_base)
    generer_statistiques("Algo 1 (Morphologique) ", masque_morpho)
    generer_statistiques("Algo 2 (Texture Canny) ", masque_texture)
    generer_statistiques("Algo 3 (Hybride par Blocs) ", masque_hybride)
    generer_statistiques("Algo 4 (Inverse Morpho puis Texture) ", masque_inverse)

    print("===================================\n")
    
    # Préparation des images de rendu pour inspection visuelle
    print("Génération des images de preview (redimensionnées en 1200x1200)...")
    preview_size = (1200, 1200)
    
    cv2.imwrite("preview_0_origine.jpg", cv2.resize(img_bgr, preview_size))
    cv2.imwrite("preview_1_base.jpg", cv2.resize(masque_vert_base, preview_size))
    cv2.imwrite("preview_2_morpho.jpg", cv2.resize(masque_morpho, preview_size))
    cv2.imwrite("preview_3_texture.jpg", cv2.resize(masque_texture, preview_size))
    cv2.imwrite("preview_4_hybride.jpg", cv2.resize(masque_hybride, preview_size))
