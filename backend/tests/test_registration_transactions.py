import asyncio
import sys
import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import get_db
from app.main import app
from app.models import Base, Hackathon, Team, TeamMember


def _member(tag: str, number: int, **overrides):
    phone_seed = "".join(str(ord(char) % 10) for char in tag)
    member = {
        "member_number": number,
        "name": f"Member {number} {tag}",
        "registration_number": f"ROLL-{tag}-{number}",
        "email": f"member{number}.{tag.lower()}@example.com",
        "phone": f"9{phone_seed}{number}".ljust(10, "0")[:10],
        "gender": "Male" if number % 2 else "Female",
        "year": "N/A",
        "branch": "N/A",
        "section": "N/A",
        "euphoria_id": f"EUPH-{tag}-{number}",
        "accommodation_type": "day_scholar",
    }
    member.update(overrides)
    return member


def _payload(tag: str | None = None):
    tag = tag or uuid.uuid4().hex[:8].upper()
    return {
        "team_name": f"Team {tag}",
        "college_type": "internal",
        "college_name": "",
        "confirmation_accepted": True,
        "members": [_member(tag, number) for number in range(1, 5)],
    }


def _code(response):
    body = response.json()
    return body.get("error", {}).get("code") or body.get("detail", {}).get("code")


def _message(response):
    body = response.json()
    return body.get("error", {}).get("message") or body.get("detail", {}).get("message")


async def _counts(factory):
    async with factory() as session:
        teams = len((await session.scalars(select(Team))).all())
        members = len((await session.scalars(select(TeamMember))).all())
        return teams, members


@pytest.fixture()
def registration_client(tmp_path):
    async def build():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'registration.db'}", echo=False)
        factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as session:
            session.add(Hackathon(id=uuid.uuid4(), name="Test Hackathon", slug=f"test-{uuid.uuid4().hex}", is_active=True))
            await session.commit()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        return client, factory, engine

    client, factory, engine = asyncio.run(build())
    try:
        yield client, factory
    finally:
        asyncio.run(client.aclose())
        app.dependency_overrides.pop(get_db, None)
        asyncio.run(engine.dispose())


def test_first_valid_registration_returns_201(registration_client):
    client, factory = registration_client
    payload = _payload("VALID001")

    response = asyncio.run(client.post("/api/registrations", json=payload))

    assert response.status_code == 201, response.text
    assert response.json()["data"]["team_name"] == payload["team_name"]
    assert asyncio.run(_counts(factory)) == (1, 4)


def test_hackathon_content_route_uses_database_session(registration_client):
    client, _ = registration_client

    response = asyncio.run(client.get("/api/hackathon"))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Test Hackathon"
    assert "sdgGoals" in body["data"]


def test_same_payload_returns_duplicate_team_409(registration_client):
    client, factory = registration_client
    payload = _payload("DUPTEAM1")

    assert asyncio.run(client.post("/api/registrations", json=payload)).status_code == 201
    response = asyncio.run(client.post("/api/registrations", json=payload))

    assert response.status_code == 409, response.text
    assert _code(response) == "DUPLICATE_TEAM"
    assert asyncio.run(_counts(factory)) == (1, 4)


def test_team_name_case_variation_returns_duplicate(registration_client):
    client, factory = registration_client
    payload = _payload("VIBECASE")
    payload["team_name"] = "Vibe coders"
    assert asyncio.run(client.post("/api/registrations", json=payload)).status_code == 201
    second = _payload("VIBECA2")
    second["team_name"] = "VIBE CODERS"

    response = asyncio.run(client.post("/api/registrations", json=second))

    assert response.status_code == 409, response.text
    assert _code(response) == "DUPLICATE_TEAM"
    assert asyncio.run(_counts(factory)) == (1, 4)


def test_team_name_whitespace_variation_returns_duplicate(registration_client):
    client, factory = registration_client
    payload = _payload("VIBESPC")
    payload["team_name"] = "Vibe coders"
    assert asyncio.run(client.post("/api/registrations", json=payload)).status_code == 201
    second = _payload("VIBESP2")
    second["team_name"] = "  Vibe   coders  "

    response = asyncio.run(client.post("/api/registrations", json=second))

    assert response.status_code == 409, response.text
    assert _code(response) == "DUPLICATE_TEAM"
    assert _message(response) == "Team name already exists. Please choose a different team name."
    assert asyncio.run(_counts(factory)) == (1, 4)


def test_duplicate_euphoria_id_returns_409(registration_client):
    client, factory = registration_client
    first = _payload("DUPEUPH1")
    assert asyncio.run(client.post("/api/registrations", json=first)).status_code == 201
    second = _payload("DUPEUPH2")
    second["members"][1]["euphoria_id"] = first["members"][0]["euphoria_id"].lower()

    response = asyncio.run(client.post("/api/registrations", json=second))

    assert response.status_code == 409, response.text
    assert _code(response) == "DUPLICATE_EUPHORIA_ID"
    assert asyncio.run(_counts(factory)) == (1, 4)


def test_duplicate_email_returns_409(registration_client):
    client, factory = registration_client
    first = _payload("DUPEMAIL")
    assert asyncio.run(client.post("/api/registrations", json=first)).status_code == 201
    second = _payload("DUPEMAI2")
    second["members"][2]["email"] = first["members"][0]["email"].upper()

    response = asyncio.run(client.post("/api/registrations", json=second))

    assert response.status_code == 409, response.text
    assert _code(response) == "DUPLICATE_EMAIL"
    assert _message(response) == "This email has already been registered."
    assert asyncio.run(_counts(factory)) == (1, 4)


def test_duplicate_phone_returns_409(registration_client):
    client, factory = registration_client
    first = _payload("DUPHONE1")
    assert asyncio.run(client.post("/api/registrations", json=first)).status_code == 201
    second = _payload("DUPHONE2")
    second["members"][3]["phone"] = first["members"][0]["phone"]

    response = asyncio.run(client.post("/api/registrations", json=second))

    assert response.status_code == 409, response.text
    assert _code(response) == "DUPLICATE_PHONE"
    assert _message(response) == "This phone number has already been registered."
    assert asyncio.run(_counts(factory)) == (1, 4)


def test_duplicate_registration_number_returns_409(registration_client):
    client, factory = registration_client
    first = _payload("DUPROLL1")
    assert asyncio.run(client.post("/api/registrations", json=first)).status_code == 201
    second = _payload("DUPROLL2")
    second["members"][0]["registration_number"] = first["members"][0]["registration_number"].lower()

    response = asyncio.run(client.post("/api/registrations", json=second))

    assert response.status_code == 409, response.text
    assert _code(response) == "DUPLICATE_REGISTRATION_NUMBER"
    assert _message(response) == "This registration/roll number is already registered."
    assert asyncio.run(_counts(factory)) == (1, 4)


def test_availability_checks_unique_values(registration_client):
    client, _ = registration_client

    checks = [
        ("team_name", "Fresh Team"),
        ("email", "fresh@example.com"),
        ("registration_number", "ROLL-FRESH-1"),
        ("phone", "9876543210"),
    ]

    for check_type, value in checks:
        response = asyncio.run(client.get("/api/registrations/check-availability", params={"type": check_type, "value": value}))
        assert response.status_code == 200, response.text
        assert response.json() == {"success": True, "available": True}


def test_availability_checks_existing_values_and_normalization(registration_client):
    client, _ = registration_client
    payload = _payload("AVAIL001")
    payload["team_name"] = "Vibe coders"
    assert asyncio.run(client.post("/api/registrations", json=payload)).status_code == 201

    checks = [
        ("team_name", "VIBE CODERS"),
        ("team_name", "  Vibe   coders  "),
        ("email", payload["members"][0]["email"].upper()),
        ("registration_number", payload["members"][1]["registration_number"].lower()),
        ("phone", payload["members"][2]["phone"]),
    ]

    for check_type, value in checks:
        response = asyncio.run(client.get("/api/registrations/check-availability", params={"type": check_type, "value": value}))
        assert response.status_code == 200, response.text
        assert response.json() == {"success": True, "available": False}


def test_availability_response_does_not_expose_existing_participant_details(registration_client):
    client, _ = registration_client
    payload = _payload("NOPII001")
    assert asyncio.run(client.post("/api/registrations", json=payload)).status_code == 201

    response = asyncio.run(client.get("/api/registrations/check-availability", params={"type": "email", "value": payload["members"][0]["email"].upper()}))

    assert response.status_code == 200, response.text
    assert response.json() == {"success": True, "available": False}


def test_availability_check_rejects_invalid_phone_format(registration_client):
    client, _ = registration_client

    response = asyncio.run(client.get("/api/registrations/check-availability", params={"type": "phone", "value": "98765abc10"}))

    assert response.status_code == 400, response.text
    assert _code(response) == "INVALID_PHONE"
    assert _message(response) == "Phone number must contain exactly 10 digits."


@pytest.mark.parametrize("phone", ["9876543210"])
def test_ten_digit_phone_is_valid(registration_client, phone):
    client, factory = registration_client
    payload = _payload("PHONEOK")
    payload["members"][0]["phone"] = phone

    response = asyncio.run(client.post("/api/registrations", json=payload))

    assert response.status_code == 201, response.text
    assert asyncio.run(_counts(factory)) == (1, 4)


@pytest.mark.parametrize("phone", ["987654321", "98765432101", "98765abc10", "98765-3210"])
def test_invalid_phone_rejected(registration_client, phone):
    client, factory = registration_client
    payload = _payload(f"BAD{uuid.uuid4().hex[:5].upper()}")
    payload["members"][0]["phone"] = phone

    response = asyncio.run(client.post("/api/registrations", json=payload))

    assert response.status_code == 422, response.text
    assert asyncio.run(_counts(factory)) == (0, 0)


def test_repeated_warden_name_and_phone_allowed(registration_client):
    client, factory = registration_client
    first = _payload("WARDEN01")
    second = _payload("WARDEN02")
    shared_hostel = {
        "hostel_name": "Shared Hostel",
        "room_number": "101",
        "warden_name": "Repeated Warden",
        "warden_phone": "9876543210",
    }
    for payload in (first, second):
        for member in payload["members"]:
            member["accommodation_type"] = "hosteller"
            member["hostel"] = {**shared_hostel, "room_number": f"{payload['team_name']}-{member['member_number']}"}

    first_response = asyncio.run(client.post("/api/registrations", json=first))
    second_response = asyncio.run(client.post("/api/registrations", json=second))

    assert first_response.status_code == 201, first_response.text
    assert second_response.status_code == 201, second_response.text
    assert asyncio.run(_counts(factory)) == (2, 8)


def test_failed_member_insert_rolls_back_complete_transaction(registration_client):
    client, factory = registration_client
    first = _payload("ROLLBACK")
    second = _payload("ROLLBAC2")
    second["members"][3]["email"] = first["members"][0]["email"]
    assert asyncio.run(client.post("/api/registrations", json=first)).status_code == 201

    response = asyncio.run(client.post("/api/registrations", json=second))

    assert response.status_code == 409, response.text
    async def check():
        async with factory() as session:
            second_team = await session.scalar(select(Team).where(Team.team_name == second["team_name"]))
            return second_team, await _counts(factory)
    second_team, counts = asyncio.run(check())
    assert second_team is None
    assert counts == (1, 4)


def test_concurrent_identical_registration_one_success_one_conflict(registration_client):
    client, factory = registration_client
    payload = _payload("CONCUR01")

    async def submit_twice():
        return await asyncio.gather(
            client.post("/api/registrations", json=payload),
            client.post("/api/registrations", json=payload),
        )

    responses = asyncio.run(submit_twice())
    statuses = sorted(response.status_code for response in responses)

    assert statuses == [201, 409], [response.text for response in responses]
    assert asyncio.run(_counts(factory)) == (1, 4)


def test_sequential_requests_reuse_engine_safely(registration_client):
    client, factory = registration_client

    first = asyncio.run(client.post("/api/registrations", json=_payload("SEQSAFE1")))
    second = asyncio.run(client.post("/api/registrations", json=_payload("SEQSAFE2")))

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert asyncio.run(_counts(factory)) == (2, 8)
