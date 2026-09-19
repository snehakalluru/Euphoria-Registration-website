"""Retest for GFG rename bug fix - verifies club slug/name changed from gdg-kare to gfg-kare."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://euphoria-register.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@euphoria.dev"
ADMIN_PASSWORD = "Admin@12345"

EXPECTED_SLUGS = ["gfg-kare", "acm-kare", "ieee-eds", "acm-w-kare", "partner-05"]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/admin/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    assert tok
    return tok


def _clubs():
    r = requests.get(f"{BASE_URL}/api/clubs")
    assert r.status_code == 200
    body = r.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


def test_clubs_list_first_is_gfg():
    clubs = _clubs()
    assert isinstance(clubs, list)
    assert len(clubs) == 5, f"expected 5 clubs, got {len(clubs)}"
    first = clubs[0]
    assert first["slug"] == "gfg-kare", f"first slug should be gfg-kare, got {first.get('slug')}"
    assert first["name"] == "GFG Campus Body · KARE", f"first name mismatch: {first.get('name')}"
    # displayOrder ordering 1..5
    orders = [c.get("displayOrder") for c in clubs]
    assert orders == [1, 2, 3, 4, 5], f"displayOrder mismatch: {orders}"
    # slugs order
    slugs = [c["slug"] for c in clubs]
    assert slugs == EXPECTED_SLUGS, f"slugs order mismatch: {slugs}"
    # logo url references GFG LOGO
    logo = first.get("logoUrl", "")
    assert "GFG" in logo or "gfg" in logo.lower(), f"logoUrl should reference GFG asset: {logo}"


def test_no_old_gdg_slug():
    slugs = [c["slug"] for c in _clubs()]
    assert "gdg-kare" not in slugs


def test_admin_login_and_stats(admin_token):
    r = requests.get(f"{BASE_URL}/api/admin/statistics",
                     headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"stats failed: {r.status_code} {r.text}"


def test_branding_rename_gfg_kare(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Rename to Test Rename
    r = requests.post(f"{BASE_URL}/api/admin/branding/club/gfg-kare",
                      headers=headers, data={"name": "Test Rename"})
    assert r.status_code == 200, f"rename failed: {r.status_code} {r.text}"

    # Verify persisted
    club = next((c for c in _clubs() if c["slug"] == "gfg-kare"), None)
    assert club is not None
    assert club["name"] == "Test Rename", f"rename not persisted: {club.get('name')}"

    # Restore
    r3 = requests.post(f"{BASE_URL}/api/admin/branding/club/gfg-kare",
                      headers=headers, data={"name": "GFG Campus Body · KARE"})
    assert r3.status_code == 200

    club = next((c for c in _clubs() if c["slug"] == "gfg-kare"), None)
    assert club["name"] == "GFG Campus Body · KARE"
