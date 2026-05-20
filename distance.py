import requests
import time


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
HEADERS = {"User-Agent": "receiptReader/1.0 (stage-project)"}


def _geocode(adresse: str) -> tuple[float, float] | None:
    """Convertit une adresse en coordonnees GPS via Nominatim."""
    try:
        params = {
            "q": adresse,
            "format": "json",
            "limit": 1,
            "countrycodes": "fr",
        }
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    time.sleep(1)
    return None


def calculer_distance(adresse_labo: str, adresse_ticket: str) -> float | None:
    """
    Calcule la distance routiere en km entre deux adresses.
    Utilise Nominatim pour geocoder et OSRM pour la distance routiere.
    Retourne la distance en km ou None si impossible.
    """
    coords_labo = _geocode(adresse_labo)
    if not coords_labo:
        return None

    time.sleep(1)  # Respect rate limit Nominatim

    coords_ticket = _geocode(adresse_ticket)
    if not coords_ticket:
        return None

    try:
        # OSRM attend lon,lat (ordre inverse)
        lat1, lon1 = coords_labo
        lat2, lon2 = coords_ticket
        url = f"{OSRM_URL}/{lon1},{lat1};{lon2},{lat2}"
        params = {"overview": "false"}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if data.get("code") == "Ok":
            metres = data["routes"][0]["distance"]
            return round(metres / 1000, 1)
    except Exception:
        pass

    return None
