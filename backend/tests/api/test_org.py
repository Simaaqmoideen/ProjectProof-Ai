import uuid

from fastapi.testclient import TestClient


def get_admin_headers(client: TestClient) -> dict:
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@projectproof.ai",
        "password": "AdminSecure2026!",
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_t_org_01_pending_company_cannot_publish(client: TestClient):
    """T-ORG-01: Pending company tries to publish -> 403 (FR-ORG-2)."""
    # BrightWave Tech is pending (created in seed)
    login_res = client.post("/api/v1/auth/login", json={
        "email": "brightwave.tech@gmail.com",
        "password": "BrightWave2026!",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create draft project
    proj_res = client.post("/api/v1/companies/me/projects", json={
        "title": "BrightWave AI Tool",
        "description": "Building an AI assistant prototype.",
        "difficulty": "intermediate",
        "duration_days": 14,
    }, headers=headers)
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # Try to publish while pending
    pub_res = client.post(f"/api/v1/projects/{proj_id}/publish", headers=headers)
    assert pub_res.status_code == 403
    assert "approved companies can publish" in pub_res.json()["error"]["message"].lower()


def test_t_org_02_admin_approves_company_writes_audit_log(client: TestClient):
    """T-ORG-02: Admin approves; action written to audit log -> Status approved; audit row with actor (FR-ORG-2, NFR-4)."""
    admin_headers = get_admin_headers(client)

    # Register a new pending company with unique domain (valid DNS without underscore)
    suffix = uuid.uuid4().hex[:8]
    domain = f"nexustech{suffix}.io"
    email = f"startup{suffix}@{domain}"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "ValidPassword2026!",
        "role": "company",
    })

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword2026!"})
    token = login_res.json()["access_token"]
    cmp_headers = {"Authorization": f"Bearer {token}"}

    # Verify email
    from app.core.security import create_email_verification_token
    # Directly verify in db via verify-email route
    user_id = login_res.json()["user"]["id"]
    verify_token = create_email_verification_token(user_id, email)
    client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    # Register company
    cmp_reg = client.post("/api/v1/companies/json", json={
        "name": f"Nexus Tech {suffix}",
        "website": f"https://{domain}",
        "description": "Cloud native infrastructure solutions",
    }, headers=cmp_headers)
    assert cmp_reg.status_code == 201
    company_id = cmp_reg.json()["id"]

    # Admin approves
    approve_res = client.post(f"/api/v1/admin/companies/{company_id}/approve", headers=admin_headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"

    # Check audit log contains actor_id and action
    audit_res = client.get(f"/api/v1/admin/audit-log?entity_type=company&entity_id={company_id}", headers=admin_headers)
    assert audit_res.status_code == 200
    items = audit_res.json()["items"]
    assert len(items) >= 1
    approval_entry = next((item for item in items if item["action"] == "company_approved"), None)
    assert approval_entry is not None
    assert approval_entry["actor_email"] == "admin@projectproof.ai"


def test_t_org_03_duplicate_domain_registration_rejected(client: TestClient):
    """T-ORG-03: Second company registers with an active company's domain -> Rejected with conflict (FR-ORG-3)."""
    # Nova Labs is already active on domain novalabs.com
    email2 = "another_person@novalabs.com"
    client.post("/api/v1/auth/register", json={
        "email": email2,
        "password": "ValidPassword2026!",
        "role": "company",
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email2, "password": "ValidPassword2026!"})
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
    """T-ORG-04: Email domain mismatch -> Check shows mismatch in admin queue (FR-ORG-3)."""
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
    """T-ORG-05: New company publishes a third project -> Blocked with explanation (FR-ORG-5)."""
    admin_headers = get_admin_headers(client)

    # Register a new unique company
    suffix = uuid.uuid4().hex[:8]
    email = f"lead_{suffix}@newcorp{suffix}.io"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "ValidPassword2026!",
        "role": "company",
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword2026!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    from app.core.security import create_email_verification_token
    user_id = login_res.json()["user"]["id"]
    verify_token = create_email_verification_token(user_id, email)
    client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    cmp_reg = client.post("/api/v1/companies/json", json={
        "name": f"NewCorp {suffix}",
        "website": f"https://newcorp{suffix}.io",
        "description": "Tech agency",
    }, headers=headers)
    company_id = cmp_reg.json()["id"]

    # Approve company
    client.post(f"/api/v1/admin/companies/{company_id}/approve", headers=admin_headers)

    # Create and publish project 1
    p1 = client.post("/api/v1/companies/me/projects", json={
        "title": "Project 1",
        "description": "First project description.",
        "difficulty": "beginner",
        "duration_days": 7,
    }, headers=headers).json()
    pub1 = client.post(f"/api/v1/projects/{p1['id']}/publish", headers=headers)
    assert pub1.status_code == 200

    # Create and publish project 2
    p2 = client.post("/api/v1/companies/me/projects", json={
        "title": "Project 2",
        "description": "Second project description.",
        "difficulty": "intermediate",
        "duration_days": 14,
    }, headers=headers).json()
    pub2 = client.post(f"/api/v1/projects/{p2['id']}/publish", headers=headers)
    assert pub2.status_code == 200

    # Create project 3
    p3 = client.post("/api/v1/companies/me/projects", json={
        "title": "Project 3",
        "description": "Third project description.",
        "difficulty": "advanced",
        "duration_days": 21,
    }, headers=headers).json()

    # Publishing project 3 should be blocked because limit is 2 open projects
    pub3 = client.post(f"/api/v1/projects/{p3['id']}/publish", headers=headers)
    assert pub3.status_code == 403
    assert "at most 2 open projects" in pub3.json()["error"]["message"]


def test_t_org_06_unapproved_recruiter_searches(client: TestClient):
    """T-ORG-06: Unapproved recruiter searches -> 403 (FR-ORG-6)."""
    # Vikram Mehta from Apex is pending approval (from seed)
    login_res = client.post("/api/v1/auth/login", json={
        "email": "recruiter@apexsearch.com",
        "password": "Recruiter2026!",
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to search students
    res = client.get("/api/v1/recruiter/students", headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "forbidden"


def test_t_org_07_suspend_company_closes_open_projects(client: TestClient):
    """T-ORG-07: Suspend company -> Open projects close; existing certificates stay valid (FR-ORG-7)."""
    admin_headers = get_admin_headers(client)

    # Register and approve a unique company
    suffix = uuid.uuid4().hex[:8]
    domain = f"suspendcorp{suffix}.com"
    email = f"owner{suffix}@{domain}"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "ValidPassword2026!",
        "role": "company",
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword2026!"})
    token = login_res.json()["access_token"]
    cmp_headers = {"Authorization": f"Bearer {token}"}

    from app.core.security import create_email_verification_token
    user_id = login_res.json()["user"]["id"]
    verify_token = create_email_verification_token(user_id, email)
    client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    cmp_reg = client.post("/api/v1/companies/json", json={
        "name": f"Suspend Corp {suffix}",
        "website": f"https://{domain}",
        "description": "Company to be suspended",
    }, headers=cmp_headers).json()
    company_id = cmp_reg["id"]

    # Admin approves
    client.post(f"/api/v1/admin/companies/{company_id}/approve", headers=admin_headers)

    # Create and publish an open project
    p = client.post("/api/v1/companies/me/projects", json={
        "title": "Cloud Migration Project",
        "description": "Cloud service deployment project.",
        "difficulty": "intermediate",
        "duration_days": 14,
    }, headers=cmp_headers).json()
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
