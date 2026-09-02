# Jarvis AI COO - Skill Registry

A privacy-first, local-first, multi-tenant backend for managing organization-scoped AI COO skills.

## Features

- **Multi-tenant isolation**: Complete separation between organizations
- **Immutable versioning**: Skills are versioned immutably - changes create new versions
- **Audit logging**: All skill creation, versioning, and activation events are logged
- **Role-based authorization**: Only organization owners can activate skills
- **Secure tool validation**: Destructive or invalid tools are rejected
- **PostgreSQL with async support**: Production-ready database setup
- **Comprehensive test suite**: Automated tests covering all requirements

## Tech Stack

- **FastAPI**: Modern, fast web framework
- **PostgreSQL**: Production database with async support
- **SQLAlchemy**: ORM with async capabilities
- **Alembic**: Database migrations
- **Pydantic**: Data validation
- **Pytest**: Testing framework
- **Docker**: Containerization

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

## Quick Start

### Using Docker Compose

```bash
# Clone the repository
git clone <your-repo-url>
cd jarvis-skill-registry

# Copy environment variables
cp .env.example .env

# Start services
docker-compose up -d

# Run migrations
docker-compose exec app alembic upgrade head
