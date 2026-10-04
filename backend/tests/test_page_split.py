from app.services.page_split import present_full, present_summary, present_ticket


def test_summary_uses_actual_fill_qty_and_status_counts():
    payload = {
        "id": 9,
        "lines": [
            {"lane_id": 1, "gap": 7, "fill_qty": 4, "status": "need_fill"},
            {"lane_id": 2, "gap": 0, "fill_qty": 0, "status": "full"},
            {"lane_id": 3, "gap": 5, "fill_qty": 0, "status": "sku_cap_full"},
        ],
        "overbooked_count": 0,
    }
    s = present_summary(1, payload)
    # 总量以各行实际补量为准（不是缺口之和），与小票对得上
    assert s["total_fill"] == 4
    assert s["need_fill_count"] == 1
    assert s["full_count"] == 1
    assert s["sku_cap_full_count"] == 1
    assert s["max_fill_qty"] == 0


def test_full_list_keeps_zero_fill_and_blocked_labels():
    payload = {
        "lines": [
            {"lane_id": 1, "fill_qty": 0, "status": "blocked", "reason": "货道封锁"},
            {"lane_id": 2, "fill_qty": 3, "status": "need_fill", "reason": ""},
            {"lane_id": 3, "fill_qty": 0, "status": "overbooked", "reason": "超占"},
            {"lane_id": 4, "fill_qty": 0, "status": "sku_cap_full", "reason": "同品合计已满"},
        ]
    }
    body = present_full(1, payload)
    ids = {l["lane_id"] for l in body["lanes"]}
    # 同品合计触顶是合计额度用尽，不是单道满仓，不得进入满仓页
    assert ids == {1, 3}


def test_ticket_keeps_row_fill_qty():
    payload = {"lines": [{"lane_id": 1, "fill_qty": 4, "gap": 9}]}
    t = present_ticket(payload)
    assert t["total_fill"] == 4
