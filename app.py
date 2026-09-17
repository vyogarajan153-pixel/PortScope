import ipaddress
import socket
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8192

COMMON_PORTS = {
    21: "FTP",
    22: "SSH",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    8080: "HTTP-ALT",
}

def resolve_target(target):
    target = target.strip()

    if not target or len(target) > 253:
        raise ValueError("Invalid target.")

    if any(char in target for char in ["/", "\\", ":", "@"]):
        raise ValueError("Enter only an IP address or hostname.")

    try:
        return str(ipaddress.ip_address(target))
    except ValueError:
        try:
            return socket.gethostbyname(target)
        except socket.gaierror:
            raise ValueError("Hostname could not be resolved.")

def is_allowed_ip(ip):
    address = ipaddress.ip_address(ip)
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
    )

def scan_port(ip, port, timeout=0.5):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((ip, port)) == 0
    except OSError:
        return False

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "connect-src 'self'; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'"
    )
    return response

@app.route("/")
def index():
    return render_template("index.html", ports=COMMON_PORTS)

@app.route("/health")
def health():
    return jsonify(status="ok")

@app.route("/api/scan", methods=["POST"])
def scan():
    data = request.get_json(silent=True) or {}

    target = str(data.get("target", "")).strip()
    selected_ports = data.get("ports")

    if not isinstance(selected_ports, list):
        return jsonify(error="Invalid port selection."), 400

    if not selected_ports:
        return jsonify(error="Select at least one port."), 400

    if len(selected_ports) > len(COMMON_PORTS):
        return jsonify(error="Too many ports selected."), 400

    try:
        ip = resolve_target(target)

        if not is_allowed_ip(ip):
            return jsonify(
                error=(
                    "For safety, this application only scans "
                    "private, loopback, and link-local addresses."
                )
            ), 403

        ports = []

        for value in selected_ports:
            try:
                port = int(value)
            except (TypeError, ValueError):
                continue

            if port in COMMON_PORTS:
                ports.append(port)

        results = []

        for port in ports:
            results.append({
                "port": port,
                "service": COMMON_PORTS[port],
                "status": "open" if scan_port(ip, port) else "closed"
            })

        return jsonify(
            target=target,
            resolved_ip=ip,
            results=results
        )

    except ValueError as error:
        return jsonify(error=str(error)), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
