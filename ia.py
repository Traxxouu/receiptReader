import os
import requests
import shutil
import subprocess


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"
MODEL = "llama3.2"

PROMPT_TEMPLATE = """Tu es un assistant qui extrait des adresses postales depuis du texte OCR de tickets de caisse.

Voici le texte extrait d'un ticket de caisse :
---
{text}
---

Extrait l'adresse postale complète du commerce (numéro de rue, nom de rue, code postal, ville).
Réponds UNIQUEMENT avec l'adresse sur une seule ligne, sans explication.
Si tu ne trouves pas d'adresse, réponds exactement : NON_TROUVE

Exemples de réponses attendues :
31 RUE DE CHEVREUSE, 78310 MAUREPAS
10 AVENUE JOHANNES GUTEN, 78310 MAUREPAS
NON_TROUVE
"""


def extraire_adresse_ia(texte_brut: str) -> str | None:
    """
    Envoie le texte brut OCR a Ollama et lui demande d'extraire l'adresse.
    Retourne l'adresse sous forme de string, ou None si non trouvee.
    """
    if not texte_brut or len(texte_brut.strip()) < 10:
        return None

    prompt = PROMPT_TEMPLATE.format(text=texte_brut[:2000])  # limite le texte

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,       # reponse deterministe
                    "num_predict": 100,     # adresse courte, pas besoin de plus
                }
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        adresse = data.get("response", "").strip()

        if not adresse or adresse == "NON_TROUVE" or len(adresse) < 5:
            return None

        return adresse

    except requests.exceptions.ConnectionError:
        raise RuntimeError("Ollama n'est pas lance. Demarre-le avec : ollama serve")
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        if status == 404:
            raise RuntimeError(
                f"Ollama a repondu 404 sur {OLLAMA_URL}. Verifie que le serveur Ollama tourne bien sur localhost:11434 et que OLLAMA_HOST n'est pas mal configure."
            )
        raise RuntimeError(f"Erreur Ollama HTTP {status or ''}: {e}")
    except Exception as e:
        raise RuntimeError(f"Erreur Ollama : {e}")


def ollama_server_reachable() -> bool:
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def ollama_model_exists(model_name: str = MODEL) -> bool:
    target = model_name.strip().lower()
    target_base = target.split(":", 1)[0]

    response = requests.get(OLLAMA_TAGS_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    models = data.get("models", [])

    for model in models:
        # Ollama can expose `name` as `llama3.2:latest` even if user requests `llama3.2`.
        raw = (model.get("name") or model.get("model") or "").strip().lower()
        if not raw:
            continue

        raw_base = raw.split(":", 1)[0]
        if raw == target or raw_base == target_base:
            return True

    return False


def ollama_pull_model(model_name: str = MODEL) -> None:
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        raise RuntimeError("La commande 'ollama' est introuvable. Installe Ollama puis reessaie.")

    result = subprocess.run(
        [ollama_bin, "pull", model_name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(stderr or f"Impossible de telecharger le modele {model_name}.")
