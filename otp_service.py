import secrets
from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    return password_hash.hash(otp)


def verify_otp(otp: str, otp_hash: str) -> bool:
    return password_hash.verify(otp, otp_hash)


def get_otp_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=10)
