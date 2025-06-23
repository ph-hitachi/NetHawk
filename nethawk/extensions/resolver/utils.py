import time
import socket
import logging
import ipaddress

from scapy.all import IP, ICMP, sr1
from urllib.parse import urlparse
from .constants import TTL_OS_MAP, LATENCY_THRESHOLDS

def is_valid_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False

def classify_latency(latency_ms):
    if latency_ms is None:
        return "unreachable"
    for label, threshold in LATENCY_THRESHOLDS.items():
        if latency_ms < threshold:
            return label
    return "very unstable"

def extract_host_and_port(raw_input, override_port=None):
    parsed = urlparse(raw_input if '://' in raw_input else f"//{raw_input}", scheme='http')
    host = parsed.hostname
    port = override_port or parsed.port
    return host, port

def guess_os_from_ttl(ttl):
    if ttl is None or not isinstance(ttl, int) or ttl <= 0:
        return "Unknown"
    
    for initial_ttl, os_name in sorted(TTL_OS_MAP.items(), reverse=True):
        if ttl <= initial_ttl and ttl > initial_ttl - 20:
            return os_name
    
    return "Unknown"

def ping_host(ip, max_tries=3):
    """
    Sends ICMP Echo Requests to the target IP using Scapy.
    Returns the first successful latency (ms) and TTL value.
    Tries up to `max_tries` times.
    """
    for _ in range(max_tries):
        try:
            packet = IP(dst=ip)/ICMP()
            start_time = time.time()
            reply = sr1(packet, timeout=2, verbose=0)
            end_time = time.time()

            if reply:
                latency = (end_time - start_time) * 1000  # ms
                ttl = reply.ttl
                return latency, ttl
        except PermissionError:
            raise RuntimeError("Scapy requires admin privileges to send ICMP packets.")
        except Exception:
            continue  # Try again

    return None, None

    
def can_connect_tcp(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception as e:
        # logging.error(f"Connection error on {host} with {port}: {e}")
        return False
    
def is_url_with_scheme(url):
    return bool(urlparse(url).scheme)
