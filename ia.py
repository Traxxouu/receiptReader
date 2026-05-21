import requests
import json


OLLAMA_URL = "http://localhost:11434/api/generate"
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
    except Exception as e:
        raise RuntimeError(f"Erreur Ollama : {e}")
