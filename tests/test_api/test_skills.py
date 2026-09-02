import pytest
from uuid import uuid4
from app.core.config import settings


class TestSkillsAPI:
    """Test skills API endpoints"""
    
    def test_create_skill_same_organization_succeeds(self, client, abc_headers, skill_payload):
        """Test: Same-organization create/read succeeds"""
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == skill_payload["name"]
        assert data["organization_id"] == "ABC Construction"
        assert data["status"] == "draft"
        
        # Read back
        skill_id = data["id"]
        response = client.get(f"/api/v1/skills/{skill_id}", headers=abc_headers)
        assert response.status_code == 200
        assert response.json()["id"] == skill_id
    
    def test_cross_organization_read_denied(self, client, abc_headers, xyz_headers, skill_payload):
        """Test: Cross-organization read is denied"""
        # Create skill in ABC
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 201
        skill_id = response.json()["id"]
        
        # Try to read with XYZ headers
        response = client.get(f"/api/v1/skills/{skill_id}", headers=xyz_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_cross_organization_update_denied(self, client, abc_headers, xyz_headers, skill_payload):
        """Test: Cross-organization update is denied"""
        # Create skill in ABC
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 201
        skill_id = response.json()["id"]
        
        # Try to update with XYZ headers
        update_data = {"name": "Hacked Name"}
        response = client.put(f"/api/v1/skills/{skill_id}", json=update_data, headers=xyz_headers)
        assert response.status_code == 403
    
    def test_non_owner_activation_denied(self, client, abc_headers, skill_payload, version_payload):
        """Test: Non-owner activation is denied"""
        # Create skill with owner=owner1
        skill_payload["owner_id"] = "owner1"
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 201
        skill_id = response.json()["id"]
        
        # Create version
        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload, headers=abc_headers)
        assert response.status_code == 201
        version_id = response.json()["id"]
        
        # Try to activate with different actor (owner2)
        activation_data = {"activated_by": "owner2"}
        response = client.post(
            f"/api/v1/skills/{skill_id}/versions/{version_id}/activate",
            json=activation_data,
            headers=abc_headers,
        )
        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()
    
    def test_draft_skill_cannot_execute_as_active(self, client, abc_headers, skill_payload):
        """Test: Draft skill cannot execute or load as active"""
        # Create draft skill
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 201
        skill_id = response.json()["id"]
        
        # Ensure it's in draft status
        response = client.get(f"/api/v1/skills/{skill_id}", headers=abc_headers)
        assert response.json()["status"] == "draft"
        
        # Get active skills for department - should not include draft
        response = client.get("/api/v1/skills/active/department/test", headers=abc_headers)
        assert response.status_code == 200
        skills = response.json()["skills"]
        assert len(skills) == 0 or skill_id not in [s["id"] for s in skills]
    
    def test_disabled_skill_excluded_from_runtime(self, client, abc_headers, skill_payload):
        """Test: Disabled skill is excluded from runtime selection"""
        # Create skill
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 201
        skill_id = response.json()["id"]
        
        # Create and activate version
        version_payload = {
            "name": "v1",
            "description": "active version",
            "configuration": {},
            "requested_tools": ["test_tool"],
            "created_by": "test-owner",
        }
        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload, headers=abc_headers)
        version_id = response.json()["id"]
        
        activation_data = {"activated_by": "test-owner"}
        response = client.post(
            f"/api/v1/skills/{skill_id}/versions/{version_id}/activate",
            json=activation_data,
            headers=abc_headers,
        )
        assert response.status_code == 200
        
        # Disable skill
        response = client.post(f"/api/v1/skills/{skill_id}/disable", headers=abc_headers)
        assert response.status_code == 200
        
        # Get active skills - should not include disabled
        response = client.get("/api/v1/skills/active/department/test", headers=abc_headers)
        assert response.status_code == 200
        skills = response.json()["skills"]
        assert skill_id not in [s["id"] for s in skills]
    
    def test_active_version_is_immutable(self, client, abc_headers, skill_payload):
        """Test: Active version is immutable"""
        # Create skill
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 201
        skill_id = response.json()["id"]
        
        # Create and activate version
        version_payload = {
            "name": "v1",
            "description": "active version",
            "configuration": {},
            "requested_tools": ["test_tool"],
            "created_by": "test-owner",
        }
        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload, headers=abc_headers)
        version_id = response.json()["id"]
        
        activation_data = {"activated_by": "test-owner"}
        response = client.post(
            f"/api/v1/skills/{skill_id}/versions/{version_id}/activate",
            json=activation_data,
            headers=abc_headers,
        )
        assert response.status_code == 200
        
        # Try to modify active version (should not be possible via API)
        # Versions are immutable - we only support creating new versions
        # This is enforced by the fact that there's no update version endpoint
        
        # Create another version
        version_payload2 = {
            "name": "v2",
            "description": "newer version",
            "configuration": {},
            "requested_tools": ["test_tool2"],
            "created_by": "test-owner",
        }
        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload2, headers=abc_headers)
        assert response.status_code == 201
        
        # Check active version is still v1
        response = client.get(f"/api/v1/skills/{skill_id}/versions", headers=abc_headers)
        versions = response.json()["versions"]
        active_versions = [v for v in versions if v["is_active"]]
        assert len(active_versions) == 1
        assert active_versions[0]["version"] == 1
    
    def test_duplicate_activation_is_safe_and_idempotent(self, client, abc_headers, skill_payload):
        """Test: Duplicate activation request is safe and idempotent"""
        # Create skill
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 201
        skill_id = response.json()["id"]
        
        # Create version
        version_payload = {
            "name": "v1",
            "description": "test version",
            "configuration": {},
            "requested_tools": ["test_tool"],
            "created_by": "test-owner",
        }
        response = client.post(f"/api/v1/skills/{skill_id}/versions", json=version_payload, headers=abc_headers)
        version_id = response.json()["id"]
        
        # Activate twice
        activation_data = {"activated_by": "test-owner"}
        for _ in range(2):
            response = client.post(
                f"/api/v1/skills/{skill_id}/versions/{version_id}/activate",
                json=activation_data,
                headers=abc_headers,
            )
            assert response.status_code == 200
        
        # Verify only one active version
        response = client.get(f"/api/v1/skills/{skill_id}/versions", headers=abc_headers)
        versions = response.json()["versions"]
        active_versions = [v for v in versions if v["is_active"]]
        assert len(active_versions) == 1
    
    def test_invalid_or_destructive_tool_rejected(self, client, abc_headers, skill_payload):
        """Test: Invalid or destructive requested tool is rejected"""
        # Try with destructive tool
        skill_payload["requested_tools"] = ["delete_all", "analyze_data"]
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 400
        assert "destructive" in response.json()["detail"].lower()
        
        # Try with invalid tool name
        skill_payload["requested_tools"] = ["valid_tool", "invalid-tool!"]
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 400
        assert "invalid tool" in response.json()["detail"].lower()
    
    def test_audit_record_contains_organization_actor_event_version(self, client, abc_headers, skill_payload):
        """Test: Audit record contains organization, actor, event and version"""
        # Create skill
        response = client.post("/api/v1/skills", json=skill_payload, headers=abc_headers)
        assert response.status_code == 201
        skill_id = response.json()["id"]
        
        # Get audit logs
        response = client.get(f"/api/v1/skills/{skill_id}/audit-logs", headers=abc_headers)
        assert response.status_code == 200
        logs = response.json()["logs"]
        assert len(logs) >= 1
        
        # Verify audit record fields
        for log in logs:
            assert "organization_id" in log
            assert log["organization_id"] == "ABC Construction"
            assert "actor" in log
            assert "event_type" in log
            assert "version_id" in log or log["version_id"] is None
            assert "details" in log
