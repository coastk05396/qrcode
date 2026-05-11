import string

import pytest

from app import token_gen


def test_base62_encode_handles_zero_and_multi_digit_values():
    assert token_gen.base62_encode(b"\x00") == token_gen.BASE62_CHARS[0]
    assert token_gen.base62_encode(b"\x3d") == "9"
    assert token_gen.base62_encode(b"\x3e") == "ba"


def test_generate_token_retries_until_unique(monkeypatch):
    calls = []
    tokens = iter(["collision", "unique-token"])

    monkeypatch.setattr(token_gen, "base62_encode", lambda digest: next(tokens))

    def fake_exists(db, token):
        calls.append((db, token))
        return token == "collisi"

    monkeypatch.setattr(token_gen, "token_exists_in_db", fake_exists)

    db = object()

    assert token_gen.generate_token("https://example.com", db) == "unique-"
    assert calls == [(db, "collisi"), (db, "unique-")]


def test_generate_token_returns_url_safe_fixed_length_token(monkeypatch):
    monkeypatch.setattr(token_gen, "token_exists_in_db", lambda db, token: False)

    token = token_gen.generate_token("https://example.com", object())

    assert len(token) == token_gen.TOKEN_LENGTH
    assert set(token) <= set(string.ascii_letters + string.digits)


def test_generate_token_raises_when_retry_limit_is_exhausted(monkeypatch):
    monkeypatch.setattr(token_gen, "base62_encode", lambda digest: "collision")
    monkeypatch.setattr(token_gen, "token_exists_in_db", lambda db, token: True)

    with pytest.raises(RuntimeError, match="Unable to generate a unique token"):
        token_gen.generate_token("https://example.com", object())
