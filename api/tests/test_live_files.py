import base64
import os
import pytest


def _b64(content: bytes) -> str:
    return base64.b64encode(content).decode()


@pytest.fixture(autouse=True)
def patch_live_files_dir(tmp_path, monkeypatch):
    import api.routes.live_files as lf_mod
    monkeypatch.setattr(lf_mod, "LIVE_FILES_DIR", str(tmp_path / "live_files"))


def test_get_live_file_missing(client, auth_headers):
    r = client.get("/admin/live-file/Econs/week1", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() is None


def test_upload_and_get_live_file(client, auth_headers):
    payload = {
        "course": "Econs",
        "week": "week1",
        "filename": "notes.pdf",
        "content_type": "application/pdf",
        "data_base64": _b64(b"%PDF-1.4 fake"),
    }
    r = client.post("/admin/live-file", json=payload, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r2 = client.get("/admin/live-file/Econs/week1", headers=auth_headers)
    assert r2.status_code == 200
    meta = r2.json()
    assert meta["filename"] == "notes.pdf"
    assert meta["content_type"] == "application/pdf"


def test_delete_live_file(client, auth_headers):
    payload = {
        "course": "Econs",
        "week": "week2",
        "filename": "slides.pdf",
        "content_type": "application/pdf",
        "data_base64": _b64(b"%PDF-1.4 slides"),
    }
    client.post("/admin/live-file", json=payload, headers=auth_headers)

    r = client.delete("/admin/live-file/Econs/week2", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"

    r2 = client.get("/admin/live-file/Econs/week2", headers=auth_headers)
    assert r2.json() is None


def test_delete_nonexistent_live_file(client, auth_headers):
    r = client.delete("/admin/live-file/Econs/week99", headers=auth_headers)
    assert r.status_code == 404


def test_upload_requires_auth(client):
    payload = {
        "course": "Econs",
        "week": "week1",
        "filename": "notes.pdf",
        "content_type": "application/pdf",
        "data_base64": _b64(b"data"),
    }
    r = client.post("/admin/live-file", json=payload)
    assert r.status_code in (401, 403)


def test_live_file_info_public(client, auth_headers):
    payload = {
        "course": "Econs",
        "week": "week3",
        "filename": "info.pdf",
        "content_type": "application/pdf",
        "data_base64": _b64(b"%PDF-1.4 info"),
    }
    client.post("/admin/live-file", json=payload, headers=auth_headers)
    r = client.get("/live-file-info/Econs/week3")
    assert r.status_code == 200
    assert r.json()["filename"] == "info.pdf"
