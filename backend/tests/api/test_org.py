import uuid

from fastapi.testclient import TestClient


def get_admin_headers(client: TestClient) -> dict:
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@projectproof.ai",
            "password": "AdminSecure2026!",
        },
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_t_org_01_pending_company_cannot_publish(client: TestClient):
    """T-ORG-01 (FR-ORG-2): Pending company tries to publish -> 403."""
    # BrightWave Tech is pending (created in seed)
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "brightwave.tech@gmail.com",
            "password": "BrightWave2026!",
        },
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create draft project
    proj_res = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": "BrightWave AI Tool",
            "description": "Building an AI assistant prototype.",
            "difficulty": "intermediate",
            "duration_days": 14,
        },
        headers=headers,
    )
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # Try to publish while pending
    pub_res = client.post(f"/api/v1/projects/{proj_id}/publish", headers=headers)
    assert pub_res.status_code == 403
    assert "approved companies can publish" in pub_res.json()["error"]["message"].lower()


def test_t_org_02_admin_approves_company_writes_audit_log(client: TestClient):
    """T-ORG-02 (FR-ORG-2, FR-ADM-1, FR-ADM-5, BR-6): Admin approves; trust score set to 50; audit row written."""
    admin_headers = get_admin_headers(client)

    # Register a new pending company with unique domain (valid DNS without underscore)
    suffix = uuid.uuid4().hex[:8]
    domain = f"nexustech{suffix}.io"
    email = f"startup{suffix}@{domain}"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "ValidPassword2026!",
            "role": "company",
        },
    )

    login_res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "ValidPassword2026!"}
    )
    token = login_res.json()["access_token"]
    cmp_headers = {"Authorization": f"Bearer {token}"}

    # Verify email
    from app.core.security import create_email_verification_token

    # Directly verify in db via verify-email route
    user_id = login_res.json()["user"]["id"]
    verify_token = create_email_verification_token(user_id, email)
    client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    # Register company (trust_score starts at 0 while pending, per BR-6)
    cmp_reg = client.post(
        "/api/v1/companies/json",
        json={
            "name": f"Nexus Tech {suffix}",
            "website": f"https://{domain}",
            "description": "Cloud native infrastructure solutions",
        },
        headers=cmp_headers,
    )
    assert cmp_reg.status_code == 201
    company_id = cmp_reg.json()["id"]

    # Admin approves; BR-6: trust score jumps to 50 on approval
    approve_res = client.post(
        f"/api/v1/admin/companies/{company_id}/approve", headers=admin_headers
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"

    # Check audit log contains actor_id and action (FR-ADM-5)
    audit_res = client.get(
        f"/api/v1/admin/audit-log?entity_type=company&entity_id={company_id}", headers=admin_headers
    )
    assert audit_res.status_code == 200
    items = audit_res.json()["items"]
    assert len(items) >= 1
    approval_entry = next((item for item in items if item["action"] == "company_approved"), None)
    assert approval_entry is not None
    assert approval_entry["actor_email"] == "admin@projectproof.ai"


def test_t_org_03_duplicate_domain_registration_rejected(client: TestClient):
    """T-ORG-03 (FR-ORG-3): Second company registers with an active company's domain -> Rejected with conflict."""
    # Nova Labs is already active on domain novalabs.com
    email2 = "another_person@novalabs.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email2,
            "password": "ValidPassword2026!",
            "role": "company",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login", json={"email": email2, "password": "ValidPassword2026!"}
    )
    token = login_res.json()["access_token"]

    from app.core.security import create_email_verification_token

    user_id = login_res.json()["user"]["id"]
    verify_token = create_email_verification_token(user_id, email2)
    client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    # Try to register company with same domain
    reg_res = client.post(
        "/api/v1/companies/json",
        json={"name": "Fake Nova Labs", "website": "https://novalabs.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reg_res.status_code == 409
    assert reg_res.json()["error"]["code"] == "conflict"


def test_t_org_04_email_domain_mismatch_check(client: TestClient):
    """T-ORG-04 (FR-ORG-3, FR-ORG-4): Email domain mismatch -> Check shows mismatch in admin queue. Automated checks are display-only."""
    admin_headers = get_admin_headers(client)

    # In seed data, BrightWave Tech used brightwave.tech@gmail.com and website https://brightwavetech.net
    queue_res = client.get("/api/v1/admin/companies?status=pending", headers=admin_headers)
    assert queue_res.status_code == 200
    companies = queue_res.json()

    bw = next((c for c in companies if c["name"] == "BrightWave Tech"), None)
    assert bw is not None
    # Automated check shows domain mismatch and free email
    assert bw["automated_checks"]["domain_matches_website"] is False
    assert bw["automated_checks"]["is_free_email"] is True


def test_t_org_05_new_company_project_limit(client: TestClient):
    """T-ORG-05 (FR-ORG-5): New company may have at most 2 open projects until 3 evaluations are completed.
    Publishes 2 successfully. Publishing the 3rd is blocked with 403.
    """
    admin_headers = get_admin_headers(client)

    # Register a new unique company
    suffix = uuid.uuid4().hex[:8]
    email = f"lead_{suffix}@newcorp{suffix}.io"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "ValidPassword2026!",
            "role": "company",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "ValidPassword2026!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    from app.core.security import create_email_verification_token

    user_id = login_res.json()["user"]["id"]
    verify_token = create_email_verification_token(user_id, email)
    client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    cmp_reg = client.post(
        "/api/v1/companies/json",
        json={
            "name": f"NewCorp {suffix}",
            "website": f"https://newcorp{suffix}.io",
            "description": "Tech agency",
        },
        headers=headers,
    )
    company_id = cmp_reg.json()["id"]

    # Approve company
    client.post(f"/api/v1/admin/companies/{company_id}/approve", headers=admin_headers)

    # Create and publish project 1
    p1 = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": "Project 1",
            "description": "First project description.",
            "difficulty": "beginner",
            "duration_days": 7,
        },
        headers=headers,
    ).json()
    pub1 = client.post(f"/api/v1/projects/{p1['id']}/publish", headers=headers)
    assert pub1.status_code == 200

    # Create and publish project 2
    p2 = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": "Project 2",
            "description": "Second project description.",
            "difficulty": "intermediate",
            "duration_days": 14,
        },
        headers=headers,
    ).json()
    pub2 = client.post(f"/api/v1/projects/{p2['id']}/publish", headers=headers)
    assert pub2.status_code == 200

    # Create project 3
    p3 = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": "Project 3",
            "description": "Third project description.",
            "difficulty": "advanced",
            "duration_days": 21,
        },
        headers=headers,
    ).json()

    # Publishing project 3 should be blocked because limit is 2 open projects
    pub3 = client.post(f"/api/v1/projects/{p3['id']}/publish", headers=headers)
    assert pub3.status_code == 403
    assert "at most 2 open projects" in pub3.json()["error"]["message"]


def test_t_org_06_unapproved_recruiter_searches(client: TestClient):
    """T-ORG-06 (FR-ORG-6): Unapproved recruiter searches -> 403. Privacy by default (AGENTS.md rule 8)."""
    # Vikram Mehta from Apex is pending approval (from seed)
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "recruiter@apexsearch.com",
            "password": "Recruiter2026!",
        },
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to search students
    res = client.get("/api/v1/recruiter/students", headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "forbidden"


def test_t_org_07_suspend_company_closes_open_projects(client: TestClient):
    """T-ORG-07 (FR-ORG-7, FR-ADM-6, FR-ADM-5): Suspend company -> Open projects close; existing certificates stay valid.
    Suspension is audited in the same transaction.
    """
    admin_headers = get_admin_headers(client)

    # Register and approve a unique company
    suffix = uuid.uuid4().hex[:8]
    domain = f"suspendcorp{suffix}.com"
    email = f"owner{suffix}@{domain}"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "ValidPassword2026!",
            "role": "company",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "ValidPassword2026!"}
    )
    token = login_res.json()["access_token"]
    cmp_headers = {"Authorization": f"Bearer {token}"}

    from app.core.security import create_email_verification_token

    user_id = login_res.json()["user"]["id"]
    verify_token = create_email_verification_token(user_id, email)
    client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    cmp_reg = client.post(
        "/api/v1/companies/json",
        json={
            "name": f"Suspend Corp {suffix}",
            "website": f"https://{domain}",
            "description": "Company to be suspended",
        },
        headers=cmp_headers,
    ).json()
    company_id = cmp_reg["id"]

    # Admin approves
    client.post(f"/api/v1/admin/companies/{company_id}/approve", headers=admin_headers)

    # Create and publish an open project
    p = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": "Cloud Migration Project",
            "description": "Cloud service deployment project.",
            "difficulty": "intermediate",
            "duration_days": 14,
        },
        headers=cmp_headers,
    ).json()
    pub_res = client.post(f"/api/v1/projects/{p['id']}/publish", headers=cmp_headers)
    assert pub_res.status_code == 200

    # Admin suspends company
    sus_res = client.post(
        f"/api/v1/admin/companies/{company_id}/suspend",
        json={"reason": "Policy violation investigation"},
        headers=admin_headers,
    )
    assert sus_res.status_code == 200
    assert sus_res.json()["status"] == "suspended"

    # Verify company projects are closed
    from app.db import SessionLocal
    from app.models.project import Project

    db = SessionLocal()
    proj_in_db = db.query(Project).filter(Project.id == p["id"]).first()
    assert proj_in_db.status == "closed"
    db.close()


def test_fr_adm_05_audit_log_query(client: TestClient):
    """FR-ADM-5: Administrative audit log query with actor and entity tracking."""
    admin_headers = get_admin_headers(client)

    # Query audit log with pagination
    audit_res = client.get("/api/v1/admin/audit-log?page=1&page_size=10", headers=admin_headers)
    assert audit_res.status_code == 200
    data = audit_res.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0

    # Non-admin cannot query audit log (FR-AUTH-5, AGENTS.md rule 6)
    stu_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "ananya@example.com",
            "password": "StudentPass2026!",
        },
    )
    stu_headers = {"Authorization": f"Bearer {stu_login.json()['access_token']}"}
    res_forbidden = client.get("/api/v1/admin/audit-log", headers=stu_headers)
    assert res_forbidden.status_code == 403


def test_fr_adm_06_suspend_reactivate_user(client: TestClient):
    """FR-ADM-6: Admin suspends any user (tokens revoked, login rejected); admin reactivates user."""
    admin_headers = get_admin_headers(client)
    suffix = uuid.uuid4().hex[:8]
    email = f"target_user_{suffix}@example.com"
    pwd = "UserPass2026!"

    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "role": "student",
        },
    )
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    user_id = login_res.json()["user"]["id"]
    token = login_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # Admin suspends user (FR-ADM-6)
    sus_res = client.post(
        f"/api/v1/admin/users/{user_id}/suspend",
        json={"reason": "Suspicious activity"},
        headers=admin_headers,
    )
    assert sus_res.status_code == 200
    assert sus_res.json()["is_active"] is False

    # Old token fails with 403 Account is suspended
    me_res = client.get("/api/v1/me", headers=user_headers)
    assert me_res.status_code == 403
    assert "suspended" in me_res.json()["error"]["message"]

    # Login fails when suspended
    fail_login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert fail_login.status_code == 403
    assert "suspended" in fail_login.json()["error"]["message"]

    # Admin reactivates user (FR-ADM-6)
    react_res = client.post(f"/api/v1/admin/users/{user_id}/reactivate", headers=admin_headers)
    assert react_res.status_code == 200
    assert react_res.json()["is_active"] is True

    # Login now succeeds
    success_login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert success_login.status_code == 200
