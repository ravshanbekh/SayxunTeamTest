"""
To'lov tizimi: pullik/bepul test, chek yuborish, admin tasdiqlashi, balans, cheklarni o'chirish.
"""
import os
from datetime import timedelta

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.models.admin import AdminUser
from app.models.payment import PaymentRequest
from app.models.test import Test
from app.services import payment_service
from app.utils.security import create_access_token, get_password_hash
from app.utils.timer import now_uz
from tests.test_rasch_report import db  # noqa: F401 - fixture

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
PDF = b"%PDF-1.4\n" + b"0" * 200
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 200


@pytest.fixture
async def client(db, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setattr(payment_service.settings, "UPLOAD_DIR", str(tmp_path))
    sent = []
    monkeypatch.setattr(payment_service, "send_telegram_message", lambda chat_id, text: sent.append((chat_id, text)))
    admin = AdminUser(username="pay_admin", password_hash=get_password_hash("secret1"), role="admin")
    db.add(admin)
    await db.commit()
    token = create_access_token({"sub": str(admin.id), "username": admin.username, "role": admin.role})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.admin_headers = {"Authorization": f"Bearer {token}"}
        c.sent = sent
        yield c


async def _make_test(client, code, price, end_time=None):
    body = {"test_code": code, "title": f"Test {code}", "test_type": "sertifikat", "price": price,
            "answer_key": {"mcq_answers": {str(i): "A" for i in range(1, 36)}, "written_questions": {}}}
    if end_time:
        body["end_time"] = end_time
    r = await client.post("/api/v1/tests/", json=body, headers=client.admin_headers)
    assert r.status_code == 201, r.text
    assert r.json()["price"] == price
    return r.json()


async def _make_user(client, telegram_id):
    r = await client.post("/api/v1/users/register", json={
        "telegram_id": telegram_id, "full_name": "Ali", "surname": "Valiyev", "region": "Toshkent"})
    assert r.status_code in (200, 201), r.text
    return r.json()


async def _submit(client, telegram_id, amount, content=PNG, test_id=None, name="chek.png"):
    data = {"telegram_id": str(telegram_id), "amount": str(amount)}
    if test_id:
        data["test_id"] = test_id
    return await client.post("/api/v1/payments/submit", data=data, files={"file": (name, content, "image/png")})


async def _start(client, user_id, test_id):
    return await client.post("/api/v1/sessions/start", json={"user_id": user_id, "test_id": test_id})


async def _balance(client, telegram_id):
    return (await client.get(f"/api/v1/payments/balance/{telegram_id}")).json()


async def test_free_test_needs_no_balance(client):
    test = await _make_test(client, "FREE1", 0)
    user = await _make_user(client, 1001)
    r = await _start(client, user["id"], test["id"])
    assert r.status_code == 201
    assert (await _balance(client, 1001))["balance"] == 0


async def test_paid_test_full_flow(client):
    test = await _make_test(client, "PAID1", 30000)
    user = await _make_user(client, 1002)

    r = await _start(client, user["id"], test["id"])
    assert r.status_code == 402
    detail = r.json()["detail"]
    assert detail["code"] == "INSUFFICIENT_BALANCE"
    assert detail["price"] == 30000 and detail["required"] == 30000

    r = await _submit(client, 1002, 30000, test_id=test["id"])
    assert r.status_code == 201
    assert (await _balance(client, 1002))["pending_amount"] == 30000

    # hali tasdiqlanmagan - kirish yo'q
    assert (await _start(client, user["id"], test["id"])).status_code == 402

    listing = (await client.get("/api/v1/admin/payments?status=pending", headers=client.admin_headers)).json()
    assert listing["counts"]["pending"] == 1
    item = listing["items"][0]
    assert item["user"]["telegram_id"] == 1002 and item["test"]["code"] == "PAID1" and item["has_file"]

    f = await client.get(f"/api/v1/admin/payments/{item['id']}/file", headers=client.admin_headers)
    assert f.status_code == 200 and f.content == PNG and f.headers["content-type"] == "image/png"

    r = await client.post("/api/v1/admin/payments/approve", json={"ids": [item["id"]]}, headers=client.admin_headers)
    assert r.json()["approved"] == 1
    assert (await _balance(client, 1002)) == {"balance": 30000, "pending_amount": 0}
    assert client.sent and client.sent[0][0] == 1002 and "tasdiqlandi" in client.sent[0][1] and "PAID1" in client.sent[0][1]

    r = await _start(client, user["id"], test["id"])
    assert r.status_code == 201
    assert (await _balance(client, 1002))["balance"] == 0

    # sessiyalar tozalanib qayta kirilsa, pul qayta yechilmaydi
    await client.delete(f"/api/v1/admin/sessions/{test['id']}", headers=client.admin_headers)
    assert (await _start(client, user["id"], test["id"])).status_code == 201
    assert (await _balance(client, 1002))["balance"] == 0


async def test_balance_covers_several_tests(client):
    t1 = await _make_test(client, "PAID2", 20000)
    t2 = await _make_test(client, "PAID3", 15000)
    user = await _make_user(client, 1003)
    await _submit(client, 1003, 30000)
    await client.post("/api/v1/admin/payments/approve-all", headers=client.admin_headers)
    assert (await _start(client, user["id"], t1["id"])).status_code == 201
    r = await _start(client, user["id"], t2["id"])
    assert r.status_code == 402 and r.json()["detail"]["required"] == 5000
    assert (await _balance(client, 1003))["balance"] == 10000


async def test_approve_with_amount_override_and_bulk(client):
    users = [await _make_user(client, 2000 + i) for i in range(4)]
    for i in range(4):
        assert (await _submit(client, 2000 + i, 10000 * (i + 1))).status_code == 201
    items = (await client.get("/api/v1/admin/payments", headers=client.admin_headers)).json()["items"]
    first, second = items[0], items[1]
    r = await client.post("/api/v1/admin/payments/approve",
                          json={"ids": [first["id"], second["id"]], "amounts": {first["id"]: 5000}},
                          headers=client.admin_headers)
    assert r.json()["approved"] == 2
    assert (await _balance(client, first["user"]["telegram_id"]))["balance"] == 5000
    r = await client.post("/api/v1/admin/payments/approve-all", headers=client.admin_headers)
    assert r.json()["approved"] == 2
    counts = (await client.get("/api/v1/admin/payments?status=all", headers=client.admin_headers)).json()["counts"]
    assert counts == {"pending": 0, "approved": 4, "rejected": 0}
    # qayta tasdiqlash ikki marta qo'shmaydi
    r = await client.post("/api/v1/admin/payments/approve", json={"ids": [first["id"]]}, headers=client.admin_headers)
    assert r.json()["approved"] == 0
    assert (await _balance(client, first["user"]["telegram_id"]))["balance"] == 5000
    assert len(users) == 4


async def test_reject_payment(client):
    await _make_user(client, 3001)
    await _submit(client, 3001, 50000, content=PDF, name="chek.pdf")
    item = (await client.get("/api/v1/admin/payments", headers=client.admin_headers)).json()["items"][0]
    assert item["content_type"] == "application/pdf"
    r = await client.post(f"/api/v1/admin/payments/{item['id']}/reject", json={"note": "Summa mos emas"},
                          headers=client.admin_headers)
    assert r.status_code == 200
    assert (await _balance(client, 3001)) == {"balance": 0, "pending_amount": 0}
    assert "tasdiqlanmadi" in client.sent[-1][1] and "Summa mos emas" in client.sent[-1][1]
    rejected = (await client.get("/api/v1/admin/payments?status=rejected", headers=client.admin_headers)).json()
    assert rejected["items"][0]["note"] == "Summa mos emas"


@pytest.mark.parametrize("content,amount,error", [
    (b"GIF89a....", 10000, "rasm"),
    (b"", 10000, "bo'sh"),
    (PNG, 500, "Summa"),
    (PNG, 999_999_999, "Summa"),
])
async def test_invalid_receipts(client, content, amount, error):
    await _make_user(client, 4001)
    r = await _submit(client, 4001, amount, content=content)
    assert r.status_code == 400 and error in r.json()["detail"]


async def test_pending_limit(client):
    await _make_user(client, 4002)
    for _ in range(payment_service.MAX_PENDING_PER_USER):
        assert (await _submit(client, 4002, 10000, content=JPG)).status_code == 201
    r = await _submit(client, 4002, 10000, content=JPG)
    assert r.status_code == 400


async def test_unknown_user_cannot_submit(client):
    assert (await _submit(client, 9999, 10000)).status_code == 404


async def test_admin_endpoints_require_auth(client):
    assert (await client.get("/api/v1/admin/payments")).status_code in (401, 403)
    assert (await client.post("/api/v1/admin/payments/approve-all")).status_code in (401, 403)


async def test_receipts_deleted_after_test_ends(client, db):  # noqa: F811
    end = (now_uz() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    test = await _make_test(client, "PAID4", 10000, end_time=end)
    await _make_user(client, 5001)
    await _make_user(client, 5002)
    await _submit(client, 5001, 10000, test_id=test["id"])
    await _submit(client, 5002, 10000, test_id=test["id"])
    items = (await client.get("/api/v1/admin/payments", headers=client.admin_headers)).json()["items"]
    await client.post("/api/v1/admin/payments/approve", json={"ids": [items[0]["id"]]}, headers=client.admin_headers)

    paths = {p.id: p.file_path for p in (await db.execute(select(PaymentRequest))).scalars().all()}
    assert all(os.path.exists(p) for p in paths.values())
    # test hali tugamagan - fayllar joyida
    assert await payment_service.purge_expired_receipts(db) == 0

    t = await db.get(Test, test["id"])
    t.end_time = now_uz() - timedelta(minutes=1)
    await db.commit()
    assert await payment_service.purge_expired_receipts(db) == 1   # faqat tasdiqlangani

    listing = (await client.get("/api/v1/admin/payments?status=all", headers=client.admin_headers)).json()
    by_status = {i["status"]: i for i in listing["items"]}
    assert by_status["approved"]["has_file"] is False
    assert by_status["pending"]["has_file"] is True   # tekshirilmagan chek o'chirilmaydi
    r = await client.get(f"/api/v1/admin/payments/{by_status['approved']['id']}/file", headers=client.admin_headers)
    assert r.status_code == 404


async def test_unlinked_receipt_deleted_after_retention(client, db):  # noqa: F811
    await _make_user(client, 6001)
    await _submit(client, 6001, 10000)
    await client.post("/api/v1/admin/payments/approve-all", headers=client.admin_headers)
    payment = (await db.execute(select(PaymentRequest))).scalars().first()
    assert await payment_service.purge_expired_receipts(db) == 0
    payment.reviewed_at = now_uz() - timedelta(days=payment_service.settings.RECEIPT_RETENTION_DAYS + 1)
    await db.commit()
    path = payment.file_path
    assert await payment_service.purge_expired_receipts(db) == 1
    assert not os.path.exists(path)


async def test_payment_settings(client):
    r = await client.put("/api/v1/admin/payment-settings", headers=client.admin_headers,
                         json={"card_number": "8600 1234 5678 9012", "card_holder": "Sayxun Team", "note": "Izohga ismingizni yozing"})
    assert r.status_code == 200
    info = (await client.get("/api/v1/payments/info")).json()
    assert info == {"card_number": "8600 1234 5678 9012", "card_holder": "Sayxun Team", "note": "Izohga ismingizni yozing"}
    await client.put("/api/v1/admin/payment-settings", headers=client.admin_headers, json={"note": ""})
    assert (await client.get("/api/v1/payments/info")).json()["card_number"] == "8600 1234 5678 9012"


async def test_toggle_price_makes_test_free(client):
    test = await _make_test(client, "PAID5", 25000)
    user = await _make_user(client, 7001)
    assert (await _start(client, user["id"], test["id"])).status_code == 402
    r = await client.patch(f"/api/v1/tests/{test['id']}", json={"price": 0}, headers=client.admin_headers)
    assert r.json()["price"] == 0
    assert (await _start(client, user["id"], test["id"])).status_code == 201
