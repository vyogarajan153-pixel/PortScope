"""Small JSON adapter for future BlackBox orchestration.

It only packages observations; it does not initiate scans or network
requests. This keeps the module safe, testable, and decoupled.
"""
from .fingerprint import build_fingerprint
from .change_detector import compare
from .adaptive_engine import choose_action, changed_ports


def make_observation(target, results, previous=None):
    current = build_fingerprint(results)
    change = compare(previous, current) if previous else {
        "changed": False, "added": [], "removed": [], "modified": []
    }
    action = choose_action(previous, current)

    return {
        "module": "portscope",
        "target": target,
        "fingerprint": current,
        "change": change,
        "adaptive_action": action,
        "investigation_ports": changed_ports(change),
    }
