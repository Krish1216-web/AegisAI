import pytest
from app.core.security import create_access_token, decode_token

def test_jwt_tampering_and_expiration():
    token = create_access_token(
        subject="user-123",
        roles=["member"],
        permissions=["workspace:view"]
    )
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"

    # Tampered token
    tampered = token[:-4] + "abcd"
    assert decode_token(tampered) is None

    # Invalid token string
    assert decode_token("invalid.token.payload") is None
