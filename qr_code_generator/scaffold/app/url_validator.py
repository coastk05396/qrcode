import ipaddress
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

MAX_URL_LENGTH = 2048

# Example blocklist for the exercise. In a real app this would live in config or a service.
BLOCKED_DOMAINS = {
    "evil.com",
    "malware.example.com",
    "phishing.example.com",
}


def is_blocked_domain(hostname: str | None) -> bool:
    if hostname is None:
        return True
    return hostname.lower() in BLOCKED_DOMAINS


def validate_url(url: str) -> str:
    """Format check, normalization, and blocklist validation."""
    # Scaffold TODO reference:
    # 1. Validate the raw input: required, size-limited, http/https only, hostname present.
    # 2. Reject blocked domains before generating a token for them.
    # 3. Normalize the URL so equivalent destinations map to the same stored value.
    candidate = url.strip()
    if not candidate:
        raise ValueError("URL is required")
    if len(candidate) > MAX_URL_LENGTH:
        raise ValueError(f"URL exceeds maximum length of {MAX_URL_LENGTH}")

    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("URL must use http or https")
    if parsed.hostname is None:
        raise ValueError("URL must include a hostname")
    if is_blocked_domain(parsed.hostname):
        raise ValueError("URL domain is blocked")

    # Normalize host/port/path/query to reduce duplicate logical URLs.
    host = parsed.hostname.lower()
    port = parsed.port
    if port in {80, 443}:
        port = None

    try:
        ipaddress.IPv6Address(host)
        normalized_host = f"[{host}]"
    except ValueError:
        normalized_host = host
    netloc = normalized_host if port is None else f"{normalized_host}:{port}"
    path = parsed.path.rstrip("/")
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)), doseq=True)

    return urlunparse(("https", netloc, path, "", query, ""))
