from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_usecase1_site_worker_inventory_flow():
    setup = client.post(
        '/api/usecase1/setup?site_id=site-ui',
        json={'workers': [], 'inventory': {}, 'priority_areas': ['세대', '상가']},
    )
    assert setup.status_code == 200

    add_worker = client.post('/api/usecase1/workers', json={'site_id': 'site-ui', 'worker_name': '정OO'})
    assert add_worker.status_code == 200
    assert '정OO' in add_worker.json()['workers']

    add_inventory = client.post(
        '/api/usecase1/inventory',
        json={'site_id': 'site-ui', 'material_name': '우레탄방수재', 'quantity': 2},
    )
    assert add_inventory.status_code == 200
    assert add_inventory.json()['inventory']['우레탄방수재'] == 2

    site_status = client.get('/api/usecase1/site/site-ui')
    assert site_status.status_code == 200
    assert '정OO' in site_status.json()['workers']
    assert site_status.json()['priority_areas'] == ['세대', '상가']


def test_plan_generation_with_rag_context():
    payload = {
        'site_id': 'site-a',
        'selected_workers': ['정OO', '김OO'],
        'incoming_materials': {'우레탄방수재': 3},
        'priority_areas': ['세대'],
        'weather_summary': '맑음',
    }
    res = client.post('/api/usecase2/plan', json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body['site_id'] == 'site-a'
    assert 'rag_context' in body['plan']
    assert len(body['plan']['timeline']) >= 1


def test_material_options_endpoint():
    res = client.get('/api/usecase1/material-options')
    assert res.status_code == 200
    assert len(res.json()['materials']) >= 1
