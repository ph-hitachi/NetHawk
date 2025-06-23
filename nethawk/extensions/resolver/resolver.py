import socket
from types import SimpleNamespace
from urllib.parse import urlparse
from .utils import (
    is_valid_ip, ping_host, classify_latency, guess_os_from_ttl,
    is_url_with_scheme, extract_host_and_port, can_connect_tcp
)

def resolve_host(raw_input, port_override=None, max_tries=3):
    result = {
        "original": raw_input,
        "input_type": None,
        "ip": None,
        "hostname": None,
        "icmp_reachable": False,
        "icmp_latency_ms": None,
        "icmp_latency_category": None,
        "os_guess_from_ttl": None,
        "resolved_url": None,
        "port": None,
        "tcp_port_open": None,
        "error": None,
    }

    try:
        host, port = extract_host_and_port(raw_input, port_override)
        result["port"] = port

        if not host:
            result["error"] = "Invalid host format"
            return SimpleNamespace(**result)

        # Determine if input is IP or domain
        if is_valid_ip(host):
            result["input_type"] = "ip"
            result["ip"] = host
            try:
                result["hostname"] = socket.gethostbyaddr(host)[0]
            except socket.herror:
                result["error"] = "Reverse DNS lookup failed"
        else:
            result["input_type"] = "domain"
            try:
                ip = socket.gethostbyname(host)
                result["ip"] = ip
                result["hostname"] = host
            except socket.gaierror as e:
                result["error"] = f"DNS resolution failed: {str(e)}"
                return SimpleNamespace(**result)

        # ICMP ping and TTL
        latency, ttl = ping_host(result["ip"], max_tries=max_tries)
        result["icmp_latency_ms"] = latency
        result["icmp_latency_category"] = classify_latency(latency)
        result["icmp_reachable"] = latency is not None
        result["os_guess_from_ttl"] = guess_os_from_ttl(ttl)

        # Protocol fallback: https -> http
        scheme = "https"
        if is_url_with_scheme(raw_input):
            scheme = urlparse(raw_input).scheme

        schemes_to_try = [scheme, "http"] if scheme == "https" else [scheme]

        for proto in schemes_to_try:
            default_port = 443 if proto == "https" else 80
            port_to_use = port or default_port

            if can_connect_tcp(host, port_to_use):
                result["tcp_port_open"] = True

                # Use hostname if available
                url_host = result["hostname"] if result["hostname"] else host

                # Update final used port and scheme
                result["port"] = port_to_use
                result["error"] = None  # Clear any earlier error

                # Ensure correct protocol-port mapping
                if (proto == "https" and port_to_use == 80) or (proto == "http" and port_to_use == 443):
                    proto = "http" if port_to_use == 80 else "https"
                    default_port = 80 if proto == "http" else 443

                # Only add port to URL if it's non-default
                if port_to_use == default_port:
                    result["resolved_url"] = f"{proto}://{url_host}"
                else:
                    result["resolved_url"] = f"{proto}://{url_host}:{port_to_use}"
                break
            else:
                result["tcp_port_open"] = False
                result["error"] = f"TCP connection to port {port_to_use} failed"

        # If port is defined but still no successful connection
        if result["resolved_url"] is None and result["tcp_port_open"] is None and port:
            if can_connect_tcp(host, port):
                result["tcp_port_open"] = True
            else:
                result["tcp_port_open"] = False
                result["error"] = f"TCP connection to port {port} failed"

        # Final fallback error if everything failed
        if result["resolved_url"] is None and result["tcp_port_open"] is None:
            result["tcp_port_open"] = False
            result["error"] = "No open port found and URL could not be resolved"

    except Exception as e:
        result["error"] = str(e)

    return SimpleNamespace(**result)
