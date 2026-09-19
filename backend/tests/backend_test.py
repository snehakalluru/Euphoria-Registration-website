"""Backend tests for Euphoria Hackathon Registration Platform."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://euphoria-register.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@euphoria.dev"
ADMIN_PASSWORD = "Admin@12345"


# ---------- helpers ----------
def _uid(n=6):
    return uuid.uuid4().hex[:n].upper()


def _member(i, *, accommodation="day_scholar", hostel=None, overrides=None):
    tag = _uid(8)
    m = {
        "member_number": i,
        "name": f"Member {i} {tag}",
        "registration_number": f"REG{tag}{i}",
        "email": f"m{i}.{tag.lower()}@test.dev",
        "phone": f"9{tag[:9].replace('A','1').replace('B','2').replace('C','3').replace('D','4').replace('E','5').replace('F','6')}{i}",
        "gender": "Other",
        "year": "3",
        "branch": "CSE",
        "section": "A",
        "euphoria_id": f"EUP{tag}{i}",
        "accommodation_type": accommodation,
        "hostel": hostel,
    }
    if overrides:
        m.update(overrides)
    return m


def _payload(*, members=4, college_type="internal", accommodation="day_scholar",
             team_name=None, college_name=None, confirmation=True):
    tag = _uid()
    ms = []
    for i in range(1, members + 1):
        hostel = None
        acc = accommodation
        if college_type == "external":
            acc = None
        if acc == "hosteller":
            hostel = {
                "hostel_name": f"Hostel-{tag}",
                "room_number": f"R{i}",
                "warden_name": "Warden X",
                "warden_phone": "9876543210",
            }
        ms.append(_member(i, accommodation=acc, hostel=hostel))
    return {
        "team_name": team_name or f"Team {tag}",
        "college_type": college_type,
        "college_name": college_name if college_name is not None else (
            "Some External College" if college_type == "external" else None
        ),
        "members": ms,
        "confirmation_accepted": confirmation,
    }


def _extract_code(resp):
    """Get error code from either dict-detail or pydantic validation list."""
    try:
        j = resp.json()
    except Exception:
        return None
    d = j.get("detail")
    if isinstance(d, dict):
        return d.get("code")
    if isinstance(d, list):
        # pydantic errors -> look for our string codes in msg / ctx
        for e in d:
            msg = (e.get("msg") or "") + " " + str(e.get("ctx") or "")
            for code in ("HOSTEL_DETAILS_REQUIRED", "INVALID_ACCOMMODATION",
                         "CONFIRMATION_REQUIRED", "COLLEGE_NAME_REQUIRED",
                         "EMAIL_ALREADY_REGISTERED", "EUPHORIA_ID_ALREADY_REGISTERED",
                         "INVALID_MEMBER_SEQUENCE"):
                if code in msg:
                    return code
        # team size errors will report on 'members' with type too_short/too_long
        for e in d:
            if e.get("loc") and "members" in e["loc"] and e.get("type") in ("too_short", "too_long"):
                return "INVALID_TEAM_SIZE"
    return None


# ---------- health & content ----------
class TestHealth:
    def test_health(self):
        r = requests.get(f"{API}/health")
        assert r.status_code == 200
        assert r.json().get("success") is True


class TestContent:
    def test_hackathon(self):
        r = requests.get(f"{API}/hackathon")
        assert r.status_code == 200
        d = r.json()["data"]
        for k in ("name", "tagline", "rules", "eligibility", "instructions", "sdgGoals", "whatsappUrl"):
            assert k in d, f"missing {k}"
        assert len(d["sdgGoals"]) == 6

    def test_clubs(self):
        r = requests.get(f"{API}/clubs")
        assert r.status_code == 200
        clubs = r.json()["data"]
        assert len(clubs) == 5
        orders = [c["displayOrder"] for c in clubs]
        assert orders == sorted(orders)


# ---------- registration success ----------
class TestRegistrationSuccess:
    def test_create_4_members(self):
        p = _payload(members=4)
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 201, r.text
        rid = r.json()["data"]["registration_id"]
        assert rid.startswith("EUH26-") and len(rid) == 12
        # GET public
        g = requests.get(f"{API}/registrations/{rid}")
        assert g.status_code == 200
        data = g.json()["data"]
        assert data["team_name"] == p["team_name"]
        assert data["member_count"] == 4
        # no PII
        assert "members" not in data
        assert "email" not in data

    def test_create_5_members(self):
        p = _payload(members=5)
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 201, r.text
        assert r.json()["data"]["member_count"] == 5

    def test_get_registration_not_found(self):
        r = requests.get(f"{API}/registrations/INVALID")
        assert r.status_code == 404
        assert _extract_code(r) == "REGISTRATION_NOT_FOUND"


# ---------- registration validation ----------
class TestRegistrationValidation:
    def test_3_members_rejected(self):
        p = _payload(members=4)
        p["members"] = p["members"][:3]
        # renumber
        for i, m in enumerate(p["members"], 1):
            m["member_number"] = i
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 422
        assert _extract_code(r) == "INVALID_TEAM_SIZE"

    def test_6_members_rejected(self):
        p = _payload(members=5)
        extra = _member(6)
        p["members"].append(extra)
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 422
        assert _extract_code(r) == "INVALID_TEAM_SIZE"

    def test_external_missing_college_name(self):
        p = _payload(members=4, college_type="external", college_name=None)
        p["college_name"] = None
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 422
        assert _extract_code(r) == "COLLEGE_NAME_REQUIRED"

    def test_internal_missing_accommodation(self):
        p = _payload(members=4, college_type="internal")
        p["members"][0]["accommodation_type"] = None
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 422
        assert _extract_code(r) == "INVALID_ACCOMMODATION"

    def test_hosteller_missing_hostel_details(self):
        p = _payload(members=4)
        p["members"][0]["accommodation_type"] = "hosteller"
        p["members"][0]["hostel"] = None
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 422
        assert _extract_code(r) == "HOSTEL_DETAILS_REQUIRED"

    def test_day_scholar_with_hostel_rejected(self):
        p = _payload(members=4)
        p["members"][0]["accommodation_type"] = "day_scholar"
        p["members"][0]["hostel"] = {
            "hostel_name": "H", "room_number": "1", "warden_name": "W", "warden_phone": "9876543210"
        }
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 422
        assert _extract_code(r) == "INVALID_ACCOMMODATION"

    def test_confirmation_required(self):
        p = _payload(members=4, confirmation=False)
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 422
        assert _extract_code(r) == "CONFIRMATION_REQUIRED"

    def test_duplicate_email_within_payload(self):
        p = _payload(members=4)
        p["members"][1]["email"] = p["members"][0]["email"]
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 422
        assert _extract_code(r) == "EMAIL_ALREADY_REGISTERED"


# ---------- duplicate detection across teams ----------
class TestDuplicateDetection:
    @pytest.fixture(scope="class")
    def seed(self):
        p = _payload(members=4)
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 201, r.text
        return p

    def test_duplicate_team_name_case_insensitive(self, seed):
        p = _payload(members=4)
        p["team_name"] = "  " + seed["team_name"].upper() + "  "
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 409, r.text
        assert _extract_code(r) == "TEAM_NAME_ALREADY_EXISTS"

    def test_duplicate_euphoria_id(self, seed):
        p = _payload(members=4)
        p["members"][0]["euphoria_id"] = seed["members"][0]["euphoria_id"].lower()
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 409, r.text
        assert _extract_code(r) == "EUPHORIA_ID_ALREADY_REGISTERED"

    def test_duplicate_phone(self, seed):
        p = _payload(members=4)
        p["members"][0]["phone"] = seed["members"][0]["phone"]
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 409, r.text
        assert _extract_code(r) == "PHONE_ALREADY_REGISTERED"

    def test_duplicate_email(self, seed):
        p = _payload(members=4)
        p["members"][0]["email"] = seed["members"][0]["email"].upper()
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 409, r.text
        assert _extract_code(r) == "EMAIL_ALREADY_REGISTERED"

    def test_duplicate_registration_number(self, seed):
        p = _payload(members=4)
        p["members"][0]["registration_number"] = seed["members"][0]["registration_number"].lower()
        r = requests.post(f"{API}/registrations", json=p)
        assert r.status_code == 409, r.text
        assert _extract_code(r) == "REGISTRATION_NUMBER_ALREADY_REGISTERED"

    def test_participant_dup_within_payload_phone(self):
        p = _payload(members=4)
        p["members"][1]["phone"] = p["members"][0]["phone"]
        r = requests.post(f"{API}/registrations", json=p)
        # normalized phone dup detected in service -> 400
        assert r.status_code in (400, 409, 422)
        assert _extract_code(r) in ("PARTICIPANT_ALREADY_REGISTERED", "PHONE_ALREADY_REGISTERED")


# ---------- admin ----------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/admin/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


class TestAdmin:
    def test_login_success(self):
        r = requests.post(f"{API}/admin/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/admin/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "WrongPass!123"})
        assert r.status_code == 401
        assert _extract_code(r) == "INVALID_CREDENTIALS"

    def test_statistics_unauth(self):
        r = requests.get(f"{API}/admin/statistics")
        assert r.status_code == 401

    def test_statistics_ok(self, admin_token):
        r = requests.get(f"{API}/admin/statistics",
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        d = r.json()["data"]
        for k in ("totalTeams", "totalParticipants", "internalTeams", "externalTeams",
                  "fourMemberTeams", "fiveMemberTeams", "hostellers", "dayScholars"):
            assert k in d
            assert isinstance(d[k], int)

    def test_admin_registrations_list_and_filters(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{API}/admin/registrations", headers=h)
        assert r.status_code == 200
        j = r.json()
        assert "data" in j and "pagination" in j
        # filters
        for params in [{"college_type": "internal"}, {"team_size": 4}, {"accommodation": "day_scholar"}, {"search": "Test"}]:
            rr = requests.get(f"{API}/admin/registrations", headers=h, params=params)
            assert rr.status_code == 200, (params, rr.text)

    def test_admin_registration_detail(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        # create a fresh team
        p = _payload(members=4)
        cr = requests.post(f"{API}/registrations", json=p)
        assert cr.status_code == 201
        rid = cr.json()["data"]["registration_id"]
        r = requests.get(f"{API}/admin/registrations/{rid}", headers=h)
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["registrationId"] == rid
        assert len(d["members"]) == 4
        assert d["members"][0]["isTeamLead"] is True

    def test_admin_export_csv(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{API}/admin/registrations/export", headers=h)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert "Registration ID" in r.text.splitlines()[0]
