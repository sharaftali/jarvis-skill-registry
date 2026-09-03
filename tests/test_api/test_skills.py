import pytest
from uuid import uuid4
from app.core.config import settings


def login(client, username="admin", password="Admin@123"):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def create_org(client, token, name):
    response = client.post(
        "/api/v1/organizations",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_org_user(client, token, org_id, username, email, password, role="owner"):
    response = client.post(
        f"/api/v1/organizations/{org_id}/users",
        json={
            "username": username,
            "email": email,
            "password": password,
            "role": role,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestSkillsAPI:
    """Test skills API endpoints"""

    def test_create_skill_same_organization_succeeds(self, client, skill_payload):
        """Test: Same-organization create/read succeeds"""
        admin_token = login(client)
        org = create_org(client, admin_token, "Moon Builders")
        org_id = org["id"]
        owner_token = login(client, "admin", "Admin@123")

        response = client.post(
            "/api/v1/skills",
            json=skill_payload,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == skill_payload["name"]
        assert data["organization_id"] == org_id
        assert data["status"] == "draft"

        skill_id = data["id"]
        response = client.get(f"/api/v1/skills/{skill_id}", headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200
        assert response.json()["id"] == skill_id

    def test_cross_organization_read_denied(self, client, skill_payload):
        """Test: Cross-organization read is denied"""
        admin_token = login(client)
        abc = create_org(client, admin_token, "ABC Construction")
        admin_token = login(client)
        abc_owner = create_org_user(client, admin_token, abc["id"], "abc-owner", "abc-owner@example.com", "StrongPass123!", role="owner")

        xyz = create_org(client, admin_token, "XYZ Builders")
        admin_token = login(client)
        xyz_owner = create_org_user(client, admin_token, xyz["id"], "xyz-owner", "xyz-owner@example.com", "StrongPass123!", role="owner")

        abc_token = login(client, abc_owner["username"], "StrongPass123!")
        xyz_token = login(client, xyz_owner["username"], "StrongPass123!")

        response = client.post(
            "/api/v1/skills",
            json=skill_payload,
            headers={"Authorization": f"Bearer {abc_token}"},
        )
        assert response.status_code == 201
        skill_id = response.json()["id"]

        response = client.get(f"/api/v1/skills/{skill_id}", headers={"Authorization": f"Bearer {xyz_token}"})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cross_organization_update_denied(self, client, skill_payload):
        """Test: Cross-organization update is denied"""
        admin_token = login(client)
        abc = create_org(client, admin_token, "ABC Construction")
        admin_token = login(client)
        abc_owner = create_org_user(client, admin_token, abc["id"], "abc-owner2", "abc-owner2@example.com", "StrongPass123!", role="owner")

        xyz = create_org(client, admin_token, "XYZ Builders")
        admin_token = login(client)
        xyz_owner = create_org_user(client, admin_token, xyz["id"], "xyz-owner2", "xyz-owner2@example.com", "StrongPass123!", role="owner")

        abc_token = login(client, abc_owner["username"], "StrongPass123!")
        xyz_token = login(client, xyz_owner["username"], "StrongPass123!")

        response = client.post(
            "/api/v1/skills",
            json=skill_payload,
            headers={"Authorization": f"Bearer {abc_token}"},
        )
        assert response.status_code == 201
        skill_id = response.json()["id"]

        update_data = {"name": "Hacked Name"}
        response = client.put(f"/api/v1/skills/{skill_id}", json=update_data, headers={"Authorization": f"Bearer {xyz_token}"})
        assert response.status_code == 403

    def test_non_owner_activation_denied(self, client, skill_payload, version_payload):
        """Test: Non-owner activation is denied"""
        admin_token = login(client)
        org = create_org(client, admin_token, "Owner Guard Org")
        admin_token = login(client)
        owner_user = create_org_user(client, admin_token, org["id"], "og-owner", "og-owner@example.com", "StrongPass123!", role="owner")
        token = login(client, owner_user["username"], "StrongPass123!")

        skill_payload["owner_id"] = "owner1"
        response = client.post("/api/v1/skills", json=skill_payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 201
        skill_id = response.json()["id"]

        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 201
        version_id = response.json()["id"]

        activation_data = {"activated_by": "owner2"}
        response = client.post(
            f"/api/v1/skills/{skill_id}/versions/{version_id}/activate",
            json=activation_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()

    def test_draft_skill_cannot_execute_as_active(self, client, skill_payload):
        """Test: Draft skill cannot execute or load as active"""
        admin_token = login(client)
        org = create_org(client, admin_token, "Draft Org")
        admin_token = login(client)
        owner_user = create_org_user(client, admin_token, org["id"], "draft-owner", "draft-owner@example.com", "StrongPass123!", role="owner")
        token = login(client, owner_user["username"], "StrongPass123!")

        response = client.post("/api/v1/skills", json=skill_payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 201
        skill_id = response.json()["id"]

        response = client.get(f"/api/v1/skills/{skill_id}", headers={"Authorization": f"Bearer {token}"})
        assert response.json()["status"] == "draft"

        response = client.get("/api/v1/skills/active/department/test", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        skills = response.json()["skills"]
        assert len(skills) == 0 or skill_id not in [s["id"] for s in skills]

    def test_disabled_skill_excluded_from_runtime(self, client, skill_payload):
        """Test: Disabled skill is excluded from runtime selection"""
        admin_token = login(client)
        org = create_org(client, admin_token, "Runtime Org")
        admin_token = login(client)
        owner_user = create_org_user(client, admin_token, org["id"], "runtime-owner", "runtime-owner@example.com", "StrongPass123!", role="owner")
        token = login(client, owner_user["username"], "StrongPass123!")
        skill_payload["owner_id"] = owner_user["username"]

        response = client.post("/api/v1/skills", json=skill_payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 201
        skill_id = response.json()["id"]

        version_payload = {
            "name": "v1",
            "description": "active version",
            "configuration": {},
            "requested_tools": ["test_tool"],
            "created_by": "runtime-owner",
        }
        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload, headers={"Authorization": f"Bearer {token}"})
        version_id = response.json()["id"]

        activation_data = {"activated_by": "runtime-owner"}
        response = client.post(
            f"/api/v1/skills/{skill_id}/versions/{version_id}/activate",
            json=activation_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        response = client.post(f"/api/v1/skills/{skill_id}/disable", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

        response = client.get("/api/v1/skills/active/department/test", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        skills = response.json()["skills"]
        assert skill_id not in [s["id"] for s in skills]

    def test_active_version_is_immutable(self, client, skill_payload):
        """Test: Active version is immutable"""
        admin_token = login(client)
        org = create_org(client, admin_token, "Version Org")
        admin_token = login(client)
        owner_user = create_org_user(client, admin_token, org["id"], "version-owner", "version-owner@example.com", "StrongPass123!", role="owner")
        token = login(client, owner_user["username"], "StrongPass123!")
        skill_payload["owner_id"] = owner_user["username"]

        response = client.post("/api/v1/skills", json=skill_payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 201
        skill_id = response.json()["id"]

        version_payload = {
            "name": "v1",
            "description": "active version",
            "configuration": {},
            "requested_tools": ["test_tool"],
            "created_by": "version-owner",
        }
        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload, headers={"Authorization": f"Bearer {token}"})
        version_id = response.json()["id"]

        activation_data = {"activated_by": "version-owner"}
        response = client.post(
            f"/api/v1/skills/{skill_id}/versions/{version_id}/activate",
            json=activation_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        version_payload2 = {
            "name": "v2",
            "description": "newer version",
            "configuration": {},
            "requested_tools": ["test_tool2"],
            "created_by": "version-owner",
        }
        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload2, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 201

        response = client.get(f"/api/v1/skills/{skill_id}/versions", headers={"Authorization": f"Bearer {token}"})
        versions = response.json()["versions"]
        active_versions = [v for v in versions if v["is_active"]]
        assert len(active_versions) == 1
        assert active_versions[0]["version"] == 1

    def test_duplicate_activation_is_safe_and_idempotent(self, client, skill_payload):
        """Test: Duplicate activation request is safe and idempotent"""
        admin_token = login(client)
        org = create_org(client, admin_token, "Duplicate Org")
        admin_token = login(client)
        owner_user = create_org_user(client, admin_token, org["id"], "dup-owner", "dup-owner@example.com", "StrongPass123!", role="owner")
        token = login(client, owner_user["username"], "StrongPass123!")
        skill_payload["owner_id"] = owner_user["username"]

        response = client.post("/api/v1/skills", json=skill_payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 201
        skill_id = response.json()["id"]

        version_payload = {
            "name": "v1",
            "description": "test version",
            "configuration": {},
            "requested_tools": ["test_tool"],
            "created_by": "dup-owner",
        }
        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload, headers={"Authorization": f"Bearer {token}"})
        version_id = response.json()["id"]

        activation_data = {"activated_by": "dup-owner"}
        for _ in range(2):
            response = client.post(
                f"/api/v1/skills/{skill_id}/versions/{version_id}/activate",
                json=activation_data,
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

        response = client.get(f"/api/v1/skills/{skill_id}/versions", headers={"Authorization": f"Bearer {token}"})
        versions = response.json()["versions"]
        active_versions = [v for v in versions if v["is_active"]]
        assert len(active_versions) == 1

    def test_invalid_or_destructive_tool_rejected(self, client, skill_payload):
        """Test: Invalid or destructive requested tool is rejected"""
        admin_token = login(client)
        org = create_org(client, admin_token, "Tool Org")
        admin_token = login(client)
        owner_user = create_org_user(client, admin_token, org["id"], "tool-owner", "tool-owner@example.com", "StrongPass123!", role="owner")
        token = login(client, owner_user["username"], "StrongPass123!")
        skill_payload["owner_id"] = owner_user["username"]

        skill_payload["requested_tools"] = ["delete_all", "analyze_data"]
        response = client.post("/api/v1/skills", json=skill_payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 400
        assert "destructive" in response.json()["detail"].lower()

        skill_payload["requested_tools"] = ["valid_tool", "invalid-tool!"]
        response = client.post("/api/v1/skills", json=skill_payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 400
        assert "invalid tool" in response.json()["detail"].lower()

    def test_audit_record_contains_organization_actor_event_version(self, client, skill_payload):
        """Test: Audit record contains organization, actor, event and version"""
        admin_token = login(client)
        org = create_org(client, admin_token, "Audit Org")
        admin_token = login(client)
        owner_user = create_org_user(client, admin_token, org["id"], "audit-owner", "audit-owner@example.com", "StrongPass123!", role="owner")
        token = login(client, owner_user["username"], "StrongPass123!")
        skill_payload["owner_id"] = owner_user["username"]

        response = client.post("/api/v1/skills", json=skill_payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 201
        skill_id = response.json()["id"]

        response = client.get(f"/api/v1/skills/{skill_id}/audit-logs", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        logs = response.json()["logs"]
        assert len(logs) >= 1

        for log in logs:
            assert "organization_id" in log
            assert log["organization_id"] == org["id"]
            assert "actor" in log
            assert "event_type" in log
            assert "version_id" in log or log["version_id"] is None
            assert "details" in log
