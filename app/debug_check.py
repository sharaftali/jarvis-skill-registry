import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.database import Base, get_db
from app.main import app
from app.core.config import settings

TEST_DATABASE_URL = settings.DATABASE_URL + '_test' if not settings.DATABASE_URL.endswith('_test') else settings.DATABASE_URL
print('DB_URL', TEST_DATABASE_URL)
engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init())
factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False)

async def override_get_db():
    async with factory() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
headers = {'X-Organization': 'ABC Construction'}
payload = {'name': 'Test Skill', 'description': 'This is a test skill', 'owner_id': 'test-owner', 'requested_tools': ['analyze_data', 'generate_report']}
resp = client.post('/api/v1/skills/', json=payload, headers=headers)
print('POST STATUS', resp.status_code)
print(resp.text)
if resp.status_code == 201:
    obj = resp.json()
    print('ID', obj.get('id'))
    resp2 = client.get(f"/api/v1/skills/{obj['id']}", headers=headers)
    print('GET STATUS', resp2.status_code)
    print(resp2.text)
    resp3 = client.post(f"/api/v1/skills/{obj['id']}/versions", json={'name': 'v1', 'description': 'active version', 'configuration': {}, 'requested_tools': ['test_tool'], 'created_by': 'test-owner'}, headers=headers)
    print('VERSION STATUS', resp3.status_code)
    print(resp3.text)
client.close()
asyncio.run(engine.dispose())
