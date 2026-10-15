import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_otp_email(to_email: str, otp: str) -> None:
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")
    sender_name = os.getenv("BREVO_SENDER_NAME", "Karya")

    if not api_key or not sender_email:
        raise RuntimeError("Brevo email configuration is missing")

    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email,
        },
        "to": [{"email": to_email}],
        "subject": "Verify your Karya email",
        "textContent": (
            f"Your Karya verification code is {otp}.\n\n"
            "This code expires in 10 minutes. "
            "If you did not request it, you can ignore this email."
        ),
    }

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    response = httpx.post(
        BREVO_API_URL,
        json=payload,
        headers=headers,
        timeout=10.0,
    )
    response.raise_for_status()



def send_password_reset_email(to_email: str, otp: str) -> None:
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")
    sender_name = os.getenv("BREVO_SENDER_NAME", "Karya")

    if not api_key or not sender_email:
        raise RuntimeError("Brevo email configuration is missing")

    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email,
        },
        "to": [{"email": to_email}],
        "subject": "Reset your Karya password",
        "textContent": (
            f"Your Karya password-reset code is {otp}.\n\n"
            "This code expires in 10 minutes. "
            "If you did not request a password reset, "
            "you can ignore this email."
        ),
    }

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    response = httpx.post(
        BREVO_API_URL,
        json=payload,
        headers=headers,
        timeout=10.0,
    )
    response.raise_for_status()
