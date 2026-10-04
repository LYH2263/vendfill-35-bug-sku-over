from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Location, SkuCap
router = APIRouter(prefix="/locations", tags=["locations"])

class CapIn(BaseModel):
    # 收原始值手动校验：JSON 的 3.0 是 float、"3" 是 str、true 是 bool，
    # 均属非法，统一在写库前以 400 拒绝，保证配置与单据停在改前。
    cap: Any


def _valid_cap(value: Any) -> int:
    # bool 是 int 的子类，必须先排除
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise HTTPException(400, "合计补量上限必须为正整数")
    return value

def _cap_out(c: SkuCap) -> dict:
    return {"id": c.id, "location_id": c.location_id, "sku_name": c.sku_name, "cap": c.cap}

@router.get("")
def list_locations(db: Session = Depends(get_db)):
    return [{"id": r.id, "code": r.code, "name": r.name, "address": r.address}
            for r in db.scalars(select(Location).order_by(Location.id)).all()]

@router.get("/{location_id}/caps")
def list_caps(location_id: int, db: Session = Depends(get_db)):
    if not db.get(Location, location_id): raise HTTPException(404, "点位不存在")
    rows = db.scalars(select(SkuCap).where(SkuCap.location_id == location_id)
                      .order_by(SkuCap.sku_name)).all()
    return [_cap_out(c) for c in rows]

@router.put("/{location_id}/caps/{sku_name}")
def upsert_cap(location_id: int, sku_name: str, body: CapIn, db: Session = Depends(get_db)):
    if not db.get(Location, location_id): raise HTTPException(404, "点位不存在")
    # 先校验，任何非法值都在写库前拒绝：配置与单据保持改前
    cap_value = _valid_cap(body.cap)
    cap = db.scalars(select(SkuCap).where(SkuCap.location_id == location_id,
                                          SkuCap.sku_name == sku_name)).first()
    if cap:
        cap.cap = cap_value
    else:
        cap = SkuCap(location_id=location_id, sku_name=sku_name, cap=cap_value)
        db.add(cap)
    db.commit(); db.refresh(cap)
    return _cap_out(cap)

@router.delete("/{location_id}/caps/{sku_name}")
def delete_cap(location_id: int, sku_name: str, db: Session = Depends(get_db)):
    cap = db.scalars(select(SkuCap).where(SkuCap.location_id == location_id,
                                          SkuCap.sku_name == sku_name)).first()
    if not cap: raise HTTPException(404, "该商品未登记合计上限")
    db.delete(cap); db.commit()
    return {"ok": True}
