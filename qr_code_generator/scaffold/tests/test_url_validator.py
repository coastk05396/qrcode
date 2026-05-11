import pytest

from app.url_validator import MAX_URL_LENGTH, validate_url


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        (" HTTP://Example.COM:80/path/?b=2&a=1 ", "https://example.com/path?a=1&b=2"),
        ("https://Example.COM:443/", "https://example.com"),
        ("http://example.com:8080/a/b/", "https://example.com:8080/a/b"),
        ("http://[2001:db8::1]:8080/path/", "https://[2001:db8::1]:8080/path"),
    ],
)
def test_validate_url_normalizes_valid_http_urls(raw_url, expected):
    assert validate_url(raw_url) == expected


@pytest.mark.parametrize(
    ("raw_url", "message"),
    [
        ("", "URL is required"),
        ("   ", "URL is required"),
        ("ftp://example.com", "URL must use http or https"),
        ("https:///missing-host", "URL must include a hostname"),
        ("https://EVIL.com/login", "URL domain is blocked"),
        (f"https://example.com/{'a' * MAX_URL_LENGTH}", "URL exceeds maximum length"),
    ],
)
def test_validate_url_rejects_invalid_or_blocked_urls(raw_url, message):
    with pytest.raises(ValueError, match=message):
        validate_url(raw_url)
