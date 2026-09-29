from fastapi.testclient import TestClient
from backend.main import app

client=TestClient(app)

def test_health():
    r=client.get('/api/health'); assert r.status_code==200; assert r.json()['status']=='ok'

def test_score():
    tx={"transaction_id":"TEST-1","amount":9500,"velocity_1h":8,"velocity_24h":20,"device_reuse_24h":5,"account_age_days":2,"geo_distance_km":800,"chargeback_history":2,"return_rate":0.3,"new_device":1,"ip_risk":0.8,"payment_risk":0.9,"hour_risk":0.7,"merchant_risk":0.6,"amount_zscore":2.5}
    r=client.post('/api/score',json=tx); assert r.status_code==200; assert 0<=r.json()['risk_score']<=1

def test_model_metrics():
    r=client.get('/api/model'); assert r.status_code==200; assert {'precision','recall','f1'} <= set(r.json())


def test_demo_incidents():
    r=client.get('/api/incidents')
    assert r.status_code==200
    items=r.json()
    assert len(items) >= 4
    assert all(item['demo'] is True for item in items[:4])
    assert {'fraud_spike_detector','return_risk_scorer','chargeback_evidence_responder','abuse_ring_sentinel'} <= {item['detector'] for item in items}


def test_system_status_is_truthful():
    data=client.get('/api/system-status').json()
    assert data['components']['demo_incident_engine']['status']=='active'
    assert 'postgres' not in data['components']
    assert 'redis' not in data['components']
    assert 'redpanda' not in data['components']


def test_incident_detail():
    r=client.get('/api/incidents/SPIKE-DEMO-001')
    assert r.status_code==200
    assert r.json()['detector']=='fraud_spike_detector'
