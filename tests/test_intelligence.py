from portscope.intelligence.fingerprint import build_fingerprint
from portscope.intelligence.change_detector import compare
from portscope.intelligence.adaptive_engine import choose_action
from portscope.intelligence.blackbox_adapter import make_observation


def test_fingerprint_is_stable():
    results = [
        {"port": 80, "service": "HTTP", "status": "open"},
        {"port": 22, "service": "SSH", "status": "closed"},
    ]
    assert build_fingerprint(results)["value"] == build_fingerprint(results)["value"]


def test_change_detection_finds_added_port():
    old = build_fingerprint([{"port": 80, "service": "HTTP", "status": "open"}])
    new = build_fingerprint([
        {"port": 80, "service": "HTTP", "status": "open"},
        {"port": 8080, "service": "HTTP-ALT", "status": "open"},
    ])
    change = compare(old, new)
    assert change["added"] == [8080]
    assert change["changed"] is True


def test_adaptive_engine_reuses_unchanged_result():
    fp = build_fingerprint([{"port": 80, "service": "HTTP", "status": "open"}])
    assert choose_action(fp, fp)["action"] == "reuse"


def test_blackbox_observation_is_json_serializable():
    observation = make_observation(
        "127.0.0.1",
        [{"port": 80, "service": "HTTP", "status": "open"}],
    )
    assert observation["module"] == "portscope"
    assert observation["investigation_ports"] == []
