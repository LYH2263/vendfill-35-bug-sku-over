"""API 级测试：同品合计补量上限的登记、校验、生成与持久化。
使用独立 sqlite 文件库，不影响开发库。"""
import os

_DB_PATH = "/tmp/vendfill_test_api.db"
if os.path.exists(_DB_PATH):
    os.remove(_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"  # 须在导入 app 前覆盖
os.environ["SEED_ON_EMPTY"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.models import Lane, Location, RefillOrder, Sale, SkuCap
from app.services.seed import seed_if_empty


@pytest.fixture()
def client():
    with TestClient(app) as c:  # lifespan: create_all
        db = SessionLocal()
        try:
            for t in (Sale, RefillOrder, SkuCap, Lane, Location):
                db.query(t).delete()
            db.commit()
        finally:
            db.close()
        yield c


def _make_location(lanes, code="VM-T1"):
    db = SessionLocal()
    try:
        loc = Location(code=code, name="测试点位", address="")
        db.add(loc)
        db.flush()
        for slot, sku, cap, stock, transit in lanes:
            db.add(Lane(location_id=loc.id, slot_no=slot, sku_name=sku,
                        capacity=cap, stock=stock, in_transit=transit))
        db.commit()
        return loc.id
    finally:
        db.close()


def _put_cap(client, loc_id, sku, cap):
    return client.put(f"/api/locations/{loc_id}/caps/{sku}", json={"cap": cap})


def test_cap_must_be_positive_and_state_unchanged(client):
    loc_id = _make_location([("B1", "薯片", 12, 3, 2)])
    assert _put_cap(client, loc_id, "薯片", 0).status_code == 400
    assert _put_cap(client, loc_id, "薯片", -3).status_code == 400
    assert client.get(f"/api/locations/{loc_id}/caps").json() == []  # 配置保持改前
    # 单据也未被改动：生成结果仍不受合计约束
    data = client.post(f"/api/refills/run?location_id={loc_id}").json()
    assert next(l for l in data["lines"] if l["slot_no"] == "B1")["fill_qty"] == 7


def test_upsert_persists_and_regenerate_follows_new_cap(client):
    loc_id = _make_location([("B1", "薯片", 12, 3, 2)])  # 缺口 7
    assert _put_cap(client, loc_id, "薯片", 5).status_code == 200
    # 重开仍在：新会话/新连接读到的仍是已登记上限
    with TestClient(app) as again:
        caps = again.get(f"/api/locations/{loc_id}/caps").json()
    assert caps == [{"id": caps[0]["id"], "location_id": loc_id, "sku_name": "薯片", "cap": 5}]

    data = client.post(f"/api/refills/run?location_id={loc_id}").json()
    assert next(l for l in data["lines"] if l["slot_no"] == "B1")["fill_qty"] == 5

    # 改上限后再生成必须跟新合计，禁止仍按旧上限超发
    assert _put_cap(client, loc_id, "薯片", 3).status_code == 200
    data = client.post(f"/api/refills/run?location_id={loc_id}").json()
    b1 = next(l for l in data["lines"] if l["slot_no"] == "B1")
    assert b1["fill_qty"] == 3
    assert data["total_fill"] == 3

    # 撤销登记后不再受合计约束
    assert client.delete(f"/api/locations/{loc_id}/caps/薯片").status_code == 200
    data = client.post(f"/api/refills/run?location_id={loc_id}").json()
    assert next(l for l in data["lines"] if l["slot_no"] == "B1")["fill_qty"] == 7


def test_combined_cap_zeroes_later_lanes_and_stays_out_of_full(client):
    loc_id = _make_location([
        ("A1", "矿泉水", 10, 10, 0),   # 单道满仓
        ("B1", "薯片", 12, 3, 2),      # 缺口 7
        ("B2", "薯片", 10, 5, 0),      # 缺口 5，合计触顶 → 0
        ("C1", "可乐", 8, 4, 0),       # 未登记上限，不受约束
    ])
    assert _put_cap(client, loc_id, "薯片", 5).status_code == 200
    data = client.post(f"/api/refills/run?location_id={loc_id}").json()
    by_slot = {l["slot_no"]: l for l in data["lines"]}

    assert by_slot["B1"]["fill_qty"] == 5
    assert by_slot["B2"]["fill_qty"] == 0
    assert by_slot["B2"]["status"] == "sku_cap_full"
    assert by_slot["B2"]["reason"] == "同品合计已满"
    assert by_slot["C1"]["fill_qty"] == 4  # 未登记上限的商品不受合计约束
    chips_total = by_slot["B1"]["fill_qty"] + by_slot["B2"]["fill_qty"]
    assert chips_total <= 5
    assert data["total_fill"] == sum(l["fill_qty"] for l in data["lines"])

    # 合计触顶不得与单道满仓并句：满仓接口只含 A1
    full = client.get(f"/api/refills/full?location_id={loc_id}").json()["lanes"]
    assert [l["slot_no"] for l in full] == ["A1"]

    summary = client.get(f"/api/refills/summary?location_id={loc_id}").json()
    assert summary["sku_cap_full_count"] == 1
    assert summary["full_count"] == 1
    assert summary["total_fill"] == data["total_fill"]


def test_seed_registers_chips_cap(client):
    db = SessionLocal()
    try:
        seed_if_empty(db)
        loc_id = db.query(Location).first().id
    finally:
        db.close()

    caps = client.get(f"/api/locations/{loc_id}/caps").json()
    assert {c["sku_name"]: c["cap"] for c in caps} == {"薯片": 5}

    data = client.post(f"/api/refills/run?location_id={loc_id}").json()
    chips = [l for l in data["lines"] if l["sku_name"] == "薯片"]
    b1 = next(l for l in chips if l["slot_no"] == "B1")
    assert b1["fill_qty"] == 5  # B1 理想缺口 7，只能补到上限 5
    assert sum(l["fill_qty"] for l in chips) <= 5
    assert all(l["fill_qty"] == 0 for l in chips if l["slot_no"] != "B1")  # 其它同名道（若有）为 0
    # 汇总总件数与小票各行之和一致
    summary = client.get(f"/api/refills/summary?location_id={loc_id}").json()
    assert summary["total_fill"] == sum(l["fill_qty"] for l in data["lines"])
