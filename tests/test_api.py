from fastapi.testclient import TestClient

from backend.main import app
from backend.weather import build_weather_request

client = TestClient(app)


def test_health():
    res = client.get('/health')
    assert res.status_code == 200
    assert res.json()['status'] == 'ok'


def test_weather_request_spec():
    spec = build_weather_request(latitude=37.46, longitude=126.71)
    assert spec['url'].startswith('https://api.open-meteo.com')
    assert spec['params']['latitude'] == 37.46
    assert spec['params']['longitude'] == 126.71
    assert 'hourly' in spec['params']


def test_usecase1_structured_fields_flow():
    setup = client.post(
        '/api/usecase1/setup?site_id=site-ui',
        json={
            'workers': ['정OO'],
            'inventory': {'우레탄방수재': 2},
            'priority_areas': ['세대'],
            'floor_area_map': {'세대': {'10층': 400.0}},
            'area_progress': {'세대': 35.0},
            'area_waterproof_methods': {'세대': '습식 2종 방수'},
        },
    )
    assert setup.status_code == 200

    site_status = client.get('/api/usecase1/site/site-ui')
    assert site_status.status_code == 200
    body = site_status.json()
    assert body['floor_area_map']['세대']['10층'] == 400.0
    assert body['area_progress']['세대'] == 35.0
    assert body['area_waterproof_methods']['세대'] == '습식 2종 방수'


def test_progress_update_endpoint():
    res = client.post('/api/usecase3/progress', json={'site_id': 'site-ui', 'area_progress': {'세대': 50.0}})
    assert res.status_code == 200
    assert res.json()['area_progress']['세대'] == 50.0


def test_plan_generation_with_rag_context_keys():
    payload = {
        'site_id': 'site-ui',
        'selected_workers': ['정OO'],
        'incoming_materials': {},
        'priority_areas': ['세대'],
    }
    res = client.post('/api/usecase2/plan', json=payload)
    assert res.status_code == 200
    body = res.json()
    rag_context = body['plan']['rag_context']
    assert 'worker_reg' in rag_context
    assert 'floor_area_map_rag' in rag_context
    assert 'area_progress_rag' in rag_context
    assert 'area_waterproof_methods_rag' in rag_context
    assert 'weather_rag' in rag_context


def test_material_options_endpoint():
    res = client.get('/api/usecase1/material-options')
    assert res.status_code == 200
    assert len(res.json()['materials']) >= 1
