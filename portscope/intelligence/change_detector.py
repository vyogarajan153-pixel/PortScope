"""Compare two PortScope exposure fingerprints."""


def compare(previous, current):
    previous = previous or {}
    current = current or {}

    old = {
        item["port"]: item
        for item in previous.get("results", [])
        if isinstance(item, dict) and "port" in item
    }
    new = {
        item["port"]: item
        for item in current.get("results", [])
        if isinstance(item, dict) and "port" in item
    }

    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(
        port for port in set(old) & set(new)
        if (old[port].get("status"), old[port].get("service"))
        != (new[port].get("status"), new[port].get("service"))
    )

    return {
        "changed": bool(added or removed or changed),
        "added": added,
        "removed": removed,
        "modified": changed,
    }
