"""Ticket / summary / full-lane views share the same stored lines.

汇总与小票同源：合计一律取各行 fill_qty 之和，分类计数按行 status 统计，
保证「汇总 = 各行相加」。满仓页只收单道满仓（以及封锁/超占），
同品合计触顶（sku_cap_full）不在其中。
"""
from __future__ import annotations


def _lines(payload: dict) -> list[dict]:
    raw = payload.get("lines") or []
    return list(raw)


def present_ticket(payload: dict) -> dict:
    out = dict(payload)
    lines = _lines(payload)
    out["lines"] = lines
    out["total_fill"] = sum(max(int(l.get("fill_qty") or 0), 0) for l in lines)
    return out


def present_summary(location_id: int, payload: dict) -> dict:
    lines = _lines(payload)
    total_fill = 0
    counts = {"need_fill": 0, "full": 0, "overbooked": 0, "sku_cap_full": 0}
    for l in lines:
        total_fill += max(int(l.get("fill_qty") or 0), 0)
        status = str(l.get("status") or "")
        if status in counts:
            counts[status] += 1
    return {
        "location_id": location_id,
        "order_id": payload.get("id"),
        "status": payload.get("status"),
        "total_fill": total_fill,
        "need_fill_count": counts["need_fill"],
        "full_count": counts["full"],
        "overbooked_count": counts["overbooked"],
        "sku_cap_full_count": counts["sku_cap_full"],
    }


# 满仓页收录：单道满仓，以及同样无需补货的封锁/超占；
# 同品合计触顶（sku_cap_full / 原因「同品合计已满」）一律排除。
_FULL_STATUSES = ("full", "blocked", "overbooked")
_CAP_FULL_REASON = "同品合计已满"


def present_full(location_id: int, payload: dict) -> dict:
    lanes = []
    for l in _lines(payload):
        status = str(l.get("status") or "")
        code = str(l.get("reject_code") or l.get("reason") or "")
        if status == "sku_cap_full" or _CAP_FULL_REASON in code:
            continue
        if status in _FULL_STATUSES:
            lanes.append(l)
            continue
        # 历史数据兜底：无明确状态但补量为 0、且原因不含同品触顶
        fill = int(l.get("fill_qty") or 0)
        if fill == 0 and ("满" in code or "封锁" in code or "超占" in code):
            lanes.append(l)
    return {"location_id": location_id, "lanes": lanes}


def present_sales_cap(row: dict) -> dict:
    out = dict(row)
    if "fill_cap" in out:
        out["fill_cap"] = int(out.get("gap") or out.get("fill_cap") or 0)
    return out
