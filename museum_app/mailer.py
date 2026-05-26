"""
Email sender for the museum kiosk: delivers the generated image to the
visitor's address via Gmail SMTP (or any SMTP provider).

Configuration (.env or Streamlit secrets):
    SMTP_USER      Gmail address (required)
    SMTP_PASSWORD  Gmail App Password — 16 characters, no spaces (required)
    SMTP_FROM      optional, defaults to SMTP_USER
    SMTP_HOST      optional, defaults to smtp.gmail.com
    SMTP_PORT      optional, defaults to 587 (STARTTLS)
    SMTP_USE_SSL   "1" to use SMTP_SSL on port 465; otherwise STARTTLS

See EMAIL_SETUP.md for the full Gmail account setup procedure.
"""

import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Display name shown to recipients; a named sender is trusted more than a
# bare address and improves inbox placement.
SENDER_NAME = "Future Transport — Bienne/Biel 2075"


def _get_secret(key: str, default: str = "") -> str:
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


EMAIL_TEMPLATES = {
    "fr": {
        "subject": "Votre vision du Zentralplatz en 2075",
        "body": (
            "Bonjour,\n\n"
            "Merci d'avoir visité l'exposition Future Transport — "
            "Bienne / Biel 2075.\n"
            "Voici, en pièce jointe, votre vision du Zentralplatz dans "
            "50 ans.\n\n"
            "Bonne découverte !\n"
        ),
    },
    "de": {
        "subject": "Ihre Vision des Zentralplatzes im Jahr 2075",
        "body": (
            "Guten Tag,\n\n"
            "Vielen Dank für Ihren Besuch der Ausstellung Future "
            "Transport — Biel / Bienne 2075.\n"
            "Anbei finden Sie Ihre Vision des Zentralplatzes in "
            "50 Jahren.\n\n"
            "Viel Spass beim Entdecken!\n"
        ),
    },
    "en": {
        "subject": "Your vision of the Zentralplatz in 2075",
        "body": (
            "Hello,\n\n"
            "Thank you for visiting the Future Transport — "
            "Bienne / Biel 2075 exhibition.\n"
            "Attached is your vision of the Zentralplatz in 50 years.\n\n"
            "Enjoy!\n"
        ),
    },
}


def _build_html(body: str, image_cid: str) -> str:
    """Render the plain-text body as a styled HTML email with the image
    shown inline (referenced by Content-ID)."""
    paragraphs = "".join(
        f'<p style="margin:0 0 1em 0;">{p.strip().replace(chr(10), "<br>")}</p>'
        for p in body.strip().split("\n\n")
        if p.strip()
    )
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:24px;background:#f4f6f8;
               font-family:Arial,Helvetica,sans-serif;color:#222;">
    <div style="max-width:600px;margin:0 auto;background:#ffffff;
                border-radius:12px;padding:28px;">
      <div style="font-size:15px;line-height:1.5;">{paragraphs}</div>
      <img src="cid:{image_cid}" alt="{SENDER_NAME}"
           style="width:100%;border-radius:8px;margin-top:8px;"/>
      <p style="font-size:12px;color:#8a93a0;margin-top:20px;border-top:
                1px solid #eceff2;padding-top:12px;">{SENDER_NAME}</p>
    </div>
  </body>
</html>"""


def is_configured() -> bool:
    """True if SMTP credentials are set and non-empty."""
    return bool(
        _get_secret("SMTP_USER")
        and _get_secret("SMTP_PASSWORD")
    )


def send_image_email(to_email: str, image_path: str, lang: str = "fr") -> None:
    """
    Send the generated image to the visitor.
    Raises RuntimeError if SMTP is not configured, smtplib.SMTPException
    on transport errors.
    """
    host = _get_secret("SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com"
    port_raw = _get_secret("SMTP_PORT", "587") or "587"
    port = int(port_raw)
    user = _get_secret("SMTP_USER")
    password = _get_secret("SMTP_PASSWORD")
    sender = _get_secret("SMTP_FROM") or user
    use_ssl = _get_secret("SMTP_USE_SSL", "0").strip() in ("1", "true", "True")

    if not (user and password):
        raise RuntimeError(
            "SMTP not configured. Set SMTP_USER and SMTP_PASSWORD in .env."
        )

    password = password.replace(" ", "")

    template = EMAIL_TEMPLATES.get(lang, EMAIL_TEMPLATES["fr"])
    sender_domain = sender.split("@")[-1] or "gmail.com"

    msg = EmailMessage()
    msg["From"] = formataddr((SENDER_NAME, sender))
    msg["To"] = to_email
    msg["Reply-To"] = sender
    msg["Subject"] = template["subject"]
    # Well-formed Date and Message-ID reduce the odds of being flagged.
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender_domain)
    # A List-Unsubscribe header lowers the spam score for automated mail.
    msg["List-Unsubscribe"] = f"<mailto:{sender}?subject=unsubscribe>"

    # Plain-text part (fallback) + HTML alternative with the image inline.
    msg.set_content(template["body"])

    img_path = Path(image_path)
    if img_path.exists():
        image_bytes = img_path.read_bytes()
        image_cid = make_msgid(domain=sender_domain)
        msg.add_alternative(
            _build_html(template["body"], image_cid[1:-1]),
            subtype="html",
        )
        # Embed the image inside the HTML part (multipart/related).
        msg.get_payload()[1].add_related(
            image_bytes, maintype="image", subtype="png", cid=image_cid
        )
        # Also attach it so the visitor can download/keep the souvenir.
        msg.add_attachment(
            image_bytes,
            maintype="image",
            subtype="png",
            filename=img_path.name,
        )

    if use_ssl:
        with smtplib.SMTP_SSL(host, port) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(msg)
