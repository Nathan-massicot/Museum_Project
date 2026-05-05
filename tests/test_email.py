"""
Quick SMTP smoke test.

Usage (from project root):
    uv run python tests/test_email.py recipient@example.com
    uv run python tests/test_email.py recipient@example.com de
    uv run python tests/test_email.py recipient@example.com en

Sends a sample Zentralplatz image to the given address using the SMTP
credentials defined in .env. Use this after configuring Gmail (see
EMAIL_SETUP.md) to verify everything works.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "museum_app"))

import mailer  # noqa: E402

STATIC_DIR = PROJECT_ROOT / "static"
SAMPLE_IMAGE = STATIC_DIR / "place_centrale_pavilion.jpg"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python test_email.py <recipient_email> [lang=fr|de|en]")
        return 1

    recipient = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) >= 3 else "fr"

    if not SAMPLE_IMAGE.exists():
        print(f"Sample image not found: {SAMPLE_IMAGE}")
        return 1

    if not mailer.is_configured():
        print(
            "SMTP not configured. Fill SMTP_USER and SMTP_PASSWORD in .env "
            "(see EMAIL_SETUP.md)."
        )
        return 1

    print(f"Sending {SAMPLE_IMAGE.name} → {recipient} (lang={lang})…")
    try:
        mailer.send_image_email(recipient, str(SAMPLE_IMAGE), lang=lang)
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 2

    print("OK — check the inbox (and the Spam folder).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
