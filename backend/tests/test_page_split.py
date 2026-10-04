from app.services.page_split import present_full, present_summary, present_ticket


def test_summary_total_equals_sum_of_row_fill_qty():
    payload = {
        "id": 9,
        "lines": [
            {"lane_id": 1, "gap": 7, "fill_qty": 4, "status": "need_fill"},
            {"lane_id": 2, "gap": 0, "fill_qty": 0, "status": "full"},
            {"lane_id": 3, "gap": 5, "fill_qty": 0, "status": "sku_cap_full"},
        ],
        "overbooked_count": 0,
        "full_count": 1,
        "sku_cap_full_count": 1,
    }
    s = present_summary(1, payload)
    # 汇总总量按各行补量相加，不得按缺口重算
    assert s["total_fill"] == 4
    assert s["need_fill_count"] == 1
    assert s["full_count"] == 1
    assert s["sku_cap_full_count"] == 1


def test_full_list_keeps_zero_fill_and_blocked_labels():
    payload = {
        "lines": [
            {"lane_id": 1, "fill_qty": 0, "status": "blocked", "reason": "货道封锁"},
            {"lane_id": 2, "fill_qty": 3, "status": "need_fill", "reason": ""},
            {"lane_id": 3, "fill_qty": 0, "status": "overbooked", "reason": "超占"},
        ]
    }
    body = present_full(1, payload)
    ids = {l["lane_id"] for l in body["lanes"]}
    assert ids == {1, 3}


def test_full_list_excludes_sku_cap_full_even_though_zero_fill():
    payload = {
        "lines": [
            {"lane_id": 1, "fill_qty": 0, "status": "full", "reason": "满仓"},
            {"lane_id": 2, "fill_qty": 0, "status": "sku_cap_full", "reason": "同品合计已满"},
            # 历史数据兜底：只有文案没有状态时也不得混入满仓页
            {"lane_id": 3, "fill_qty": 0, "status": "", "reason": "同品合计已满"},
        ]
    }
    body = present_full(1, payload)
    ids = {l["lane_id"] for l in body["lanes"]}
    assert ids == {1}


def test_ticket_keeps_row_fill_qty():
    payload = {"lines": [{"lane_id": 1, "fill_qty": 4, "gap": 9}]}
    t = present_ticket(payload)
    assert t["total_fill"] == 4
