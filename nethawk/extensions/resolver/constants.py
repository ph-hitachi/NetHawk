LATENCY_THRESHOLDS = {
    'fast': 50,
    'stable': 150,
    'slow': 300,
    'unstable': 1000,
}

# TTL to OS mapping: threshold TTL values and corresponding likely OS
TTL_OS_MAP = {
    255: "Cisco/Network Device",
    128: "Windows",
    64: "Linux",
    32: "Older Windows (e.g., Win9x/NT)",
    1: "Unknown Device or Hop-Limited"
}
