"""M10 — Transaction Monitoring API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.modules.transactions.engine import get_transaction_engine

router = APIRouter(prefix="/api/v1/transactions", tags=["m10-transactions"])


class TransactionScreenRequest(BaseModel):
    external_ref: Optional[str] = None
    subject_identifier: str
    counterparty_identifier: Optional[str] = None
    counterparty_country: Optional[str] = None
    amount: float
    currency: str
    channel: str
    country: str
    occurred_at: Optional[datetime] = None


@router.post("/screen")
async def screen_transaction(
    req: TransactionScreenRequest, current_user: CurrentUser = Depends(get_current_user)
):
    return await get_transaction_engine().score_transaction(
        tenant_id=current_user.tenant_id,
        txn_data=req.model_dump(),
        user_id=current_user.user_id,
    )


@router.get("/summary")
async def transaction_summary(current_user: CurrentUser = Depends(get_current_user)):
    return await get_transaction_engine().summary(tenant_id=current_user.tenant_id)


@router.get("")
async def list_transactions(
    status: Optional[str] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await get_transaction_engine().list_transactions(
        tenant_id=current_user.tenant_id, status=status, risk_level=risk_level, limit=limit
    )


@router.get("/{transaction_id}")
async def get_transaction(transaction_id: str, current_user: CurrentUser = Depends(get_current_user)):
    txn = await get_transaction_engine().get_transaction(
        tenant_id=current_user.tenant_id, transaction_id=transaction_id
    )
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
