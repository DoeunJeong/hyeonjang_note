from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_references():
    rag = client.get('/api/reference/rag-stack')
    assert rag.status_code == 200
    assert rag.json()['vector_db'] == 'chroma'

    templates = client.get('/api/reference/templates')
    assert templates.status_code == 200
    assert 'inventory' in templates.json()


def test_plan_generation_with_site():
    payload = {
        'site_id': 'site-a',
        'selected_workers': ['정OO', '김OO'],
        'incoming_materials': {'우레탄': 3},
        'priority_areas': ['세대'],
        'weather_summary': '맑음',
    }
    res = client.post('/api/usecase2/plan', json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body['site_id'] == 'site-a'
    assert body['plan']['scheduler_status'] == 'skeleton'
    assert len(body['plan']['timeline']) > 0
