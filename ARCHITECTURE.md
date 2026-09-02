# Architecture notes

The system follows a simple multi-tenant boundary model centered on `organization_id`.

- The database uses PostgreSQL with async SQLAlchemy sessions.
- Each API route reads the authenticated user from the JWT and validates the routed organization against that JWT.
- Skill operations are isolated at the organization level and access is denied if the user and skill do not share the same organization.
- Skill lifecycle transitions are recorded as audit events with organization, actor, event type, and version metadata.
- Ownership checks are enforced for activation and disabling so only an organization owner can affect the runtime state of a skill.

This keeps the prototype aligned with the evaluation’s requirement for strict tenant isolation without introducing cross-tenant admin shortcuts.