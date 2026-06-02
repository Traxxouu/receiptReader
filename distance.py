import re
import time
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
HEADERS = {"User-Agent": "receiptReader/1.0 (stage-project)"}

DISTANCE_SUSPECTE_KM = 150  # au-dela -> "a verifier". Ajuste selon le rayon du labo.

_geocode_cache: dict = {}


def _geocode_raw(adresse: str) -> dict | None:
    """Un seul appel reseau. Renvoie lat/lon/postcode ou None."""
    try:
        params = {"q": adresse, "format": "json", "limit": 1,
                  "countrycodes": "fr", "addressdetails": 1}
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data:
            top = data[0]
            addr = top.get("address", {})
            return {
                "lat": float(top["lat"]),
                "lon": float(top["lon"]),
                "postcode": (addr.get("postcode") or "").strip(),
            }
    except Exception:
        pass
    finally:
        time.sleep(1)  # rate limit Nominatim (1 req/s)
    return None


def _geocode(adresse: str) -> tuple[dict | None, bool]:
    """Renvoie (geo, fallback_utilise). Cache -> le labo n'est geocode qu'une fois."""
    key = adresse.strip().lower()
    if key in _geocode_cache:
        return _geocode_cache[key]

    geo = _geocode_raw(adresse)
    fallback = False
    if geo is None:  # fallback : code postal + ville
        m = re.search(r"(\d{5})[\s,]+([A-Za-zÀ-ÿ' \-]+)", adresse)
        if m:
            geo = _geocode_raw(f"{m.group(1)} {m.group(2).strip()}")
            fallback = geo is not None

    result = (geo, fallback)
    _geocode_cache[key] = result
    return result


def _confiance(adresse_ticket: str, geo: dict | None, fallback: bool, dist_km) -> str:
    """haute (vert) / moyenne (orange) / basse (rouge). Pur calcul local, 0 reseau."""
    if geo is None or dist_km is None:
        return "basse"
    if dist_km > DISTANCE_SUSPECTE_KM:
        return "moyenne"
    if fallback:
        return "moyenne"

    m = re.search(r"\b(\d{5})\b", adresse_ticket)
    cp_lu = m.group(1) if m else None
    cp_geo = geo.get("postcode") or ""

    if not cp_lu:
        return "moyenne"
    if cp_geo and cp_lu == cp_geo:
        return "haute"
    if cp_geo and cp_lu[:2] == cp_geo[:2]:
        return "moyenne"
    if cp_geo and cp_lu[:2] != cp_geo[:2]:
        return "moyenne"
    return "haute"


def calculer_distance(adresse_labo: str, adresse_ticket: str) -> tuple[float | None, str]:
    """Renvoie (distance_km | None, confiance)."""
    geo_labo, _ = _geocode(adresse_labo)
    if not geo_labo:
        return None, "basse"
    geo_ticket, fallback = _geocode(adresse_ticket)
    if not geo_ticket:
        return None, "basse"

    dist = None
    try:
        url = f"{OSRM_URL}/{geo_labo['lon']},{geo_labo['lat']};{geo_ticket['lon']},{geo_ticket['lat']}"
        r = requests.get(url, params={"overview": "false"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("code") == "Ok":
            dist = round(data["routes"][0]["distance"] / 1000, 1)
    except Exception:
        pass

    return dist, _confiance(adresse_ticket, geo_ticket, fallback, dist)
