"""Backend tests for File & Media storage integration (uploads/branding/media)."""
import io
import os
import struct
import uuid
import zlib

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://euphoria-register.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@euphoria.dev"
ADMIN_PASSWORD = "Admin@12345"


# ---------- helpers ----------
def _tiny_png() -> bytes:
    """Minimal valid 1x1 PNG."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00", 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _tiny_pdf() -> bytes:
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _uid(n=8):
    return uuid.uuid4().hex[:n].upper()


def _member(i, *, accommodation="day_scholar", hostel=None, id_proof=None):
    tag = _uid(8)
    m = {
        "member_number": i,
        "name": f"Member {i} {tag}",
        "registration_number": f"REG{tag}{i}",
        "email": f"m{i}.{tag.lower()}@test.dev",
        "phone": f"9{uuid.uuid4().int % 10**9:09d}{i}"[:15],
        "gender": "Other",
        "year": "3",
        "branch": "CSE",
        "section": "A",
        "euphoria_id": f"EUP{tag}{i}",
        "accommodation_type": accommodation,
        "hostel": hostel,
    }
    if id_proof is not None:
        m["id_proof"] = id_proof
    return m


def _extract_code(resp):
    try:
        j = resp.json()
    except Exception:
        return None
    d = j.get("detail")
    if isinstance(d, dict):
        return d.get("code")
    if isinstance(d, list):
        for e in d:
            msg = (e.get("msg") or "") + " " + str(e.get("ctx") or "")
            for c in ("TEAM_LEAD_ID_PROOF_REQUIRED", "INVALID_ACCOMMODATION",
                      "HOSTEL_DETAILS_REQUIRED", "CONFIRMATION_REQUIRED"):
                if c in msg:
                    return c
    return None


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/admin/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def uploaded_id_proof_png():
    files = {"file": ("id.png", _tiny_png(), "image/png")}
    r = requests.post(f"{API}/uploads/id-proof", files=files, timeout=60)
    assert r.status_code == 200, f"seed upload failed: {r.status_code} {r.text}"
    return r.json()["data"]


# ---------- ID-Proof upload (public) ----------
class TestIdProofUpload:
    def test_upload_png_success(self):
        files = {"file": ("id.png", _tiny_png(), "image/png")}
        r = requests.post(f"{API}/uploads/id-proof", files=files, timeout=60)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["success"] is True
        d = j["data"]
        for k in ("path", "filename", "content_type", "size"):
            assert k in d
        assert d["filename"] == "id.png"
        assert d["content_type"] == "image/png"
        assert d["path"].endswith(".png")
        assert d["size"] > 0

    def test_upload_pdf_success(self):
        files = {"file": ("id.pdf", _tiny_pdf(), "application/pdf")}
        r = requests.post(f"{API}/uploads/id-proof", files=files, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["content_type"] == "application/pdf"
        assert d["path"].endswith(".pdf")

    def test_upload_over_5mb_rejected(self):
        # 5MB + 1 byte
        big = b"\x00" * (5 * 1024 * 1024 + 1)
        files = {"file": ("big.png", big, "image/png")}
        r = requests.post(f"{API}/uploads/id-proof", files=files, timeout=120)
        assert r.status_code == 400, r.text
        assert _extract_code(r) == "UPLOAD_FAILED"

    def test_upload_unsupported_extension_rejected(self):
        files = {"file": ("malware.exe", b"MZ\x90\x00\x03\x00", "application/octet-stream")}
        r = requests.post(f"{API}/uploads/id-proof", files=files, timeout=60)
        assert r.status_code == 400, r.text
        assert _extract_code(r) == "UPLOAD_FAILED"


# ---------- Hackathon logo branding ----------
class TestHackathonLogo:
    def test_requires_auth(self):
        files = {"file": ("logo.png", _tiny_png(), "image/png")}
        r = requests.post(f"{API}/admin/branding/hackathon-logo", files=files, timeout=60)
        assert r.status_code == 401, r.text

    def test_upload_and_reflected_in_get_hackathon(self, admin_token):
        files = {"file": ("hack-logo.png", _tiny_png(), "image/png")}
        r = requests.post(f"{API}/admin/branding/hackathon-logo",
                          files=files,
                          headers={"Authorization": f"Bearer {admin_token}"},
                          timeout=60)
        assert r.status_code == 200, r.text
        path = r.json()["data"]["path"]
        assert path.endswith(".png")

        g = requests.get(f"{API}/hackathon")
        assert g.status_code == 200
        logo_url = g.json()["data"]["logoUrl"]
        assert logo_url and logo_url.endswith(path), f"logoUrl={logo_url}, path={path}"

        # media publicly serves it
        m = requests.get(f"{BASE_URL}{logo_url}")
        assert m.status_code == 200
        assert m.headers.get("content-type", "").startswith("image/")


# ---------- Club logo & rename ----------
class TestClubBranding:
    def test_club_logo_requires_auth(self):
        files = {"file": ("logo.png", _tiny_png(), "image/png")}
        r = requests.post(f"{API}/admin/branding/club-logo/euphoria-register",
                          files=files, timeout=60)
        assert r.status_code == 401, r.text

    def test_club_logo_upload_reflected_in_clubs(self, admin_token):
        files = {"file": ("gdg-logo.png", _tiny_png(), "image/png")}
        r = requests.post(f"{API}/admin/branding/club-logo/gdg-kare",
                          files=files,
                          headers={"Authorization": f"Bearer {admin_token}"},
                          timeout=60)
        assert r.status_code == 200, r.text
        path = r.json()["data"]["path"]

        g = requests.get(f"{API}/clubs")
        assert g.status_code == 200
        clubs = g.json()["data"]
        gdg = next((c for c in clubs if c["slug"] == "gdg-kare"), None)
        assert gdg is not None
        assert gdg["logoUrl"] and gdg["logoUrl"].endswith(path)

    def test_club_logo_unknown_slug_404(self, admin_token):
        files = {"file": ("logo.png", _tiny_png(), "image/png")}
        r = requests.post(f"{API}/admin/branding/club-logo/does-not-exist",
                          files=files,
                          headers={"Authorization": f"Bearer {admin_token}"},
                          timeout=60)
        assert r.status_code == 404, r.text
        assert _extract_code(r) == "CLUB_NOT_FOUND"

    def test_rename_club(self, admin_token):
        # snapshot existing club values first
        clubs = requests.get(f"{API}/clubs").json()["data"]
        gdg = next(c for c in clubs if c["slug"] == "gdg-kare")
        original_name = gdg["name"]

        new_name = f"{original_name} · Updated {_uid(4)}"
        r = requests.post(
            f"{API}/admin/branding/club/gdg-kare",
            data={"name": new_name, "faculty_in_charge": "Dr Faculty",
                  "student_in_charge": "Student Lead"},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        j = r.json()["data"]
        assert j["name"] == new_name
        assert j["facultyInCharge"] == "Dr Faculty"

        # verify via /api/clubs
        clubs2 = requests.get(f"{API}/clubs").json()["data"]
        gdg2 = next(c for c in clubs2 if c["slug"] == "gdg-kare")
        assert gdg2["name"] == new_name
        assert gdg2["facultyInCharge"] == "Dr Faculty"

        # restore original name (best-effort)
        requests.post(
            f"{API}/admin/branding/club/gdg-kare",
            data={"name": original_name,
                  "faculty_in_charge": gdg.get("facultyInCharge") or "",
                  "student_in_charge": gdg.get("studentInCharge") or ""},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )


# ---------- Media & admin file endpoints ----------
class TestMediaAndAdminFiles:
    def test_media_serves_image_after_id_proof_png(self, uploaded_id_proof_png):
        r = requests.get(f"{API}/media/{uploaded_id_proof_png['path']}", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")

    def test_media_invalid_path_404(self):
        r = requests.get(f"{API}/media/euphoria-hackathon/id-proofs/{uuid.uuid4()}.png", timeout=60)
        assert r.status_code == 404
        assert _extract_code(r) == "MEDIA_NOT_FOUND"

    def test_media_pdf_forbidden(self):
        # upload a PDF then try to fetch via /api/media
        files = {"file": ("id.pdf", _tiny_pdf(), "application/pdf")}
        u = requests.post(f"{API}/uploads/id-proof", files=files, timeout=60)
        assert u.status_code == 200, u.text
        path = u.json()["data"]["path"]
        r = requests.get(f"{API}/media/{path}", timeout=60)
        assert r.status_code == 403, r.text
        assert _extract_code(r) == "MEDIA_FORBIDDEN"

    def test_admin_files_requires_auth(self, uploaded_id_proof_png):
        r = requests.get(f"{API}/admin/files/{uploaded_id_proof_png['path']}", timeout=60)
        assert r.status_code == 401, r.text

    def test_admin_files_returns_bytes(self, admin_token, uploaded_id_proof_png):
        r = requests.get(f"{API}/admin/files/{uploaded_id_proof_png['path']}",
                         headers={"Authorization": f"Bearer {admin_token}"}, timeout=60)
        assert r.status_code == 200
        assert len(r.content) > 0
        # for PNG we uploaded → should be an image content-type
        assert r.headers.get("content-type", "").startswith("image/")


# ---------- Registration with id_proof enforcement ----------
def _basic_payload(members_count=4, with_lead_id_proof=None):
    tag = _uid()
    ms = []
    for i in range(1, members_count + 1):
        id_proof = None
        if i == 1 and with_lead_id_proof is not None:
            id_proof = with_lead_id_proof
        ms.append(_member(i, id_proof=id_proof))
    return {
        "team_name": f"Team {tag}",
        "college_type": "internal",
        "college_name": None,
        "members": ms,
        "confirmation_accepted": True,
    }


class TestRegistrationIdProof:
    def test_missing_team_lead_id_proof_rejected(self):
        p = _basic_payload(members_count=4, with_lead_id_proof=None)
        r = requests.post(f"{API}/registrations", json=p, timeout=30)
        assert r.status_code in (400, 422), r.text
        assert _extract_code(r) == "TEAM_LEAD_ID_PROOF_REQUIRED"

    def test_registration_with_id_proof_success_and_admin_detail(self, admin_token, uploaded_id_proof_png):
        id_proof = {
            "path": uploaded_id_proof_png["path"],
            "filename": uploaded_id_proof_png["filename"],
            "content_type": uploaded_id_proof_png["content_type"],
        }
        p = _basic_payload(members_count=4, with_lead_id_proof=id_proof)
        r = requests.post(f"{API}/registrations", json=p, timeout=30)
        assert r.status_code == 201, r.text
        rid = r.json()["data"]["registration_id"]
        assert rid.startswith("EUH26-")

        # admin detail includes idProof fields on member[0]
        d = requests.get(f"{API}/admin/registrations/{rid}",
                         headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
        assert d.status_code == 200, d.text
        members = d.json()["data"]["members"]
        lead = next(m for m in members if m["memberNumber"] == 1)
        assert lead["isTeamLead"] is True
        assert lead["idProofPath"] == id_proof["path"]
        assert lead["idProofFilename"] == id_proof["filename"]
        assert lead["idProofContentType"] == id_proof["content_type"]
        # non-lead members must not carry idProof
        non_leads = [m for m in members if m["memberNumber"] != 1]
        for m in non_leads:
            assert not m.get("idProofPath")
