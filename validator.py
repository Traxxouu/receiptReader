import time
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "receiptReader/1.0 (stage-project)"}


def valider_adresse(adresse_brute: str, code_postal: str = None, ville: str = None) -> dict:
    """
    Valide l'adresse via Nominatim.
    Stratégie en cascade :
      1. Adresse complète brute
      2. Fallback : code postal + ville uniquement
    """
    result = {
        "adresse_validee": None,
        "latitude": None,
        "longitude": None,
        "confiance": "non trouvée",
        "mode": None,
    }

    # Tentative 1 : adresse complète
    if adresse_brute:
        res = _query_nominatim(adresse_brute)
        if res:
            result.update(res)
            result["mode"] = "adresse complète"
            return result
        time.sleep(1)

    # Tentative 2 : fallback code postal + ville
    if code_postal and ville:
        query = f"{ville}, {code_postal}, France"
        res = _query_nominatim(query)
        if res:
            result.update(res)
            result["mode"] = "fallback ville"
            return result
        time.sleep(1)

    # Tentative 3 : fallback code postal seul
    if code_postal:
        query = f"{code_postal}, France"
        res = _query_nominatim(query)
        if res:
            result.update(res)
            result["mode"] = "fallback code postal"
            return result
        time.sleep(1)

    return result


def _query_nominatim(query: str) -> dict | None:
    """Envoie une requête à Nominatim et retourne le résultat ou None."""
    try:
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": 1,
            "countrycodes": "fr",
        }
        response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data:
            top = data[0]
            importance = float(top.get("importance", 0))
            return {
                "adresse_validee": top.get("display_name"),
                "latitude": top.get("lat"),
                "longitude": top.get("lon"),
                "confiance": "haute" if importance > 0.5 else "moyenne",
            }
    except Exception:
        pass

    time.sleep(1)
    return None
