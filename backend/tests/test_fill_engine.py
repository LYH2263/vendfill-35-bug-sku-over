from app.services.fill_engine import build_fill_lines, compute_gap, summarize

def test_gap_basic():
    assert compute_gap(20, 5, 0) == 15
    assert compute_gap(20, 10, 5) == 5

def test_no_negative_fill():
    lanes = [{"id": 1, "slot_no": "A1", "sku_name": "水", "capacity": 10, "stock": 12, "in_transit": 0}]
    lines = build_fill_lines(lanes)
    assert lines[0].fill_qty == 0
    assert lines[0].status == "overbooked"

def test_cap_by_gap():
    lanes = [{"id": 1, "slot_no": "A1", "sku_name": "水", "capacity": 20, "stock": 5, "in_transit": 0}]
    lines = build_fill_lines(lanes, requested={1: 100})
    assert lines[0].fill_qty == 15
    assert lines[0].gap == 15

def test_full_zero_fill():
    lanes = [{"id": 1, "slot_no": "A1", "sku_name": "水", "capacity": 10, "stock": 8, "in_transit": 2}]
    s = summarize(build_fill_lines(lanes))
    assert s["full_count"] == 1
    assert s["total_fill"] == 0

def _lane(i, slot, sku, cap, stock, transit=0):
    return {"id": i, "slot_no": slot, "sku_name": sku, "capacity": cap, "stock": stock, "in_transit": transit}

def test_sku_cap_truncates_in_slot_order():
    lanes = [
        _lane(1, "B1", "薯片", 12, 3, 2),  # 缺口 7，上限 5 → 补到 5
        _lane(2, "B2", "薯片", 10, 5),     # 合计已满 → 0
    ]
    lines = build_fill_lines(lanes, sku_caps={"薯片": 5})
    assert lines[0].fill_qty == 5
    assert lines[0].status == "need_fill"
    assert lines[1].fill_qty == 0
    assert lines[1].status == "sku_cap_full"
    assert lines[1].reason == "同品合计已满"
    assert sum(l.fill_qty for l in lines) <= 5

def test_sku_cap_partial_then_zero():
    lanes = [
        _lane(1, "B1", "薯片", 12, 5),   # 缺口 7 → 7，余 1
        _lane(2, "B2", "薯片", 10, 5),   # 缺口 5 → 截到 1
        _lane(3, "B3", "薯片", 8, 4),    # 触顶 → 0
    ]
    lines = build_fill_lines(lanes, sku_caps={"薯片": 8})
    assert [l.fill_qty for l in lines] == [7, 1, 0]
    assert [l.status for l in lines] == ["need_fill", "need_fill", "sku_cap_full"]
    assert sum(l.fill_qty for l in lines) == 8

def test_sku_cap_only_constrains_registered_sku():
    lanes = [_lane(1, "B1", "薯片", 12, 3, 2), _lane(2, "B2", "薯片", 10, 5)]
    lines = build_fill_lines(lanes, sku_caps={"可乐": 1})
    assert [l.fill_qty for l in lines] == [7, 5]
    assert all(l.status == "need_fill" for l in lines)

def test_sku_cap_keeps_full_and_overbooked_status():
    lanes = [
        _lane(1, "B1", "薯片", 10, 10),      # 满仓，不占合计额度
        _lane(2, "B2", "薯片", 10, 8, 5),    # 超占
        _lane(3, "B3", "薯片", 12, 5),       # 缺口 7 → 上限 3
    ]
    lines = build_fill_lines(lanes, sku_caps={"薯片": 3})
    assert lines[0].status == "full" and lines[0].reason == "满仓"
    assert lines[1].status == "overbooked"
    assert lines[2].fill_qty == 3 and lines[2].status == "need_fill"

def test_sku_cap_full_counted_separately_from_full():
    lanes = [
        _lane(1, "A1", "矿泉水", 10, 10),    # 单道满仓
        _lane(2, "B1", "薯片", 12, 3, 2),
        _lane(3, "B2", "薯片", 10, 5),
    ]
    s = summarize(build_fill_lines(lanes, sku_caps={"薯片": 5}))
    assert s["full_count"] == 1
    assert s["sku_cap_full_count"] == 1
    assert s["total_fill"] == 5
    assert s["total_fill"] == sum(l["fill_qty"] for l in s["lines"])
