"""
Test de connexion à l'API OpenAI - Génération DALL-E 3
Vérifie que la clé API fonctionne et estime le coût par image.
"""

import os
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Coûts DALL-E 3 par image (en USD)
DALLE3_PRICING = {
    ("1024x1024", "standard"): 0.040,
    ("1024x1024", "hd"): 0.080,
    ("1024x1792", "standard"): 0.080,
    ("1024x1792", "hd"): 0.120,
    ("1792x1024", "standard"): 0.080,
    ("1792x1024", "hd"): 0.120,
}


def test_dalle(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
) -> str | None:
    """Génère une image avec DALL-E 3 et retourne le chemin du fichier sauvegardé."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-REMPLACE"):
        print("ERREUR : Configure ta clé API dans le fichier .env")
        return None

    client = OpenAI(api_key=api_key)

    cost = DALLE3_PRICING.get((size, quality), "inconnu")
    print(f"Modèle   : DALL-E 3")
    print(f"Taille   : {size}")
    print(f"Qualité  : {quality}")
    print(f"Coût est.: ${cost}")
    print(f"Prompt   : {prompt}")
    print()
    print("Génération en cours...")

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality=quality,
        n=1,
    )

    image_url = response.data[0].url
    revised_prompt = response.data[0].revised_prompt

    print(f"Image générée !")
    print(f"Prompt révisé par DALL-E : {revised_prompt}")

    # Sauvegarder l'image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = str(OUTPUT_DIR / f"test_{timestamp}.png")
    urllib.request.urlretrieve(image_url, filename)
    print(f"Image sauvegardée : {filename}")
    print()
    print(f"Coût de cette génération : ${cost}")

    return filename


if __name__ == "__main__":
    print("=" * 50)
    print("TEST API OpenAI - DALL-E 3")
    print("=" * 50)
    print()

    test_dalle(
        prompt="A futuristic electric tramway gliding through a European city center, "
        "with solar-powered overhead lines and green vegetation integrated into the tracks, "
        "photorealistic, golden hour lighting",
    )
