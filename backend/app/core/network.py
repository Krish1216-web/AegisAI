"""
AegisAI Enterprise — Production Networking & Client IP Resolution
Provides secure client IP extraction with trusted proxy validation, preventing
header spoofing across reverse proxies, load balancers, and direct connections.
"""

import ipaddress
from typing import List, Optional, Union
from fastapi import Request
from app.core.config import settings

def is_trusted_proxy(ip_str: str, trusted_proxies: Optional[List[str]] = None) -> bool:
    """
    Evaluates whether an IP address matches the configured list of trusted proxies or CIDR blocks.
    """
    if not ip_str or ip_str == "unknown":
        return False

    if trusted_proxies is None:
        trusted_proxies = getattr(
            settings,
            "TRUSTED_PROXIES",
            ["127.0.0.1", "::1", "localhost", "172.16.0.0/12", "10.0.0.0/8", "192.168.0.0/16"]
        )

    # Handle localhost name
    if ip_str.lower() in ("localhost", "testclient", "testserver"):
        return "localhost" in trusted_proxies or "127.0.0.1" in trusted_proxies

    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    for proxy_pattern in trusted_proxies:
        if proxy_pattern.lower() in ("localhost", "testclient", "testserver"):
            if ip_obj.is_loopback:
                return True
            continue

        try:
            if "/" in proxy_pattern:
                net = ipaddress.ip_network(proxy_pattern, strict=False)
                if ip_obj in net:
                    return True
            else:
                proxy_ip = ipaddress.ip_address(proxy_pattern)
                if ip_obj == proxy_ip:
                    return True
        except ValueError:
            continue

    return False

def get_trusted_client_ip(
    request: Request,
    trusted_proxies: Optional[List[str]] = None
) -> str:
    """
    Extracts the genuine client IP address.
    If the direct socket peer (request.client.host) is a trusted reverse proxy,
    inspects X-Forwarded-For / X-Real-IP headers.
    If the direct peer is NOT in the trusted proxy list, header values are ignored
    to prevent client-side IP spoofing.
    """
    direct_ip = request.client.host if request.client else "unknown"

    if direct_ip == "unknown":
        return "unknown"

    # Only inspect forwarding headers if request arrives from a trusted proxy
    if is_trusted_proxy(direct_ip, trusted_proxies):
        # 1. Check X-Forwarded-For header
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For format: client, proxy1, proxy2
            ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
            if ips:
                # First IP is the originating client
                client_candidate = ips[0]
                try:
                    # Validate candidate is a syntactically valid IP
                    ipaddress.ip_address(client_candidate)
                    return client_candidate
                except ValueError:
                    pass

        # 2. Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            real_ip = real_ip.strip()
            try:
                ipaddress.ip_address(real_ip)
                return real_ip
            except ValueError:
                pass

    return direct_ip
