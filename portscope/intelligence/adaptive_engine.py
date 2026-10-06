"""Resource-light decision logic for BlackBox integration.

The engine decides whether a scan result can be reused and which ports
deserve attention. It intentionally does not create threads or workers.
BlackBox remains responsible for scheduling and resource limits.
"""


def choose_action(previous_fingerprint, current_fingerprint):
    if not previous_fingerprint:
        return {
            "action": "baseline",
            "reason": "No previous fingerprint is available.",
        }

    if previous_fingerprint.get("value") == current_fingerprint.get("value"):
        return {
            "action": "reuse",
            "reason": "Exposure fingerprint is unchanged.",
        }

    return {
        "action": "investigate_change",
        "reason": "Exposure fingerprint changed.",
    }


def changed_ports(change):
    return sorted(
        set(change.get("added", []))
        | set(change.get("removed", []))
        | set(change.get("modified", []))
    )
