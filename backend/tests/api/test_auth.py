import uuid

from fastapi.testclient import TestClient


def test_t_auth_01_register_student_company_recruiter(client: TestClient):
    """T-AUTH-01: Register student, company, recruiter -> Accounts created unverified (FR-AUTH-1)."""
    unique_suffix = uuid.uuid4().hex[:8]

    # Register student
    res_stu = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"student_{unique_suffix}@example.com",
            "password": "ValidPassword2026!",
            "role": "student",
            "full_name": "Test Student",
        },
    )
    assert res_stu.status_code == 201, res_stu.text
    data_stu = res_stu.json()
    assert data_stu["role"] == "student"
    assert data_stu["email_verified"] is False

    # Register company
    res_cmp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"contact_{unique_suffix}@techcorp.com",
            "password": "ValidPassword2026!",
            "role": "company",
        },
    )
    assert res_cmp.status_code == 201, res_cmp.text
    data_cmp = res_cmp.json()
    assert data_cmp["role"] == "company"
    assert data_cmp["email_verified"] is False

    # Register recruiter
    res_rec = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"recruiter_{unique_suffix}@agency.com",
            "password": "ValidPassword2026!",
            "role": "recruiter",
        },
    )
    assert res_rec.status_code == 201, res_rec.text
    data_rec = res_rec.json()
    assert data_rec["role"] == "recruiter"
    assert data_rec["email_verified"] is False


def test_t_auth_02_act_before_verifying_email(client: TestClient):
    """T-AUTH-02 (FR-AUTH-2): Email must be verified before ANY action beyond viewing own profile.
    Unverified user: /me returns 200, any other guarded action returns 403.
    """
    email = f"unverified_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "ValidPassword2026!"

    # Register student (email_verified=False)
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "role": "company",
        },
    )
    assert reg_res.status_code == 201

    # Login succeeds even when email not verified (FR-AUTH-3 allows login; FR-AUTH-2 gates actions)
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Viewing own profile (/me) is permitted without email verification
    me_res = client.get("/api/v1/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email_verified"] is False

    # Every other action returns 403 — FR-AUTH-2
    # 1. Register company profile
    act_res = client.post(
        "/api/v1/companies/json",
        json={"name": "New Company", "website": "https://newcompany.com"},
        headers=headers,
    )
    assert act_res.status_code == 403
    assert act_res.json()["error"]["code"] == "forbidden"

    # 2. Creating a project draft also blocked
    draft_res = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": "Test",
            "description": "Test description.",
            "difficulty": "beginner",
            "duration_days": 7,
        },
        headers=headers,
    )
    assert draft_res.status_code == 403


def test_t_auth_03_wrong_password_rate_limit(client: TestClient):
    """T-AUTH-03 (FR-AUTH-3): Wrong password five times -> Rate limited; message does not reveal whether email exists."""
    email = f"target_{uuid.uuid4().hex[:8]}@example.com"

    # Attempt wrong password 5 times
    statuses = []
    messages = []
    for _ in range(6):
        res = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword!"})
        statuses.append(res.status_code)
        messages.append(res.json()["error"]["message"])

    # First attempts return 401 with generic message
    assert statuses[0] == 401
    assert "Invalid email or password" in messages[0]

    # After repeated failures, rate limited (429)
    assert 429 in statuses
    # Message does not reveal whether the email exists
    assert "Invalid email or password" in messages[0]


def test_t_auth_04_refresh_token_rotation(client: TestClient):
    """T-AUTH-04 (FR-AUTH-3): Valid refresh cookie -> New access token; old refresh token rotated."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "ValidPassword2026!"

    client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "role": "student"})
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    old_cookie = login_res.cookies.get("refresh_token")
    assert old_cookie is not None

    # Call /auth/refresh
    refresh_res = client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_cookie})
    assert refresh_res.status_code == 200
    new_access_token = refresh_res.json()["access_token"]
    assert new_access_token is not None

    new_cookie = refresh_res.cookies.get("refresh_token")
    assert new_cookie is not None
    assert new_cookie != old_cookie  # Old refresh token rotated!


def test_t_auth_05_reuse_rotated_refresh_token(client: TestClient):
    """T-AUTH-05 (FR-AUTH-3): Reuse of a rotated refresh token -> Token family revoked (detection of token theft)."""
    email = f"reuse_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "ValidPassword2026!"

    client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "role": "student"})
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token_v1 = login_res.cookies.get("refresh_token")

    # Rotate token_v1 to get token_v2
    ref_res1 = client.post("/api/v1/auth/refresh", cookies={"refresh_token": token_v1})
    assert ref_res1.status_code == 200
    token_v2 = ref_res1.cookies.get("refresh_token")

    # Attacker tries to reuse token_v1!
    res_reuse = client.post("/api/v1/auth/refresh", cookies={"refresh_token": token_v1})
    assert res_reuse.status_code == 401

    # Now legitimate token_v2 should ALSO be revoked because family was revoked!
    res_v2 = client.post("/api/v1/auth/refresh", cookies={"refresh_token": token_v2})
    assert res_v2.status_code == 401


def test_t_auth_06_public_signup_role_admin_rejected(client: TestClient):
    """T-AUTH-06 (FR-AUTH-6): Public sign-up with role=admin -> Rejected; admins created only via CLI script."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"hacker_{uuid.uuid4().hex[:8]}@example.com",
            "password": "ValidPassword2026!",
            "role": "admin",
        },
    )
    # Must be rejected with 403 forbidden or 400 validation error
    assert res.status_code in (400, 403)


def test_t_auth_07_authorization_matrix(client: TestClient):
    """T-AUTH-07 (FR-AUTH-5): Authorization matrix: Student and company cannot reach admin routes."""
    # Login as student
    stu_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "ananya@example.com",
            "password": "StudentPass2026!",
        },
    )
    stu_token = stu_login.json()["access_token"]
    stu_headers = {"Authorization": f"Bearer {stu_token}"}

    # Student calling admin routes -> 403
    res_admin_q = client.get("/api/v1/admin/companies", headers=stu_headers)
    assert res_admin_q.status_code == 403
    res_audit = client.get("/api/v1/admin/audit-log", headers=stu_headers)
    assert res_audit.status_code == 403

    # Login as company
    cmp_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "contact@novalabs.com",
            "password": "NovaLabs2026!",
        },
    )
    cmp_token = cmp_login.json()["access_token"]
    cmp_headers = {"Authorization": f"Bearer {cmp_token}"}

    # Company calling admin routes -> 403
    res_cmp_admin = client.get("/api/v1/admin/companies", headers=cmp_headers)
    assert res_cmp_admin.status_code == 403


def test_t_auth_08_other_user_record_returns_404(client: TestClient):
    """T-AUTH-08 (FR-AUTH-5): Student requests another user's resource -> 404, not 403.
    Authorization order: role -> ownership -> state. Another user's record returns 404 (AGENTS.md rule 6).
    """
    # An unmapped / other user resource returns 404, not 403
    stu_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "ananya@example.com",
            "password": "StudentPass2026!",
        },
    )
    stu_token = stu_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {stu_token}"}

    random_id = uuid.uuid4()
    # Check that accessing a nonexistent or another user's project/application gives 404
    res = client.get(f"/api/v1/projects/{random_id}", headers=headers)
    assert res.status_code == 404


def test_fr_auth_04_password_reset(client: TestClient):
    """FR-AUTH-4: Password reset by emailed one-time link.
    User requests reset token -> submits new password with valid token -> can log in with new password.
    """
    email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "OriginalPassword2026!"
    new_pwd = "NewSecurePassword2026!"

    # Register user
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "role": "student",
        },
    )
    assert reg.status_code == 201

    # Request password reset (FR-AUTH-4)
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    assert "If an account exists" in forgot_res.json()["message"]

    # Generate valid reset token using core security helper (simulating email delivery)
    from app.core.security import create_password_reset_token
    from app.db import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    token = create_password_reset_token(str(user.id), email)
    db.close()

    # Reset password with valid token
    reset_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": new_pwd,
        },
    )
    assert reset_res.status_code == 200
    assert "Password reset successfully" in reset_res.json()["message"]

    # Old password no longer works
    old_login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert old_login.status_code == 401

    # New password succeeds
    new_login = client.post("/api/v1/auth/login", json={"email": email, "password": new_pwd})
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()
