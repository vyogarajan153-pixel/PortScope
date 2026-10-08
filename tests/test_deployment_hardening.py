import json

import app as portscope_app


def client():
    portscope_app.app.config.update(TESTING=True)
    return portscope_app.app.test_client()


def test_health_has_mode():
    response = client().get('/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'ok'


def test_public_ipv4_is_blocked(monkeypatch):
    monkeypatch.setattr(portscope_app, 'DEMO_MODE', True)
    response = client().post('/api/scan', json={'target': '8.8.8.8', 'ports': [80]})
    assert response.status_code == 403


def test_bad_ports_are_rejected():
    response = client().post('/api/scan', json={'target': '127.0.0.1', 'ports': [80, 'abc']})
    assert response.status_code == 400


def test_duplicate_ports_are_rejected():
    response = client().post('/api/scan', json={'target': '127.0.0.1', 'ports': [80, 80]})
    assert response.status_code == 400


def test_demo_scan_uses_aee_and_does_not_scan_socket(monkeypatch):
    monkeypatch.setattr(portscope_app, 'DEMO_MODE', True)
    monkeypatch.setattr(portscope_app, 'scan_port', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('socket scan called')))
    with portscope_app.CACHE_LOCK:
        portscope_app.CACHE.clear()
    response = client().post('/api/scan', json={'target': '127.0.0.1', 'ports': [22, 80]})
    assert response.status_code == 200
    data = response.get_json()
    assert data['simulated'] is True
    assert data['adaptive_action']['action'] == 'baseline'
    assert len(data['fingerprint']) == 64
    json.dumps(data)


def test_invalid_json_shape_rejected():
    response = client().post('/api/scan', json=['not', 'an', 'object'])
    assert response.status_code == 400


def test_non_json_rejected():
    response = client().post('/api/scan', data='target=127.0.0.1')
    assert response.status_code == 415
