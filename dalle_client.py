"""
gpt-image-1.5 client for the Future Transport museum exhibition.
Handles image editing, token tracking, and file saving.
"""

import base64
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OUTPUT_DIR = Path("output")

# gpt-image-1.5 token pricing in USD
TOKEN_PRICE_TEXT_INPUT = 5.0 / 1_000_000    # $5 per 1M text input tokens
TOKEN_PRICE_IMAGE_INPUT = 8.0 / 1_000_000   # $8 per 1M image input tokens
TOKEN_PRICE_TEXT_OUTPUT = 10.0 / 1_000_000   # $10 per 1M text output tokens
TOKEN_PRICE_IMAGE_OUTPUT = 32.0 / 1_000_000  # $32 per 1M image output tokens


def compute_cost(usage) -> float:
    """Return the cost in USD based on detailed token usage."""
    text_in = getattr(usage, "input_tokens", 0)
    image_in = getattr(usage, "input_tokens_details", None)
    image_in_tokens = getattr(image_in, "image_tokens", 0) if image_in else 0
    text_in_tokens = text_in - image_in_tokens

    text_out = getattr(usage, "output_tokens", 0)
    image_out = getattr(usage, "output_tokens_details", None)
    image_out_tokens = getattr(image_out, "image_tokens", 0) if image_out else 0
    text_out_tokens = text_out - image_out_tokens

    return (
        text_in_tokens * TOKEN_PRICE_TEXT_INPUT
        + image_in_tokens * TOKEN_PRICE_IMAGE_INPUT
        + text_out_tokens * TOKEN_PRICE_TEXT_OUTPUT
        + image_out_tokens * TOKEN_PRICE_IMAGE_OUTPUT
    )


def generate_image(
    prompt: str,
    source_image: str | None = None,
    size: str = "1024x1024",
    quality: str = "low",
) -> dict:
    """
    Edit or generate an image with gpt-image-1.

    If source_image is provided, it is used as the base image to modify.
    Otherwise, generates from prompt only.

    Returns a dict with keys:
        file_path: path to saved PNG
        cost: cost in USD based on token usage
        input_tokens: number of input tokens used
        output_tokens: number of output tokens used
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-REMPLACE"):
        raise ValueError("OPENAI_API_KEY not configured in .env")

    client = OpenAI(api_key=api_key)
    OUTPUT_DIR.mkdir(exist_ok=True)

    if source_image and Path(source_image).exists():
        with open(source_image, "rb") as img_file:
            response = client.images.edit(
                model="gpt-image-1.5",
                image=img_file,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
    else:
        response = client.images.generate(
            model="gpt-image-1.5",
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )

    image_b64 = response.data[0].b64_json
    usage = response.usage
    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = OUTPUT_DIR / f"transport_{timestamp}.png"
    filename.write_bytes(base64.b64decode(image_b64))

    return {
        "file_path": str(filename),
        "cost": compute_cost(usage),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
