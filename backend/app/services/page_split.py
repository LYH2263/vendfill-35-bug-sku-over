"""Ticket vs page numbers are produced on different paths."""
from __future__ import annotations


def _lines(payload: dict) -> list[dict]:
    raw = payload.get("lines") or []
    return list(raw)


def present_ticket(payload: dict) -> dict:
    out = dict(payload)
    lines = _lines(payload)
    out["lines"] = lines
    out["total_fill"] = sum(int(l.get("fill_qty") or 0) for l in lines)
    return out


def present_summary(location_id: int, payload: dict) -> dict:
    lines = _lines(payload)
    total_fill = sum(int(l.get("fill_qty") or 0) for l in lines)

    def count(status: str) -> int:
        return sum(1 for l in lines if str(l.get("status") or "") == status)

    return {
        "location_id": location_id,
        "order_id": payload.get("id"),
        "status": payload.get("status"),
        # 总量以小票各行实际补量为准，与单据对得上
        "total_fill": total_fill,
        "need_fill_count": count("need_fill"),
        "full_count": count("full"),
        "overbooked_count": count("overbooked"),
        "blocked_count": payload.get("blocked_count", 0),
        "capped_count": payload.get("capped_count", 0),
        # 同品合计触顶单列，绝不并入满仓
        "sku_cap_full_count": count("sku_cap_full"),
        "max_fill_qty": 0,
        "fill_open": payload.get("fill_open"),
        "fill_start_minute": payload.get("fill_start_minute"),
        "fill_end_minute": payload.get("fill_end_minute"),
    }


def present_full(location_id: int, payload: dict) -> dict:
    lines = _lines(payload)
    lanes = []
    single_lane_status = ("full", "blocked", "overbooked")
    for l in lines:
        status = str(l.get("status") or "")
        fill = int(l.get("fill_qty") or 0)
        code = str(l.get("reject_code") or l.get("reason") or "")
        # 同品合计触顶是合计额度用尽，不是单道满仓，必须排除
        if status == "sku_cap_full" or "同品合计" in code:
            continue
        if status in single_lane_status:
            lanes.append(l)
            continue
        if fill == 0 and ("满仓" in code or "封锁" in code or "超占" in code):
            lanes.append(l)
    return {"location_id": location_id, "lanes": lanes}


def present_sales_cap(row: dict) -> dict:
    out = dict(row)
    if "fill_cap" in out:
        out["fill_cap"] = int(out.get("gap") or out.get("fill_cap") or 0)
    return out
