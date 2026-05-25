import pytest
from app.core.security import create_access_token, verify_token, hash_api_key, verify_api_key


def test_create_and_verify_token():
    token = create_access_token(data={"sub": "user:1"})
    payload = verify_token(token)
    assert payload["sub"] == "user:1"


def test_verify_invalid_token():
    payload = verify_token("invalid-token")
    assert payload is None


def test_hash_and_verify_api_key():
    raw_key = "dk_test_abc123"
    hashed = hash_api_key(raw_key)
    assert verify_api_key(raw_key, hashed) is True
    assert verify_api_key("wrong_key", hashed) is False
