from tests.conftest import client as client_fixture

# Call fixture function directly, matching pytest's setup path more closely.
result = client_fixture.__wrapped__() if hasattr(client_fixture, '__wrapped__') else client_fixture()
print(type(result))
# This is a generator fixture; use the yielded value via context manager.
try:
    with result as client:
        headers = {'X-Organization': 'ABC Construction'}
        payload = {'name': 'Test Skill', 'description': 'This is a test skill', 'owner_id': 'test-owner', 'requested_tools': ['analyze_data', 'generate_report']}
        response = client.post('/api/v1/skills', json=payload, headers=headers)
        print('POST', response.status_code, response.text)
        if response.status_code == 201:
            skill_id = response.json()['id']
            response2 = client.get(f'/api/v1/skills/{skill_id}', headers=headers)
            print('GET', response2.status_code, response2.text)
except Exception as exc:
    print('ERROR', type(exc), exc)
