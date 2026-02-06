from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


def test_health():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_plan_generation():
    payload = {
        'selected_workers': ['정OO', '김OO'],
        'incoming_materials': {'우레탄': 3},
        'priority_areas': ['세대'],
        'weather_summary': '맑음',
    }
    res = client.post('/api/usecase2/plan', json=payload)
    assert res.status_code == 200
    body = res.json()
    assert 'plan' in body
    assert len(body['plan']['timeline']) > 0
