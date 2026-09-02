import pytest


class TestAuthAPI:
    def test_default_admin_can_login(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_default_admin_can_create_organization(self, client):
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        token = login.json()["access_token"]

        response = client.post(
            "/api/v1/organizations",
            json={"name": "Moon Builders"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Moon Builders"

    def test_default_admin_can_create_org_user_with_role(self, client):
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        token = login.json()["access_token"]

        org_response = client.post(
            "/api/v1/organizations",
            json={"name": "Aurora Labs"},
            headers={"Authorization": f"Bearer {token}"},
        )
        org_id = org_response.json()["id"]

        relogin = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        token = relogin.json()["access_token"]

        response = client.post(
            f"/api/v1/organizations/{org_id}/users",
            json={
                "username": "analyst1",
                "email": "analyst1@aurora.local",
                "password": "StrongPass123!",
                "role": "member",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "analyst1"
        assert data["role"] == "member"

    def test_default_admin_cannot_manage_foreign_org(self, client):
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        token = login.json()["access_token"]

        response = client.post(
            "/api/v1/organizations/abc-construction/users",
            json={
                "username": "foreign-user",
                "email": "foreign@abc.local",
                "password": "StrongPass123!",
                "role": "member",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "organization" in response.json()["detail"].lower()
