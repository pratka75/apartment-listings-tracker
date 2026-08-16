"""
Send the digest via Gmail SMTP using an app password.

Credentials come from the environment / .env (see secrets_env.py); the recipient
comes from config.local.json. Nothing is hard-coded, printed, or logged.

Generate an App Password at https://myaccount.google.com/apppasswords
(requires 2-Step Verification on the Google account).
"""

import re
import smtplib
import ssl
from email.message import EmailMessage

from config import get_config
from secrets_env import get_secret

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _single_line(value: str) -> str:
    """Strip CR/LF so header values can't be used for SMTP header injection."""
    return value.replace("\r", "").replace("\n", "").strip()


def _recipients(raw: str) -> list[str]:
    """Parse one or more comma-separated recipient addresses; validate each.
    CR/LF are neutralized first, so a header-injection attempt yields an invalid
    address and is rejected rather than adding a hidden Bcc."""
    flat = raw.replace("\r", " ").replace("\n", " ")
    parts = [p.strip() for p in flat.split(",") if p.strip()]
    bad = [p for p in parts if not _EMAIL_RE.match(p)]
    if not parts or bad:
        raise SystemExit(f"Invalid recipient address(es): {bad or 'none provided'}")
    return parts


def send(subject: str, html_body: str, to: str | None = None) -> None:
    sender = _single_line(get_secret("GMAIL_SENDER"))
    # App passwords are displayed with spaces for readability; Gmail accepts them without.
    app_password = get_secret("GMAIL_APP_PASSWORD").replace(" ", "")
    # Recipient resolution (so it need not sit in a public repo). Any of these may
    # be a single address or several comma-separated:
    #   explicit arg -> DIGEST_RECIPIENT env -> config email.recipient -> sender itself
    raw = (to or get_secret("DIGEST_RECIPIENT", required=False)
           or get_config().get("email", {}).get("recipient") or sender)
    recipients = _recipients(raw)

    msg = EmailMessage()
    msg["Subject"] = _single_line(subject)
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content("This digest is best viewed as HTML.")
    msg.add_alternative(html_body, subtype="html")

    ctx = ssl.create_default_context()
    try:
        # Preferred: implicit TLS on 465.
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=30) as server:
            server.login(sender, app_password)
            server.send_message(msg, from_addr=sender, to_addrs=recipients)
    except OSError:
        # Some sandboxes block 465; fall back to STARTTLS on 587.
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls(context=ctx)
            server.login(sender, app_password)
            server.send_message(msg, from_addr=sender, to_addrs=recipients)
    print(f"Email sent to {len(recipients)} recipient(s).")


if __name__ == "__main__":
    send("Apartment tracker — SMTP test",
         "<p>✅ Gmail app-password delivery is working.</p>")
