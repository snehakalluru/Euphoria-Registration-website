"""Iteration 4: verify logo/name mapping fix + Postgres swap."""
import io
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"
ADMIN_EMAIL = "admin@euphoria.dev"
ADMIN_PASSWORD = "Admin@12345"

EXPECTED = [
    {"slug": "gfg-kare",   "name": "GFG Campus Body · KARE",      "logo_ends": "kwb4jxde_GFG%20LOGO.webp",                                              "logo_contains": "kwb4jxde"},
    {"slug": "acm-kare",   "name": "KARE ACM Student Chapter",    "logo_ends": "8f6z2auc_WhatsApp%20Image%202026-09-09%20at%209.58.21%20PM.jpeg",       "logo_contains": "8f6z2auc"},
    {"slug": "ieee-eds",   "name": "KARE IEEE Education Society", "logo_ends": "%282%29.jpeg",                                                          "logo_contains": "zaogaxa6"},
    {"slug": "acm-w-kare", "name": "KARE ACM-W",                  "logo_ends": "%281%29.jpeg",                                                          "logo_contains": "qop5o1eu"},
    {"slug": "gdg-kare",   "name": "GDG On Campus · KARE",        "logo_ends": "oje6iuak_image.png",                                                    "logo_contains": "oje6iuak"},
]


def _clubs():
    r = requests.get(f"{API}/clubs", timeout=15)
    assert r.status_code == 200
    return r.json()["data"]


def _uid(n=6):
    return uuid.uuid4().hex[:n].upper()


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/admin/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# --- Postgres swap ---
def test_env_has_postgres_url():
    with open("/app/backend/.env") as f:
        env = f.read()
    assert "postgresql+asyncpg" in env, "DATABASE_URL is not postgresql+asyncpg"


def test_health_ok():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    assert r.json().get("success") is True


# --- Logo/name mapping ---
def test_clubs_count_and_order():
    clubs = _clubs()
    assert len(clubs) == 5
    assert [c["displayOrder"] for c in clubs] == [1, 2, 3, 4, 5]
    assert [c["slug"] for c in clubs] == [e["slug"] for e in EXPECTED]


def test_no_old_partner_05_slug():
    slugs = [c["slug"] for c in _clubs()]
    assert "partner-05" not in slugs


@pytest.mark.parametrize("idx", list(range(5)))
def test_club_mapping(idx):
    club = _clubs()[idx]
    exp = EXPECTED[idx]
    assert club["slug"] == exp["slug"]
    assert club["name"] == exp["name"]
    logo = club["logoUrl"]
    # Accept either the original seed asset OR a re-uploaded club-logos path
    # (branding upload test in this suite may re-upload gdg-kare logo).
    seed_ok = exp["logo_contains"] in logo and logo.endswith(exp["logo_ends"])
    reupload_ok = f"/club-logos/{exp['slug']}/" in logo
    assert seed_ok or reupload_ok, f"logoUrl mismatch for {exp['slug']}: {logo}"


# --- Admin (Postgres seed) ---
def test_admin_login_returns_token(admin_token):
    assert isinstance(admin_token, str) and len(admin_token) > 20


def test_admin_statistics(admin_token):
    r = requests.get(f"{API}/admin/statistics",
                     headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    d = r.json()["data"]
    for k in ("totalTeams", "totalParticipants", "internalTeams", "externalTeams"):
        assert k in d and isinstance(d[k], int)


# --- Registration create + duplicate 409 (Postgres unique index) ---
def _member(i):
    tag = _uid(8)
    return {
        "member_number": i,
        "name": f"M{i} {tag}",
        "registration_number": f"REG{tag}{i}",
        "email": f"m{i}.{tag.lower()}@t.dev",
        "phone": f"9{tag[:8]}{i}".replace("A", "1").replace("B", "2").replace("C", "3")
                     .replace("D", "4").replace("E", "5").replace("F", "6")[:10],
        "gender": "Other",
        "year": "3",
        "branch": "CSE",
        "section": "A",
        "euphoria_id": f"EUP{tag}{i}",
        "accommodation_type": "day_scholar",
        "hostel": None,
    }


_PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf"
    b"\xc0\x00\x00\x00\x03\x00\x01\x8b\xf4V\xd7\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _upload_id_proof():
    files = {"file": (f"id_{_uid()}.png", io.BytesIO(_PNG_1x1), "image/png")}
    r = requests.post(f"{API}/uploads/id-proof", files=files, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    return {"path": d["path"], "filename": d["filename"], "content_type": d.get("content_type") or "image/png"}


def _payload(team_name=None):
    members = [_member(i) for i in range(1, 5)]
    members[0]["id_proof"] = _upload_id_proof()
    return {
        "team_name": team_name or f"PGTeam {_uid()}",
        "college_type": "internal",
        "college_name": None,
        "members": members,
        "confirmation_accepted": True,
    }


class TestRegistrationPG:
    created_rid = None
    team_name = None

    def test_create_registration(self):
        p = _payload()
        TestRegistrationPG.team_name = p["team_name"]
        r = requests.post(f"{API}/registrations", json=p, timeout=20)
        assert r.status_code == 201, r.text
        rid = r.json()["data"]["registration_id"]
        assert rid.startswith("EUH26-") and len(rid) == 12
        TestRegistrationPG.created_rid = rid

    def test_duplicate_team_name_returns_409(self):
        assert TestRegistrationPG.team_name is not None
        p = _payload(team_name=TestRegistrationPG.team_name.upper())
        r = requests.post(f"{API}/registrations", json=p, timeout=20)
        assert r.status_code == 409, r.text
        detail = r.json().get("detail")
        code = detail.get("code") if isinstance(detail, dict) else None
        assert code == "TEAM_NAME_ALREADY_EXISTS", detail

    def test_get_public_registration_no_pii(self):
        assert TestRegistrationPG.created_rid
        r = requests.get(f"{API}/registrations/{TestRegistrationPG.created_rid}", timeout=15)
        assert r.status_code == 200
        d = r.json()["data"]
        assert "members" not in d and "email" not in d

    def test_stats_after_create(self, admin_token):
        r = requests.get(f"{API}/admin/statistics",
                         headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["data"]["totalTeams"] >= 1


# --- Uploads still work ---
def test_upload_id_proof():
    files = {"file": (f"id_{_uid()}.png", io.BytesIO(_PNG_1x1), "image/png")}
    r = requests.post(f"{API}/uploads/id-proof", files=files, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j.get("success") is True
    data = j.get("data") or {}
    assert "path" in data and "filename" in data


def test_branding_upload_gdg_kare_logo(admin_token):
    files = {"file": (f"logo_{_uid()}.png", io.BytesIO(_PNG_1x1), "image/png")}
    r = requests.post(
        f"{API}/admin/branding/club-logo/gdg-kare",
        headers={"Authorization": f"Bearer {admin_token}"},
        files=files, timeout=30,
    )
    assert r.status_code == 200, r.text
    club = next((c for c in _clubs() if c["slug"] == "gdg-kare"), None)
    assert club is not None
    # After branding upload, logoUrl should reflect uploaded asset path
    assert club["logoUrl"], "logoUrl empty after upload"
