"""Vending refill: gap = capacity - stock - in_transit; fills capped by gap; no negative fills.

同品合计补量上限：同一商品名下各货道先按缺口算理想补量，再按传入顺序
（调用方须按货道编号升序传入）累加；合计触顶后后续货道补量置 0，状态记为
sku_cap_full（原因「同品合计已满」），与单道满仓（full）分开统计。
未登记上限的商品不受合计约束。
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

STATUS_REASONS = {
    "need_fill": "待补",
    "full": "满仓",
    "overbooked": "超占",
    "sku_cap_full": "同品合计已满",
}

@dataclass
class FillLine:
    lane_id: int
    slot_no: str
    sku_name: str
    capacity: int
    stock: int
    in_transit: int
    gap: int
    fill_qty: int
    status: str  # need_fill | full | overbooked | sku_cap_full
    reason: str = ""

def compute_gap(capacity: int, stock: int, in_transit: int) -> int:
    return capacity - stock - in_transit

def build_fill_lines(
    lanes: list[dict],
    requested: dict[int, int] | None = None,
    sku_caps: dict[str, int] | None = None,
) -> list[FillLine]:
    """requested optional desired fill per lane_id; capped by gap; never negative.
    sku_caps optional {sku_name: 合计上限}; lanes must arrive in slot_no order."""
    lines: list[FillLine] = []
    for lane in lanes:
        gap = compute_gap(int(lane["capacity"]), int(lane["stock"]), int(lane["in_transit"]))
        if gap < 0:
            status = "overbooked"
            fill = 0
        elif gap == 0:
            status = "full"
            fill = 0
        else:
            status = "need_fill"
            desire = gap if requested is None else int(requested.get(lane["id"], gap))
            fill = max(0, min(desire, gap))
        lines.append(FillLine(
            lane_id=lane["id"], slot_no=lane["slot_no"], sku_name=lane["sku_name"],
            capacity=lane["capacity"], stock=lane["stock"], in_transit=lane["in_transit"],
            gap=gap, fill_qty=fill, status=status, reason=STATUS_REASONS[status],
        ))
    if sku_caps:
        _apply_sku_caps(lines, sku_caps)
    return lines

def _apply_sku_caps(lines: list[FillLine], sku_caps: dict[str, int]) -> None:
    """Truncate fills so each registered sku_name sums to at most its cap.
    Lanes are visited in given (slot_no) order; a lane zeroed by the cap is
    marked sku_cap_full, never merged with single-lane full."""
    remaining = {name: int(cap) for name, cap in sku_caps.items()}
    for line in lines:
        if line.sku_name not in remaining or line.status != "need_fill":
            continue  # 未登记上限的商品不受合计约束；满仓/超占不占用合计额度
        left = remaining[line.sku_name]
        if left <= 0:
            line.fill_qty = 0
            line.status = "sku_cap_full"
            line.reason = STATUS_REASONS["sku_cap_full"]
        elif line.fill_qty > left:
            line.fill_qty = left
            remaining[line.sku_name] = 0
        else:
            remaining[line.sku_name] = left - line.fill_qty

def summarize(lines: list[FillLine]) -> dict:
    return {
        "total_fill": sum(l.fill_qty for l in lines),
        "need_fill_count": sum(1 for l in lines if l.status == "need_fill"),
        "full_count": sum(1 for l in lines if l.status == "full"),
        "overbooked_count": sum(1 for l in lines if l.status == "overbooked"),
        "sku_cap_full_count": sum(1 for l in lines if l.status == "sku_cap_full"),
        "lines": [asdict(l) for l in lines],
    }
