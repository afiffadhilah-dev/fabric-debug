"""URL building and normalization utilities."""

from urllib.parse import urlunparse, urlparse


def normalize_host(host: str) -> str:
    """
    Normalize host string by removing scheme, port, and trailing slashes.
    
    Args:
        host: Raw host string (can include http://, https://, trailing slash, etc.)
    
    Returns:
        Clean hostname only (e.g., 'localhost', '127.0.0.1', 'api.example.com')
    
    Examples:
        - normalize_host('http://127.0.0.1') -> '127.0.0.1'
        - normalize_host('https://api.example.com/') -> 'api.example.com'
        - normalize_host('localhost:3000') -> 'localhost'
        - normalize_host('127.0.0.1') -> '127.0.0.1'
    """
    # Remove leading/trailing whitespace
    host = host.strip()
    
    # If it looks like a URL, parse it
    if "://" in host:
        parsed = urlparse(host)
        host = parsed.hostname or parsed.netloc
    
    # Remove port if present (e.g., 'localhost:3000' -> 'localhost')
    if ":" in host and not host.startswith("["):  # Ignore IPv6 addresses with []
        host = host.split(":")[0]
    
    # Remove trailing slash
    host = host.rstrip("/")
    
    return host


def build_api_url(host: str, port: int) -> str:
    """
    Build normalized API URL based on host and port.
    
    Handles standard ports (80 for HTTP, 443 for HTTPS) by excluding them from URL.
    Automatically normalizes host input (removes scheme, port, trailing slashes).
    
    Args:
        host: API host - can be in any format (see examples)
        port: API port (80, 443, 8000, etc.)
    
    Returns:
        Properly formatted URL without redundant port numbers.
    
    Examples:
        - build_api_url('localhost', 8000) -> 'http://localhost:8000'
        - build_api_url('localhost', 80) -> 'http://localhost'
        - build_api_url('api.example.com', 443) -> 'https://api.example.com'
        - build_api_url('http://127.0.0.1', 8000) -> 'http://127.0.0.1:8000'
        - build_api_url('https://api.example.com/', 443) -> 'https://api.example.com'
    """
    # Normalize the host first
    clean_host = normalize_host(host)
    
    # Determine scheme based on port
    scheme = "https" if port == 443 else "http"
    
    # Omit port from netloc if it's a standard port
    netloc = clean_host if port in (80, 443) else f"{clean_host}:{port}"
    
    return urlunparse((scheme, netloc, "", "", "", ""))
