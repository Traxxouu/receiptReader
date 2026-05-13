import time
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "receiptReader/1.0 (stage-project)"}


def valider_adresse(numero: str, nom_rue: str, code_postal: str, ville: str | None = None) -> dict:
    """
    Stratégie en cascade :
    1. Numéro + rue + code postal + ville si disponible
    2. Numéro + rue + code postal
    3. Rue + code postal + ville si disponible
    4. Rue + code postal (sans numéro)
    5. Code postal seul → au moins la ville
    """
    result = {
        "adresse_validee": None,
        "ville": None,
        "latitude": None,
        "longitude": None,
        "confiance": "non trouvée",
        "mode": None,
    }

    # Tentative 1 : adresse complète
    if numero and nom_rue and code_postal and ville:
        query = f"{numero} {nom_rue}, {code_postal} {ville}, France"
        res = _query(query)
        if res:
            result.update(res)
            result["mode"] = "adresse complète"
            return result
        time.sleep(1)

    if numero and nom_rue and code_postal:
        query = f"{numero} {nom_rue}, {code_postal}, France"
        res = _query(query)
        if res:
            result.update(res)
            result["mode"] = "adresse complète"
            return result
        time.sleep(1)

    # Tentative 2 : rue + code postal
    if nom_rue and code_postal and ville:
        query = f"{nom_rue}, {code_postal} {ville}, France"
        res = _query(query)
        if res:
            result.update(res)
            result["mode"] = "rue + code postal"
            return result
        time.sleep(1)

    if nom_rue and code_postal:
        query = f"{nom_rue}, {code_postal}, France"
        res = _query(query)
        if res:
            result.update(res)
            result["mode"] = "rue + code postal"
            return result
        time.sleep(1)

    # Tentative 3 : code postal seul → déduit la ville
    if code_postal and ville:
        query = f"{code_postal} {ville}, France"
        res = _query(query)
        if res:
            result.update(res)
            result["mode"] = "code postal + ville"
            return result
        time.sleep(1)

    if code_postal:
        query = f"{code_postal}, France"
        res = _query(query)
        if res:
            result.update(res)
            result["mode"] = "code postal uniquement"
            return result
        time.sleep(1)

    return result


def _query(query: str) -> dict | None:
    try:
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": 1,
            "countrycodes": "fr",
        }
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data:
            top = data[0]
            importance = float(top.get("importance", 0))
            # Extraire la ville depuis addressdetails
            addr = top.get("address", {})
            ville = (addr.get("city") or addr.get("town") or
                     addr.get("village") or addr.get("municipality") or "")
            return {
                "adresse_validee": top.get("display_name"),
                "ville": ville,
                "latitude": top.get("lat"),
                "longitude": top.get("lon"),
                "confiance": "haute" if importance > 0.5 else "moyenne",
            }
    except Exception:
        pass
    time.sleep(1)
    return None
