def test_login_success(client):
    r = client.post("/admin/login", json={"password": "testpass"})
    assert r.status_code == 200
    assert "token" in r.json()
    assert r.json()["role"] == "admin"


def test_login_wrong_password(client):
    r = client.post("/admin/login", json={"password": "wrongpass"})
    assert r.status_code == 401


def test_login_empty_password(client):
    r = client.post("/admin/login", json={"password": ""})
    assert r.status_code == 401


def test_admin_panel_returns_html(client):
    r = client.get("/admin")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_protected_endpoint_requires_token(client):
    r = client.get("/admin/face-enrollments")
    assert r.status_code in (401, 403)


def test_protected_endpoint_with_token(client, auth_headers):
    r = client.get("/admin/face-enrollments", headers=auth_headers)
    assert r.status_code == 200
    assert "enrollments" in r.json()


def test_auto_token_blocked_when_password_set(client):
    r = client.get("/admin/auto-token")
    assert r.status_code == 403
