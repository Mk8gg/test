#!/usr/bin/env python3
import concurrent.futures
import ipaddress
import os
import socket
import ssl
import time
from pathlib import Path

import requests

PORT = int(os.getenv("PORT", "443"))
TOP_N = int(os.getenv("TOP_N", "50"))
TIMEOUT = float(os.getenv("TIMEOUT_MS", "2500")) / 1000
MAX_IPS_PER_CIDR = int(os.getenv("MAX_IPS_PER_CIDR", "256"))
OUT = Path("results")
OUT.mkdir(parents=True, exist_ok=True)

CF_RANGES_URL = "https://www.cloudflare.com/ips-v4"

def get_ranges():
    r = requests.get(CF_RANGES_URL, timeout=15)
    r.raise_for_status()
    return [x.strip() for x in r.text.splitlines() if x.strip()]

def expand_network(cidr):
    net = ipaddress.ip_network(cidr)
    hosts = list(net.hosts())
    if len(hosts) <= MAX_IPS_PER_CIDR:
        return hosts
    # Evenly sample a CIDR instead of scanning millions of addresses.
    step = max(1, len(hosts) // MAX_IPS_PER_CIDR)
    return hosts[::step][:MAX_IPS_PER_CIDR]

def test_ip(ip):
    start = time.perf_counter()
    try:
        with socket.create_connection((str(ip), PORT), timeout=TIMEOUT):
            tcp_ms = (time.perf_counter() - start) * 1000

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        tls_start = time.perf_counter()
        with socket.create_connection((str(ip), PORT), timeout=TIMEOUT) as raw:
            with ctx.wrap_socket(raw, server_hostname="speed.cloudflare.com"):
                tls_ms = (time.perf_counter() - tls_start) * 1000

        return {
            "ip": str(ip),
            "tcp_ms": round(tcp_ms, 2),
            "tls_ms": round(tls_ms, 2),
            "score": round(tcp_ms + tls_ms, 2),
        }
    except Exception:
        return None

def main():
    ranges = get_ranges()
    candidates = []
    for cidr in ranges:
        candidates.extend(expand_network(cidr))

    print(f"Testing {len(candidates)} sampled Cloudflare IPv4 addresses...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        for result in pool.map(test_ip, candidates):
            if result:
                results.append(result)

    results.sort(key=lambda x: (x["score"], x["tcp_ms"]))
    results = results[:TOP_N]

    lines = [f'{x["ip"]}:{PORT}#CF-Best | {x["tcp_ms"]:.0f}ms' for x in results]

    (OUT / "all.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    (OUT / "443.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # Placeholder until real China Telecom/Unicom/Mobile probes are connected.
    for name in ("ctcc.txt", "cucc.txt", "cmcc.txt"):
        (OUT / name).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    (OUT / "raw.json").write_text(
        __import__("json").dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Successful: {len(results)}")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
