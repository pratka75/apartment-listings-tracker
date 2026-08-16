"""
Send the digest via Gmail SMTP using an app password.

Credentials come from the environment / .env (see secrets_env.py); the recipient
comes from config.local.json. Nothing is hard-coded, printed, or logged.

Generate an App Password at https://myaccount.google.com/apppasswords
(requires 2-Step Verification on the Google account).
"""

import smtplib
import ssl
from email.message import EmailMessage

from config import get_config
from secrets_env import get_secret


def _single_line(value: str) -> str:
    """Strip CR/LF so header values can't be used for SMTP header injection."""
    return value.replace("\r", "").replace("\n", "").strip()


def send(subject: str, html_body: str, to: str | None = None) -> None:
    sender = _single_line(get_secret("GMAIL_SENDER"))
    # App passwords are displayed with spaces for readability; Gmail accepts them without.
    app_password = get_secret("GMAIL_APP_PASSWORD").replace(" ", "")
    to = _single_line(to or get_config()["email"]["recipient"])

    msg = EmailMessage()
    msg["Subject"] = _single_line(subject)
    msg["From"] = sender
    msg["To"] = to
    msg.set_content("This digest is best viewed as HTML.")
    msg.add_alternative(html_body, subtype="html")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
        server.login(sender, app_password)
        server.send_message(msg)
    print(f"Email sent to {to}.")


if __name__ == "__main__":
    send("Apartment tracker — SMTP test",
         "<p>✅ Gmail app-password delivery is working.</p>")
