# PortScope Adaptive Exposure Upgrade

This upgrade adds a lightweight intelligence layer without replacing the
existing Flask scanner.

## Added capabilities

- Exposure fingerprinting using SHA-256 over normalized scan results
- Change detection: added, removed, and modified ports
- Adaptive decision: baseline / reuse / investigate_change
- Small TTL cache with no background thread
- BlackBox JSON observation adapter
- Unit tests for the new intelligence layer

## Design rule

PortScope does not create its own worker pool. BlackBox remains responsible
for scheduling, concurrency, resource limits, and cloud offloading.

## Safety

The existing app.py target restrictions remain unchanged. Only scan systems
you own or are explicitly authorized to test.

## VS Code setup

```bash
cd ~/PortScope
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v
python app.py
```

Copy the `portscope/` directory and the new `tests/test_intelligence.py`
into the existing repository, then commit them on a feature branch.
