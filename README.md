# Jarvis AI COO - Skill Registry

A privacy-first, local-first, multi-tenant backend for managing organization-scoped AI COO skills.

## Features

- **Multi-tenant isolation**: Organization-scoped access is enforced on every protected route.
- **Immutable versioning**: Skills are versioned immutably; changes create new versions.
- **Audit logging**: Skill, version, and activation events are logged with organization, actor, and version metadata.
- **Role-based authorization**: Only organization owners can activate or disable skills.
- **Secure tool validation**: Destructive or invalid requested tools are rejected.
- **PostgreSQL with async support**: PostgreSQL is the default runtime database.
- **Automated tests**: Regression coverage for auth, isolation, versioning, and audit behavior.

## Tech Stack

- FastAPI
- PostgreSQL
- SQLAlchemy Async ORM
- Alembic
- Pydantic
- Pytest
- Docker Compose

## Prerequisites

- Docker and Docker Compose
- Python 3.11+

## Quick Start

```bash
# Clone the repository
git clone https://github.com/sharaftali/jarvis-skill-registry.git
cd jarvis-skill-registry

# Create local env file from template
cp .env.example .env

# Start services
docker-compose up -d

# Apply database migrations
docker-compose exec app alembic upgrade head
```

## Default bootstrap account

The app creates a default bootstrap owner on startup using the env values in `.env`:

- Username: `DEFAULT_ADMIN_USERNAME`
- Email: `DEFAULT_ADMIN_EMAIL`
- Password: `DEFAULT_ADMIN_PASSWORD`
- Organization: `DEFAULT_ORGANIZATION_ID`

This bootstrap credential is used only for initial setup and must not be treated as a cross-tenant admin bypass.

## Example login and protected calls

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}'
```

```bash
curl -X GET http://localhost:8000/api/v1/skills \
  -H 'Authorization: Bearer <token>' \
  -H 'X-Organization: ABC Construction'
```

## Testing

```bash
docker-compose exec -T app pytest tests/test_api/test_auth.py tests/test_api/test_skills.py -q
```

## Security and isolation notes

- Organization membership is enforced by `organization_id`.
- Cross-tenant reads and writes are rejected.
- Only owners can activate or disable skills.
- Skill versions are immutable; new versions are created rather than mutating active content.

