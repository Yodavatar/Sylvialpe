import requests

# URL de l'API Grand Lyon
API_URL = "https://data.grandlyon.com/fr/datapusher/ws/grandlyon/ima_gestion_images.imaortho2023tif500m5cmcc46/all.json?maxfeatures=-1"

def calculer_poids_total():
    print("Récupération de la liste des dalles...")
    data = requests.get(API_URL).json()
    # Gestion des formats d'API (values ou features)
    dalles = data.get("values", data.get("features", []))
    
    total_octets = 0
    print(f"Calcul du poids pour {len(dalles)} dalles. Veuillez patienter...")
    
    for i, item in enumerate(dalles, 1):
        properties = item.get("properties", item)
        url = properties.get("url", properties.get("url_telechargement"))
        
        try:
            # On demande uniquement les headers (très rapide)
            response = requests.head(url, timeout=10)
            taille = int(response.headers.get('Content-Length', 0))
            total_octets += taille
        except Exception:
            pass
            
        if i % 100 == 0:
            print(f"Progression : {i}/{len(dalles)}...")

    return total_octets

def afficher_taille(octets):
    bit = octets * 8
    ko = octets / 1024
    mo = ko / 1024
    go = mo / 1024
    
    print("\n--- RÉSULTATS DU POIDS TOTAL ---")
    print(f"Bits : {bit:,.0f} bits")
    print(f"Octets : {octets:,.0f} octets")
    print(f"Mégaoctets (Mo) : {mo:,.2f} Mo")
    print(f"Gigaoctets (Go) : {go:,.2f} Go")

if __name__ == "__main__":
    taille_totale = calculer_poids_total()
    afficher_taille(taille_totale)