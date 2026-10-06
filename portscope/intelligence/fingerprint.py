"""Lightweight exposure fingerprinting for PortScope.

This module does not perform scanning. It converts already-authorized
scan results into a stable fingerprint so BlackBox can compare states
without repeating work unnecessarily.
"""
import hashlib
import json


def normalize_results(results):
    normalized = []
    for item in results or []:
        try:
            port = int(item["port"])
        except (KeyError, TypeError, ValueError):
            continue
        normalized.append({
            "port": port,
            "service": str(item.get("service", "unknown")),
            "status": str(item.get("status", "unknown")).lower(),
        })
    return sorted(normalized, key=lambda x: x["port"])


def build_fingerprint(results):
    normalized = normalize_results(results)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return {
        "algorithm": "sha256",
        "value": digest,
        "open_ports": [
            item["port"] for item in normalized if item["status"] == "open"
        ],
        "results": normalized,
    }
