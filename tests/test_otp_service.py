from otp_service import (
    generate_otp,
    hash_otp,
    verify_otp,
    get_otp_expiry,
)
from datetime import datetime, timezone, timedelta


def test_generate_otp_returns_six_digits():
    otp = generate_otp()

    assert len(otp) == 6
    assert otp.isdigit()


def test_generate_otp_preserves_leading_zeros():
    otp = "004281"

    assert len(otp) == 6
    assert otp.isdigit()


def test_hash_otp_does_not_store_plain_text():
    otp = "123456"
    otp_hash = hash_otp(otp)

    assert otp_hash != otp
    assert verify_otp(otp, otp_hash)


def test_verify_otp_rejects_wrong_code():
    otp_hash = hash_otp("123456")

    assert not verify_otp("654321", otp_hash)


def test_otp_expiry_is_ten_minutes_ahead():
    before = datetime.now(timezone.utc)
    expiry = get_otp_expiry()
    after = datetime.now(timezone.utc)

    assert before + timedelta(minutes=10) <= expiry
    assert expiry <= after + timedelta(minutes=10)
