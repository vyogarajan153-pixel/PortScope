"""PortScope: lightweight, safety-first port scanning demo/API."""
import ipaddress
import json
import os
import socket
import time
from collections import defaultdict, deque
from threading import Lock

from flask import Flask, jsonify, render_template, request

from portscope.intelligence.blackbox_adapter import make_observation
from portscope.intelligence.cache import TTLCache

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8192

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 25: "SMTP", 53: "DNS", 80: "HTTP",
    110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 8080: "HTTP-ALT",
}
# Public hosting defaults to a no-network demo. Real scanning must be opted into
# explicitly and protected by a secret token configured in the hosting dashboard.
DEMO_MODE = os.environ.get("PORTSCOPE_DEMO_MODE", "1").strip().lower() not in {"0", "false", "no"}
SCAN_TOKEN = os.environ.get("PORTSCOPE_SCAN_TOKEN", "").strip()
SCAN_TIMEOUT = min(max(float(os.environ.get("PORTSCOPE_SCAN_TIMEOUT", "0.5")), 0.1), 1.5)
CACHE = TTLCache(ttl_seconds=60)
CACHE_LOCK = Lock()
REQUESTS = defaultdict(deque)
REQUESTS_LOCK = Lock()
RATE_WINDOW_SECONDS = 60
RATE_MAX_REQUESTS = 20


def resolve_ipv4_targets(target):
    """Resolve once and return every IPv4 address; reject malformed hostnames."""
    target = target.strip()
    if not target or len(target) > 253 or any(c in target for c in "/\\:@"):
        raise ValueError("Enter a valid IP address or hostname.")
    try:
        literal = ipaddress.ip_address(target)
        if literal.version != 4:
            raise ValueError("Only IPv4 targets are supported.")
        return [str(literal)]
    except ValueError as literal_error:
        # Distinguish a valid-but-unsupported IPv6 literal from a hostname.
        try:
            parsed = ipaddress.ip_address(target)
            if parsed.version != 4:
                raise ValueError("Only IPv4 targets are supported.")
        except ValueError as parsed_error:
            if str(parsed_error) == "Only IPv4 targets are supported.":
                raise parsed_error
        try:
            infos = socket.getaddrinfo(target, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise ValueError("Hostname could not be resolved.") from None
        addresses = sorted({info[4][0] for info in infos})
        if not addresses:
            raise ValueError("Hostname has no IPv4 address.")
        return addresses


def is_allowed_ip(value):
    address = ipaddress.ip_address(value)
    return address.is_private or address.is_loopback or address.is_link_local


def validate_ports(selected_ports):
    if not isinstance(selected_ports, list) or not selected_ports:
        raise ValueError("Select at least one port.")
    if len(selected_ports) > len(COMMON_PORTS):
        raise ValueError("Too many ports selected.")
    ports = []
    for value in selected_ports:
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError("Invalid port value.")
        if isinstance(value, str) and not value.isdecimal():
            raise ValueError("Invalid port value.")
        try:
            port = int(value)
        except (TypeError, ValueError):
            raise ValueError("Invalid port value.") from None
        if port not in COMMON_PORTS:
            raise ValueError("Unsupported port.")
        if port in ports:
            raise ValueError("Duplicate ports are not allowed.")
        ports.append(port)
    return ports


def scan_port(ip, port, timeout=SCAN_TIMEOUT):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((ip, port)) == 0
    except OSError:
        return False


def rate_limited(client_ip):
    now = time.monotonic()
    with REQUESTS_LOCK:
        queue = REQUESTS[client_ip]
        while queue and now - queue[0] > RATE_WINDOW_SECONDS:
            queue.popleft()
        if len(queue) >= RATE_MAX_REQUESTS:
            return True
        queue.append(now)
        # Keep the bookkeeping bounded when many client addresses are seen.
        if len(REQUESTS) > 2048:
            for key in list(REQUESTS)[:1024]:
                if key != client_ip:
                    REQUESTS.pop(key, None)
    return False


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    )
    return response


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="Request body is too large."), 413


@app.route("/")
def index():
    return render_template("index.html", ports=COMMON_PORTS)


@app.route("/health")
def health():
    return jsonify(status="ok", mode="demo" if DEMO_MODE else "lab")


@app.route("/api/scan", methods=["POST"])
def scan():
    if rate_limited(request.remote_addr or "unknown"):
        return jsonify(error="Too many requests. Please wait and try again."), 429
    if not request.is_json:
        return jsonify(error="Send a JSON request."), 415
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Invalid JSON request."), 400
    target = data.get("target", "")
    if not isinstance(target, str):
        return jsonify(error="Target must be a string."), 400
    try:
        ports = validate_ports(data.get("ports"))
        addresses = resolve_ipv4_targets(target)
        # Reject mixed DNS answers as a unit; never pick a safe address from a
        # hostname that also resolves to a public address.
        if any(not is_allowed_ip(address) for address in addresses):
            return jsonify(error=("For safety, only private, loopback, and "
                                  "link-local IPv4 targets are permitted.")), 403
        if not DEMO_MODE and not SCAN_TOKEN:
            return jsonify(error="Live scanning is disabled until an admin scan token is configured."), 503
        if not DEMO_MODE:
            auth = request.headers.get("Authorization", "")
            expected = "Bearer " + SCAN_TOKEN
            if not auth or not __import__("hmac").compare_digest(auth, expected):
                return jsonify(error="Authentication required for live scanning."), 401

        # Use the exact resolved address for both validation and connection.
        ip = addresses[0]
        cache_key = json.dumps([ip, ports], separators=(",", ":"))
        with CACHE_LOCK:
            cached = CACHE.get(cache_key)
            previous = CACHE.get("baseline:" + ip)
        if cached is not None:
            results = cached
            mode = "demo" if DEMO_MODE else "lab"
        elif DEMO_MODE:
            # Deterministic sample results: this mode performs no socket scans.
            sample_open = {22, 80, 443}
            results = [{"port": p, "service": COMMON_PORTS[p],
                        "status": "open" if p in sample_open else "closed"}
                       for p in ports]
            mode = "demo"
        else:
            results = [{"port": p, "service": COMMON_PORTS[p],
                        "status": "open" if scan_port(ip, p) else "closed"}
                       for p in ports]
            mode = "lab"
        observation = make_observation(ip, results, previous=previous)
        with CACHE_LOCK:
            CACHE.set(cache_key, results)
            CACHE.set("baseline:" + ip, observation["fingerprint"])
        return jsonify(target=target, resolved_ip=ip, results=results,
                       mode=mode, simulated=(mode == "demo"),
                       adaptive_action=observation["adaptive_action"],
                       change=observation["change"],
                       fingerprint=observation["fingerprint"]["value"],
                       investigation_ports=observation["investigation_ports"])
    except ValueError as error:
        return jsonify(error=str(error)), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=False)
