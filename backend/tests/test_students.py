"""
O'quvchilar ro'yxati: hammasi va test bo'yicha, qidiruv, viloyat/holat filtri, sahifalash.
"""
from datetime import timedelta

from sqlalchemy import func, select

from app.models.result import Result
from app.models.session import TestSession
from app.models.user import User
from app.utils.timer import now_uz
from tests.test_payments import _make_test, _start, client  # noqa: F401 - fixture
from tests.test_rasch_report import db  # noqa: F401 - fixture

URL = "/api/v1/admin/students/list"

PEOPLE = [
    (9001, "Jasur", "Ergashev", "Samarqand"),
    (9002, "Madina", "Rasulova", "Toshkent"),
    (9003, "Sardor", "Norbekov", "Samarqand"),
    (9004, "Sevara", "Turayeva", "Buxoro"),
    (9005, "Javohir", "Ergashev", "Toshkent"),
]


async def _register(client):
    users = {}
    for tg, name, surname, region in PEOPLE:
        r = await client.post("/api/v1/users/register", json={
            "telegram_id": tg, "full_name": name, "surname": surname, "region": region})
        assert r.status_code in (200, 201), r.text
        users[tg] = r.json()
    return users


async def _get(client, **params):
    r = await client.get(URL, params=params, headers=client.admin_headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_requires_admin(client):
    assert (await client.get(URL)).status_code in (401, 403)


async def test_all_students_pagination_and_filters(client):
    await _register(client)

    page1 = await _get(client, page_size=2)
    assert page1["total"] == 5 and page1["pages"] == 3 and len(page1["items"]) == 2
    page3 = await _get(client, page_size=2, page=3)
    assert len(page3["items"]) == 1
    seen = {i["telegram_id"] for p in (1, 2, 3) for i in (await _get(client, page_size=2, page=p))["items"]}
    assert seen == {p[0] for p in PEOPLE}

    # Sahifa raqami chegaradan oshsa, oxirgi sahifa qaytadi
    assert (await _get(client, page_size=2, page=99))["page"] == 3

    assert {i["telegram_id"] for i in (await _get(client, q="ergashev"))["items"]} == {9001, 9005}
    assert [i["telegram_id"] for i in (await _get(client, q="jasur erga"))["items"]] == [9001]
    assert [i["telegram_id"] for i in (await _get(client, q="9004"))["items"]] == [9004]

    samarqand = await _get(client, region="Samarqand")
    assert samarqand["total"] == 2
    assert samarqand["regions"] == ["Buxoro", "Samarqand", "Toshkent"]

    by_name = [i["surname"] for i in (await _get(client, sort="name"))["items"]]
    assert by_name == sorted(by_name)


async def test_tests_taken_and_balance(client):
    users = await _register(client)
    t1 = await _make_test(client, "STU1", 0)
    t2 = await _make_test(client, "STU2", 0)
    for test in (t1, t2):
        assert (await _start(client, users[9002]["id"], test["id"])).status_code == 201
    assert (await _start(client, users[9003]["id"], t1["id"])).status_code == 201

    items = {i["telegram_id"]: i for i in (await _get(client, sort="tests"))["items"]}
    assert items[9002]["tests_taken"] == 2
    assert items[9003]["tests_taken"] == 1
    assert items[9001]["tests_taken"] == 0
    assert items[9001]["balance"] == 0
    assert items[9001]["registered_at"].endswith("Z")
    assert (await _get(client, sort="tests"))["items"][0]["telegram_id"] == 9002


async def test_per_test_list_statuses_and_scores(client, db):  # noqa: F811
    users = await _register(client)
    test = await _make_test(client, "STU3", 0)
    other = await _make_test(client, "STU4", 0)
    for tg in (9001, 9002, 9003, 9004):
        assert (await _start(client, users[tg]["id"], test["id"])).status_code == 201
    assert (await _start(client, users[9005]["id"], other["id"])).status_code == 201

    sessions = {s.user_id: s for s in (await db.execute(
        select(TestSession).where(TestSession.test_id == test["id"]))).scalars()}
    by_tg = {u.telegram_id: u.id for u in (await db.execute(select(User))).scalars()}

    # 9001 topshirgan (ball 40), 9002 vaqti tugagan, 9003 va 9004 jarayonda
    done = sessions[by_tg[9001]]
    done.is_submitted = True
    db.add(Result(user_id=done.user_id, test_id=done.test_id, session_id=done.id,
                  mcq_score=30, written_score=10, total_score=40))
    sessions[by_tg[9002]].expires_at = now_uz() - timedelta(minutes=1)
    await db.commit()

    data = await _get(client, test_id=test["id"])
    assert data["summary"] == {"submitted": 1, "expired": 1, "in_progress": 2, "all": 4}
    assert data["total"] == 4
    assert 9005 not in {i["telegram_id"] for i in data["items"]}
    row = next(i for i in data["items"] if i["telegram_id"] == 9001)
    assert row["status"] == "submitted" and row["score"] == 40 and row["mcq_score"] == 30

    assert [i["telegram_id"] for i in (await _get(client, test_id=test["id"], status="submitted"))["items"]] == [9001]
    assert [i["telegram_id"] for i in (await _get(client, test_id=test["id"], status="expired"))["items"]] == [9002]
    in_progress = await _get(client, test_id=test["id"], status="in_progress", page_size=1)
    assert in_progress["total"] == 2 and in_progress["pages"] == 2

    assert (await _get(client, test_id=test["id"], sort="score"))["items"][0]["telegram_id"] == 9001

    # Qidiruv va viloyat filtri holat sonlariga ham ta'sir qiladi
    sam = await _get(client, test_id=test["id"], region="Samarqand")
    assert sam["summary"]["all"] == 2 and sam["regions"] == ["Buxoro", "Samarqand", "Toshkent"]
    assert (await _get(client, test_id=test["id"], q="sevara"))["summary"]["in_progress"] == 1


async def test_listing_changes_nothing(client, db):  # noqa: F811
    users = await _register(client)
    test = await _make_test(client, "STU5", 0)
    await _start(client, users[9001]["id"], test["id"])

    async def counts():
        return [(await db.execute(select(func.count()).select_from(m))).scalar_one()
                for m in (User, TestSession, Result)]

    before = await counts()
    await _get(client)
    await _get(client, test_id=test["id"], q="x", region="Toshkent", status="submitted", sort="score")
    assert await counts() == before


async def test_invalid_params_rejected(client):
    for params in ({"status": "deleted"}, {"sort": "drop"}, {"page_size": 1000}, {"page": 0}):
        r = await client.get(URL, params=params, headers=client.admin_headers)
        assert r.status_code == 422, params
