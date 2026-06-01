import re
import time
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
HEADERS = {"User-Agent": "receiptReader/1.0 (stage-project)"}

_geocode_cache: dict[str, tuple[float, float] | None] = {}


def _geocode_raw(adresse: str) -> tuple[float, float] | None:
    try:
        params = {"q": adresse, "format": "json", "limit": 1, "countrycodes": "fr"}
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    finally:
        time.sleep(1)  # rate limit Nominatim (1 req/s)
    return None


def _geocode(adresse: str) -> tuple[float, float] | None:
    key = adresse.strip().lower()
    if key in _geocode_cache:          # labo + adresses deja vues : zero appel reseau
        return _geocode_cache[key]

    coords = _geocode_raw(adresse)
    if coords is None:                 # fallback : code postal + ville
        m = re.search(r"(\d{5})[\s,]+([A-Za-zÀ-ÿ' \-]+)", adresse)
        if m:
            coords = _geocode_raw(f"{m.group(1)} {m.group(2).strip()}")

    _geocode_cache[key] = coords
    return coords


def calculer_distance(adresse_labo: str, adresse_ticket: str) -> float | None:
    coords_labo = _geocode(adresse_labo)
    if not coords_labo:
        return None
    coords_ticket = _geocode(adresse_ticket)
    if not coords_ticket:
        return None
    try:
        lat1, lon1 = coords_labo
        lat2, lon2 = coords_ticket
        url = f"{OSRM_URL}/{lon1},{lat1};{lon2},{lat2}"
        r = requests.get(url, params={"overview": "false"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("code") == "Ok":
            return round(data["routes"][0]["distance"] / 1000, 1)
    except Exception:
        pass
    return None