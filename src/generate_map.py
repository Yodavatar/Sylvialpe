import pandas as pd
import folium
import json
import os
from pyproj import Transformer

#print(os.path.abspath(os.getcwd()))

TOTAL_DALLES_CIBLE = 2588
SURFACE_TOTALE_ZONE_KM2 = TOTAL_DALLES_CIBLE * 0.25 

# 1. Configuration des projections géographiques (CC46 vers GPS WGS84)
transformer = Transformer.from_crs("EPSG:3946", "EPSG:4326", always_xy=True)

def calculer_stats(csv_path):
    df = pd.read_csv(csv_path)
    nb_dalles = len(df)
    total_surface = df["Surface Arborée (m2)"].sum()
    return nb_dalles, total_surface

def cc46_to_wgs84(x_cc46, y_cc46):
    """Convertit un point CC46 en coordonnées GPS (Lat, Lon)"""
    lon, lat = transformer.transform(x_cc46, y_cc46)
    return lat, lon

def get_color(pourcentage):
    """Définit la couleur du carré selon le taux de verdure"""
    if pourcentage < 3:
        return "#d63031" # Rouge vif
    elif pourcentage < 7:
        return "#fdcb6e" # Jaune/Orange
    elif pourcentage < 12:
        return "#3dfa8b" # Vert clair
    else:
        return "#46775A" # Vert foncé

if __name__ == "__main__":
    csv_path = "data/inventaire_canopee_lyon.csv"
    df = pd.read_csv(csv_path)

    
    nb_analyzed = len(df)
    surface_verte_km2 = round(df["Surface Arborée (m2)"].sum() / 1000000, 2)
    pourcentage_global = round((surface_verte_km2 / SURFACE_TOTALE_ZONE_KM2) * 100, 2)

    stats = {
        "nb_analyzed": nb_analyzed,
        "nb_total": TOTAL_DALLES_CIBLE,
        "surface_verte_km2": surface_verte_km2,
        "surface_totale_km2": SURFACE_TOTALE_ZONE_KM2,
        "pourcentage": pourcentage_global
    }

    with open("website/stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f)
    print("✅ stats.json mis à jour.")

    # 3. Génération de la CARTE
    carte = folium.Map(location=[45.75, 4.85], zoom_start=12, tiles="OpenStreetMap")
    PAS = 500 

    for _, row in df.iterrows():
        parts = row["Nom Dalle"].split('_')
        x_min, y_min = float(parts[0]) * 100, float(parts[1]) * 100
        x_max, y_max = x_min + PAS, y_min + PAS
        
        # Conversion des 4 coins
        poly = [cc46_to_wgs84(x_min, y_min), cc46_to_wgs84(x_min, y_max), 
                cc46_to_wgs84(x_max, y_max), cc46_to_wgs84(x_max, y_min)]
        
        # Formatage des données pour un affichage propre
        verdure_pct = round(row["Pourcentage Verdure (%)"], 2)
        surface_m2 = round(row["Surface Arborée (m2)"], 2)
        
        # Construction du texte du popup (avec balises HTML pour la mise en forme)
        texte_popup = f"""
        <strong>Dalle :</strong> {row['Nom Dalle']}<br>
        <strong>Verdure :</strong> {verdure_pct} %<br>
        <strong>Surface arborée :</strong> {surface_m2:,} m²
        """.replace(',', ' ') # Espace pour le séparateur des milliers
        
        folium.Polygon(
            locations=[[lat, lon] for lat, lon in poly],
            fill=True, fill_color=get_color(row["Pourcentage Verdure (%)"]),
            fill_opacity=0.4, color=get_color(row["Pourcentage Verdure (%)"]),
            weight=1.5,
            popup=folium.Popup(texte_popup, max_width=300)
        ).add_to(carte)

    # --- INJECTION DU BOUTON ET DE LA LÉGENDE INTERACTIVE ---
    html_legende = """
    <div id="wrapper-legende" style="position: fixed; top: 20px; right: 20px; z-index: 9999;">
        <button id="btn-legende" onclick="toggleLegende()" style="
            background-color: #2c3e50; color: white; border: none; 
            padding: 10px 15px; font-weight: bold; border-radius: 5px; 
            cursor: pointer; box-shadow: 0 2px 5px rgba(0,0,0,0.3); font-family: sans-serif;">
            ℹ️ Légende & Algos
        </button>
        
        <div id="panneau-legende" style="
            display: none; background: white; width: 300px; padding: 15px; 
            border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); 
            margin-top: 10px; font-family: sans-serif; font-size: 14px; color: #333; line-height: 1.4;">
            
            <h3 style="margin-top: 0; color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px;">Sylvialpe — Canopée</h3>
            <p style="font-size: 12px; color: #7f8c8d; margin-bottom: 15px;">Classification de la végétation par dalles de 500m × 500m.</p>
            
            <div style="margin-bottom: 8px;"><span style="display:inline-block; width:20px; height:15px; background:#27ae60; vertical-align:middle; margin-right:8px; border-radius:3px;"></span><b>&gt; 12 % :</b> Forêt / Végétation dense (Vert foncé)</div>
            <div style="margin-bottom: 8px;"><span style="display:inline-block; width:20px; height:15px; background:#2ecc71; vertical-align:middle; margin-right:8px; border-radius:3px;"></span><b>7 % à 12 % :</b> Zone arborée / Parcs (Vert clair)</div>
            <div style="margin-bottom: 8px;"><span style="display:inline-block; width:20px; height:15px; background:#fdcb6e; vertical-align:middle; margin-right:8px; border-radius:3px;"></span><b>3 % à 7 % :</b> Tissu urbain mixte (Orange)</div>
            <div style="margin-bottom: 15px;"><span style="display:inline-block; width:20px; height:15px; background:#d63031; vertical-align:middle; margin-right:8px; border-radius:3px;"></span><b>&lt; 3 % :</b> Zone minérale / Béton (Rouge)</div>
            
            <h4 style="margin-bottom: 5px; color: #2c3e50;">Méthodologie Hybride</h4>
            <p style="font-size: 11px; margin-top: 0; text-align: justify; color: #555;">
                Les pixels sont d'abord isolés par couleur (masque HSV). Le moteur applique ensuite un filtre de texture (Canny) combiné à une fermeture morphologique. Cela permet de valider la rugosité de la canopée et de fusionner les arbres en massifs cohérents tout en éliminant les faux positifs lisses (piscines, pelouses rases).
            </p>
        </div>
    </div>

    <script>
    function toggleLegende() {
        var panneau = document.getElementById("panneau-legende");
        var btn = document.getElementById("btn-legende");
        if (panneau.style.display === "none") {
            panneau.style.display = "block";
            btn.style.backgroundColor = "#e74c3c";
            btn.innerHTML = "❌ Fermer";
        } else {
            panneau.style.display = "none";
            btn.style.backgroundColor = "#2c3e50";
            btn.innerHTML = "ℹ️ Légende & Algos";
        }
    }
    </script>
    """

    # On injecte le bloc HTML/JS dans le corps de la carte Folium
    carte.get_root().html.add_child(folium.Element(html_legende))

    # Sauvegarde de la carte
    carte_output = "website/map/index.html"
    carte.save(carte_output)
    print(f"🎉 Carte avec bouton générée ! Ouvre '{carte_output}' pour tester.")
