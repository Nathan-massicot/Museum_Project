"""
DALL-E 3 client for the Future Transport museum exhibition.
Handles image generation, cost tracking, and file saving.
"""

import os
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OUTPUT_DIR = Path("output")

# DALL-E 3 pricing per image in USD
DALLE3_PRICING = {
    ("1024x1024", "standard"): 0.040,
    ("1024x1024", "hd"): 0.080,
    ("1024x1792", "standard"): 0.080,
    ("1024x1792", "hd"): 0.120,
    ("1792x1024", "standard"): 0.080,
    ("1792x1024", "hd"): 0.120,
}


def get_cost(size: str = "1024x1024", quality: str = "standard") -> float:
    """Return the estimated cost in USD for a DALL-E 3 generation."""
    return DALLE3_PRICING.get((size, quality), 0.0)


def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
) -> dict:
    """
    Generate an image with DALL-E 3.

    Returns a dict with keys:
        file_path: path to saved PNG
        revised_prompt: DALL-E's revised prompt
        cost: estimated cost in USD
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-REMPLACE"):
        raise ValueError("OPENAI_API_KEY not configured in .env")

    client = OpenAI(api_key=api_key)
    OUTPUT_DIR.mkdir(exist_ok=True)

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality=quality,
        n=1,
    )

    image_url = response.data[0].url
    revised_prompt = response.data[0].revised_prompt

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = OUTPUT_DIR / f"transport_{timestamp}.png"
    urllib.request.urlretrieve(image_url, str(filename))

    return {
        "file_path": str(filename),
        "revised_prompt": revised_prompt,
        "cost": get_cost(size, quality),
    }
