"""
gpt-image-2 client (with gpt-image-1.5 fallback) for the Future Transport
museum exhibition. Handles image editing, token tracking, and file saving.
"""

import base64
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    """Get a secret from st.secrets (Streamlit Cloud) or os.getenv (local .env)."""
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

OUTPUT_DIR = Path(__file__).parent.parent / "output"

PRIMARY_MODEL = "gpt-image-2"
FALLBACK_MODEL = "gpt-image-1.5"

# Token pricing per 1M tokens (USD), keyed by model
PRICING = {
    "gpt-image-2": {
        "text_input": 5.0 / 1_000_000,
        "image_input": 8.0 / 1_000_000,
        "image_input_cached": 2.0 / 1_000_000,
        "text_output": 10.0 / 1_000_000,
        "image_output": 30.0 / 1_000_000,
    },
    "gpt-image-1.5": {
        "text_input": 5.0 / 1_000_000,
        "image_input": 8.0 / 1_000_000,
        "image_input_cached": 2.0 / 1_000_000,
        "text_output": 10.0 / 1_000_000,
        "image_output": 32.0 / 1_000_000,
    },
}


def compute_cost(usage, model: str = PRIMARY_MODEL) -> float:
    """Return the cost in USD based on detailed token usage and model."""
    rates = PRICING.get(model, PRICING[PRIMARY_MODEL])

    text_in = getattr(usage, "input_tokens", 0)
    in_details = getattr(usage, "input_tokens_details", None)
    image_in_tokens = getattr(in_details, "image_tokens", 0) if in_details else 0
    cached_image_in_tokens = getattr(in_details, "cached_tokens", 0) if in_details else 0
    image_in_tokens = max(image_in_tokens - cached_image_in_tokens, 0)
    text_in_tokens = max(text_in - image_in_tokens - cached_image_in_tokens, 0)

    text_out = getattr(usage, "output_tokens", 0)
    out_details = getattr(usage, "output_tokens_details", None)
    image_out_tokens = getattr(out_details, "image_tokens", 0) if out_details else 0
    text_out_tokens = max(text_out - image_out_tokens, 0)

    return (
        text_in_tokens * rates["text_input"]
        + image_in_tokens * rates["image_input"]
        + cached_image_in_tokens * rates["image_input_cached"]
        + text_out_tokens * rates["text_output"]
        + image_out_tokens * rates["image_output"]
    )


def _call_api(client: OpenAI, model: str, prompt: str, source_image: str | None,
              size: str, quality: str):
    """Issue a single edit/generate call against the given model."""
    if source_image and Path(source_image).exists():
        with open(source_image, "rb") as img_file:
            return client.images.edit(
                model=model,
                image=img_file,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
    return client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
        quality=quality,
        n=1,
    )


def generate_image(
    prompt: str,
    source_image: str | None = None,
    size: str = "1024x1024",
    quality: str = "low",
) -> dict:
    """
    Edit or generate an image with gpt-image-2, falling back to gpt-image-1.5
    if the primary model is unavailable.

    Returns a dict with keys:
        file_path: path to saved PNG
        cost: cost in USD based on token usage
        input_tokens: number of input tokens used
        output_tokens: number of output tokens used
        model: model that actually produced the image
    """
    api_key = _get_secret("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-REMPLACE"):
        raise ValueError("OPENAI_API_KEY not configured in .env or Streamlit secrets")

    client = OpenAI(api_key=api_key)
    OUTPUT_DIR.mkdir(exist_ok=True)

    model_used = PRIMARY_MODEL
    try:
        response = _call_api(
            client, PRIMARY_MODEL, prompt, source_image, size, quality
        )
    except Exception as primary_err:
        try:
            response = _call_api(
                client, FALLBACK_MODEL, prompt, source_image, size, quality
            )
            model_used = FALLBACK_MODEL
        except Exception as fallback_err:
            raise RuntimeError(
                f"Both models failed. {PRIMARY_MODEL}: {primary_err}. "
                f"{FALLBACK_MODEL}: {fallback_err}"
            ) from fallback_err

    image_b64 = response.data[0].b64_json
    usage = response.usage
    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = OUTPUT_DIR / f"transport_{timestamp}.png"
    filename.write_bytes(base64.b64decode(image_b64))

    return {
        "file_path": str(filename),
        "cost": compute_cost(usage, model_used),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model": model_used,
    }
