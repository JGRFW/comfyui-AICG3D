# Copyright (C) 2026 AICG3D
# SPDX-License-Identifier: GPL-3.0-or-later
"""Network endpoint policy shared by the prompt optimizer backends."""

from __future__ import annotations

import ipaddress
import urllib.parse


OFFICIAL_API_HOSTS = frozenset(
    {
        "api.openai.com",
        "generativelanguage.googleapis.com",
        "openrouter.ai",
        "dashscope.aliyuncs.com",
        "api.siliconflow.cn",
        "www.runninghub.cn",
    }
)

_CREDENTIAL_QUERY_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "client_secret",
        "key",
        "passwd",
        "password",
        "secret",
        "sig",
        "signature",
        "token",
        "x_goog_api_key",
    }
)


def _query_key_name(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _normalized_hostname(parsed: urllib.parse.SplitResult) -> str:
    hostname = str(parsed.hostname or "").strip().lower().rstrip(".")
    if not hostname:
        raise ValueError("API URL must include a hostname")
    if " " in hostname or "\x00" in hostname:
        raise ValueError("API URL contains an invalid hostname")
    return hostname


def _is_loopback_host(hostname: str) -> bool:
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _is_private_ip_literal(hostname: str) -> bool:
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return bool(
        address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def sanitize_optimizer_url(value: str) -> str:
    """Remove credential-like query parameters from a user-entered API URL."""
    parsed = urllib.parse.urlsplit(str(value or "").strip())
    if not parsed.query:
        return urllib.parse.urlunsplit(parsed)
    pairs = [
        (key, item)
        for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if _query_key_name(key) not in _CREDENTIAL_QUERY_KEYS
    ]
    query = urllib.parse.urlencode(pairs, doseq=True)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment)
    )


def validate_optimizer_endpoint(url: str, *, has_credentials: bool) -> str:
    """Return a safe optimizer URL or raise before credentials can be sent.

    Credentialed remote requests are limited to the supported provider hosts.
    Local loopback APIs remain available for Ollama and local proxies. Public
    HTTPS endpoints without credentials are also allowed for local/custom use.
    """
    value = sanitize_optimizer_url(url)
    parsed = urllib.parse.urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("API URL must use http only for loopback, otherwise https")
    if parsed.username or parsed.password:
        raise ValueError("API URL must not contain embedded usernames or passwords")
    if parsed.fragment:
        raise ValueError("API URL must not contain a fragment")

    hostname = _normalized_hostname(parsed)
    loopback = _is_loopback_host(hostname)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("API URL contains an invalid port") from error

    if scheme == "http" and not loopback:
        raise ValueError("Remote API URLs must use HTTPS")

    if has_credentials:
        if loopback:
            return value
        if scheme != "https" or hostname not in OFFICIAL_API_HOSTS:
            raise ValueError(
                "API keys may only be sent to supported provider hosts or a loopback service"
            )
        if port not in {None, 443}:
            raise ValueError("Credentialed remote API URLs must use port 443")
        return value

    if _is_private_ip_literal(hostname) and not loopback:
        raise ValueError("API URL must not target a private, link-local, or reserved address")
    if hostname.endswith((".local", ".internal", ".lan")):
        raise ValueError("API URL must not target a local-only hostname")
    return value


def safe_endpoint_label(url: str) -> str:
    """Describe an endpoint without exposing credentials or query values."""
    parsed = urllib.parse.urlsplit(str(url or ""))
    hostname = str(parsed.hostname or "").strip().lower()
    path = parsed.path or "/"
    return f"{hostname}{path}" if hostname else path
