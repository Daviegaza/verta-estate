"""
WhatsApp Business API webhook & messaging endpoints.
Handles incoming messages, webhook verification, and outbound messaging.
"""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.services.whatsapp_service import (
    verify_webhook,
    verify_webhook_signature,
    process_webhook_event,
    send_text_message,
    send_template_message,
    send_property_card,
    send_verification_report,
    send_payment_request,
)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


# ── Webhook: Meta calls this ───────────────────────────────────────────────────

@router.get("/webhook")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    """
    WhatsApp webhook verification endpoint.
    Meta sends a GET request to verify the webhook URL.
    """
    challenge = verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return int(challenge)  # Must return plain integer
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def whatsapp_webhook_receive(request: Request):
    """
    Receive incoming WhatsApp messages and status updates.
    Meta sends POST requests with message data.
    """
    # Verify signature
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = await request.json()
    entries = data.get("entry", [])

    for entry in entries:
        await process_webhook_event(entry)

    return {"status": "processed"}


# ── Outbound Messaging (authenticated) ─────────────────────────────────────────

@router.post("/send/text")
async def api_send_text(
    phone: str,
    message: str,
    current_user=Depends(get_current_user),
):
    """Send a WhatsApp text message (authenticated API)."""
    result = await send_text_message(phone, message)
    return {"result": result}


@router.post("/send/property-card")
async def api_send_property_card(
    phone: str,
    property_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a property card via WhatsApp."""
    from app.services.property_service import get_property_by_id

    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    result = await send_property_card(
        to_phone=phone,
        title=prop.title,
        price=f"KES {prop.price:,.0f}",
        location=f"{prop.city}, {prop.county}",
        bedrooms=prop.bedrooms or 0,
        property_url=f"https://vestra.co.ke/properties/{prop.id}",
    )
    return {"result": result}


@router.post("/send/verification-report")
async def api_send_verification(
    verification_id: int,
    phone: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a verification report via WhatsApp."""
    from app.services.verification_service import get_verification_by_id

    v = await get_verification_by_id(db, verification_id)
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")

    prop_title = "Property"
    if v.property_id:
        from app.services.property_service import get_property_by_id
        prop = await get_property_by_id(db, v.property_id)
        if prop:
            prop_title = prop.title

    result = await send_verification_report(
        to_phone=phone,
        trust_score=v.trust_score or 0,
        fraud_score=v.fraud_risk_score or 0,
        recommendation=v.ai_recommendation or "review",
        property_title=prop_title,
        report_url=f"https://vestra.co.ke/verify?vid={v.id}",
    )
    return {"result": result}


@router.post("/send/payment-request")
async def api_send_payment_request(
    phone: str,
    amount: float,
    purpose: str,
    current_user=Depends(get_current_user),
):
    """Send an M-Pesa payment prompt via WhatsApp."""
    result = await send_payment_request(
        to_phone=phone,
        amount=amount,
        purpose=purpose,
    )
    return {"result": result}


@router.post("/broadcast")
async def api_broadcast(
    phones: list[str],
    message: str,
    current_user=Depends(get_current_admin),
):
    """Send a WhatsApp message to multiple recipients (admin only)."""
    if len(phones) > 50:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Maximum 50 recipients per broadcast")

    results = []
    for phone in phones:
        result = await send_text_message(phone, message)
        results.append({"phone": phone, "result": result})

    return {"sent": len(results), "results": results}
