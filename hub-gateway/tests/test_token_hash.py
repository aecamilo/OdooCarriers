from app.services.token_service import generate_api_token, hash_token


def test_generate_api_token_length():
    token = generate_api_token()
    assert len(token) >= 32


def test_hash_token_deterministic():
    h1 = hash_token("same-token-value-here")
    h2 = hash_token("same-token-value-here")
    assert h1 == h2
    assert h1 != hash_token("other-token-value-here")
