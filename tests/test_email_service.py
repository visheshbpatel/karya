import httpx
import pytest

import email_service


def test_send_otp_email_success(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "test-api-key")
    monkeypatch.setenv("BREVO_SENDER_EMAIL", "sender@example.com")
    monkeypatch.setenv("BREVO_SENDER_NAME", "Karya")

    def mock_post(url, json, headers, timeout):
        assert url == email_service.BREVO_API_URL
        assert json["to"] == [{"email": "user@example.com"}]
        assert json["sender"]["email"] == "sender@example.com"
        assert "123456" in json["textContent"]
        assert headers["api-key"] == "test-api-key"
        assert timeout == 10.0

        return httpx.Response(
            201,
            json={"messageId": "test-message-id"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(email_service.httpx, "post", mock_post)

    email_service.send_otp_email("user@example.com", "123456")


def test_send_otp_email_missing_configuration(monkeypatch):
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.delenv("BREVO_SENDER_EMAIL", raising=False)

    with pytest.raises(RuntimeError, match="configuration is missing"):
        email_service.send_otp_email("user@example.com", "123456")


def test_send_otp_email_api_error(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "test-api-key")
    monkeypatch.setenv("BREVO_SENDER_EMAIL", "sender@example.com")

    def mock_post(url, json, headers, timeout):
        return httpx.Response(
            401,
            json={"message": "Unauthorized"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(email_service.httpx, "post", mock_post)

    with pytest.raises(httpx.HTTPStatusError):
        email_service.send_otp_email("user@example.com", "123456")
