"""
WhatsApp Business Cloud API integration for Vestra.
Handles message sending, webhook verification, and conversation flows.
Uses Meta's WhatsApp Cloud API (graph.facebook.com).
"""
from __future__ import annotations

import asyncio
import json
import logging
import hashlib
import hmac
from typing import Optional, Any
from datetime import datetime

import httpx

from app.core.config import settings
from app.ai.engine import vestra_ai

logger = logging.getLogger("vestra")

# ── WhatsApp Cloud API Config ──────────────────────────────────────────────────

WHATSAPP_API_VERSION = "v21.0"
WHATSAPP_API_BASE = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
WHATSAPP_PHONE_NUMBER_ID = settings.WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN
WHATSAPP_VERIFY_TOKEN = settings.WHATSAPP_VERIFY_TOKEN
WHATSAPP_BUSINESS_ID = settings.WHATSAPP_BUSINESS_ID


# ── Webhook Verification ───────────────────────────────────────────────────────

def verify_webhook(mode: str, token: str, challenge: str) -> Optional[str]:
    """
    Verify WhatsApp webhook subscription.
    Meta sends GET with hub.mode, hub.verify_token, hub.challenge.
    """
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        logger.info('{"event":"whatsapp_webhook_verified"}')
        return challenge
    logger.warning('{"event":"whatsapp_webhook_failed","mode":"%s"}', mode)
    return None


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify that the webhook payload is from Meta.
    Uses HMAC-SHA256 with the app secret.
    """
    if not settings.WHATSAPP_APP_SECRET:
        return True  # Skip if app secret not configured

    try:
        expected = hmac.new(
            settings.WHATSAPP_APP_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        received = signature.replace("sha256=", "")
        return hmac.compare_digest(expected, received)
    except Exception:
        return False


# ── Message Sending ────────────────────────────────────────────────────────────

async def send_text_message(to_phone: str, text: str) -> dict:
    """Send a plain text WhatsApp message."""
    return await _send_message(to_phone, {"type": "text", "text": {"body": text}})


async def send_template_message(
    to_phone: str,
    template_name: str,
    language: str = "en",
    parameters: Optional[list[dict]] = None,
) -> dict:
    """Send a WhatsApp template message."""
    payload = {
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
        },
    }
    if parameters:
        payload["template"]["components"] = [
            {
                "type": "body",
                "parameters": parameters,
            }
        ]
    return await _send_message(to_phone, payload)


async def send_interactive_message(
    to_phone: str,
    header_text: str,
    body_text: str,
    buttons: list[dict],
) -> dict:
    """
    Send an interactive message with buttons.
    buttons: [{"id": "btn1", "title": "View Properties"}, ...]
    """
    payload = {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {"type": "text", "text": header_text[:60]},
            "body": {"text": body_text[:1024]},
            "action": {"buttons": buttons[:3]},  # Max 3 buttons
        },
    }
    return await _send_message(to_phone, payload)


async def send_property_card(
    to_phone: str,
    title: str,
    price: str,
    location: str,
    bedrooms: int,
    image_url: str = "",
    property_url: str = "",
) -> dict:
    """Send a rich property listing card via WhatsApp."""
    body_lines = [
        f"🏠 *{title[:60]}*",
        f"💰 {price}",
        f"📍 {location}",
        f"🛏 {bedrooms} bedroom(s)",
    ]

    # Use interactive with URL button
    return await send_interactive_message(
        to_phone=to_phone,
        header_text=title[:60],
        body_text="\n".join(body_lines),
        buttons=[
            {"id": "view", "title": "View Property"},
            {"id": "verify", "title": "Verify (KES 500)"},
            {"id": "search", "title": "Search More"},
        ],
    )


async def send_verification_report(
    to_phone: str,
    trust_score: float,
    fraud_score: float,
    recommendation: str,
    property_title: str,
    report_url: str = "",
) -> dict:
    """Send AI verification report summary via WhatsApp."""
    emoji_map = {"approve": "✅", "review": "⚠️", "reject": "🚫"}
    emoji = emoji_map.get(recommendation, "📋")

    text = (
        f"{emoji} *Vestra Verification Report*\n\n"
        f"🏠 {property_title[:50]}\n"
        f"🛡 Trust Score: *{trust_score:.0f}/100*\n"
        f"⚠️ Fraud Risk: *{fraud_score:.0f}/100*\n"
        f"📋 AI Says: *{recommendation.upper()}*\n\n"
        f"{'View full report: ' + report_url if report_url else 'Reply HELP for options'}"
    )

    return await send_text_message(to_phone, text)


async def send_payment_request(
    to_phone: str,
    amount: float,
    purpose: str,
    payment_link: str = "",
) -> dict:
    """Send M-Pesa payment prompt via WhatsApp."""
    text = (
        f"💳 *Payment Request — Vestra*\n\n"
        f"Purpose: {purpose}\n"
        f"Amount: KES {amount:,.0f}\n\n"
        f"Reply *PAY* to receive an M-Pesa STK Push on your phone.\n"
        f"Or pay via link: {payment_link}"
    )
    return await send_text_message(to_phone, text)


# ── Message Handling (Incoming) ────────────────────────────────────────────────

async def handle_incoming_message(
    from_phone: str,
    from_name: str,
    message_text: str,
    message_type: str = "text",
) -> dict:
    """
    Process incoming WhatsApp messages.
    Returns the response to send back.
    """
    text = message_text.strip().lower()

    # ── Commands ────────────────────────────────────────────────────────────
    if text in ("hi", "hello", "hey", "start", "menu"):
        return await _handle_greeting(from_phone, from_name)

    if text in ("help", "?"):
        return await _handle_help(from_phone)

    if text.startswith("search") or text.startswith("find"):
        return await _handle_property_search(from_phone, text)

    if text.startswith("verify"):
        return await _handle_verification(from_phone, text)

    if text in ("pay", "payment", "mpesa"):
        return await _handle_payment(from_phone)

    if text in ("market", "trends", "insights"):
        return await _handle_market(from_phone)

    if text in ("sell", "list", "post"):
        return await _handle_listing(from_phone)

    # ── Default ──────────────────────────────────────────────────────────────
    return await send_text_message(
        from_phone,
        "I didn't quite understand that. Here's what I can help you with:\n\n"
        "🔍 *SEARCH <location>* — Find properties\n"
        "🛡 *VERIFY <property ID>* — Get AI trust report\n"
        "💳 *PAY* — Make a payment via M-Pesa\n"
        "📊 *MARKET <city>* — Market insights\n"
        "🏠 *SELL* — List your property\n\n"
        "Reply *HELP* for more options."
    )


# ── Conversation Handlers ──────────────────────────────────────────────────────

async def _handle_greeting(phone: str, name: str) -> dict:
    text = (
        f"👋 *Jambo {name}!* Welcome to Vestra — Africa's #1 AI-powered property platform.\n\n"
        f"*What would you like to do?*\n"
        f"🔍 Search properties (e.g., *SEARCH 3br Nairobi under 50k*)\n"
        f"🛡 Verify a property (e.g., *VERIFY 123*)\n"
        f"📊 Market trends (e.g., *MARKET Westlands*)\n"
        f"🏠 List your property (type *SELL*)\n\n"
        f"Powered by AI. Trusted by Kenyans. 🇰🇪"
    )
    return await send_text_message(phone, text)


async def _handle_help(phone: str) -> dict:
    text = (
        "📚 *Vestra WhatsApp Help*\n\n"
        "*Search Properties:*\n"
        "Type SEARCH followed by what you want.\n"
        "Example: *SEARCH 2 bedroom apartment in Kilimani under 80k*\n\n"
        "*Verify Property:*\n"
        "Type VERIFY followed by property ID.\n"
        "Example: *VERIFY 42*\n\n"
        "*Market Insights:*\n"
        "Type MARKET followed by city.\n"
        "Example: *MARKET Karen*\n\n"
        "*Payments:*\n"
        "Type PAY to get M-Pesa payment prompt.\n\n"
        "*List Property:*\n"
        "Type SELL to start listing your property.\n\n"
        "📞 Support: +254 XXX XXX XXX\n"
        "🌐 Web: vestra.co.ke"
    )
    return await send_text_message(phone, text)


async def _handle_property_search(phone: str, text: str) -> dict:
    """Handle property search via WhatsApp."""
    # Extract the actual query (remove 'search'/'find' prefix)
    query = text.replace("search", "", 1).replace("find", "", 1).strip()
    if not query:
        return await send_text_message(
            phone,
            "Please tell me what kind of property you're looking for.\n\n"
            "Example: *SEARCH 3 bedroom apartment in Westlands under 50k*"
        )

    # Use Vestra's AI search parser (non-blocking via executor)
    try:
        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(None, vestra_ai.parse_search, query)
    except Exception:
        parsed = None

    response = f"🔍 *Searching: {query}*\n\n"

    if parsed and parsed.interpretation:
        response += f"I understood: _{parsed.interpretation}_\n\n"

    response += (
        "I'll find the best matches for you. For full results with photos and "
        "Trust Scores, visit our website or download the Vestra app.\n\n"
        f"🌐 https://vestra.co.ke/market?q={_url_encode(query)}&ai=1"
    )

    return await send_interactive_message(
        to_phone=phone,
        header_text="Property Search",
        body_text=response[:1024],
        buttons=[
            {"id": "view_web", "title": "View on Website"},
            {"id": "verify", "title": "Verify Property"},
            {"id": "search", "title": "New Search"},
        ],
    )


async def _handle_verification(phone: str, text: str) -> dict:
    """Handle property verification request via WhatsApp."""
    # Extract property ID
    import re
    match = re.search(r'(\d+)', text)
    if not match:
        return await send_text_message(
            phone,
            "Please provide the property ID you want to verify.\n\n"
            "Example: *VERIFY 42*\n\n"
            "You can find property IDs on our website or by searching properties."
        )

    property_id = int(match.group(1))
    return await send_interactive_message(
        to_phone=phone,
        header_text="Property Verification",
        body_text=(
            f"🛡 Ready to verify property *#{property_id}*\n\n"
            f"Our AI will analyze:\n"
            f"✅ Ownership documents\n"
            f"✅ Price reasonableness\n"
            f"✅ Fraud risk signals\n"
            f"✅ Agent/seller trust\n\n"
            f"💰 Cost: KES 500 (one-time)\n"
            f"⏱ Report ready in under 2 minutes\n\n"
            f"Reply *YES* to proceed with M-Pesa payment."
        ),
        buttons=[
            {"id": f"verify_{property_id}", "title": "Verify Now (KES 500)"},
            {"id": "view_property", "title": "View Property First"},
            {"id": "help", "title": "Learn More"},
        ],
    )


async def _handle_payment(phone: str) -> dict:
    """Handle M-Pesa payment initiation via WhatsApp."""
    return await send_interactive_message(
        to_phone=phone,
        header_text="M-Pesa Payment",
        body_text=(
            "💳 *Pay via M-Pesa*\n\n"
            "Choose what you're paying for:\n\n"
            "1️⃣ Property Verification — KES 500\n"
            "2️⃣ Agent Badge — KES 5,000/month\n"
            "3️⃣ Listing Fee — KES 500-2,000\n\n"
            "I'll send an STK Push to your phone."
        ),
        buttons=[
            {"id": "pay_verify", "title": "Verification KES 500"},
            {"id": "pay_badge", "title": "Agent Badge"},
            {"id": "pay_listing", "title": "List Property"},
        ],
    )


async def _handle_market(phone: str, text: str) -> dict:
    """Handle market insights request."""
    # Extract city
    parts = text.replace("market", "", 1).replace("trends", "", 1).replace("insights", "", 1).strip()
    city = parts if parts else "Nairobi"

    # Get insights from Vestra AI (non-blocking via executor)
    try:
        loop = asyncio.get_event_loop()
        insights = await loop.run_in_executor(None, vestra_ai.market_insights, city, "sale")
    except Exception:
        insights = {"market_status": "active", "avg_price_kes": 0, "trend_summary": "Market data temporarily unavailable."}

    status_map = {"hot": "🔥 HOT", "warm": "🌤 WARM", "neutral": "📊 STABLE"}
    status = status_map.get(insights.get("market_status", ""), "📊 STABLE")

    text_out = (
        f"📊 *{city.title()} Market Insights*\n\n"
        f"Status: {status}\n"
        f"Avg Price: KES {insights.get('avg_price_kes', 0):,}\n"
        f"Supply/Demand: {insights.get('supply_demand', 'balanced')}\n\n"
        f"💡 *Vestra Tip:* {insights.get('investor_tip', 'Focus on areas near upcoming infrastructure for best returns.')}\n\n"
        f"Reply *SEARCH {city}* to find properties here."
    )

    return await send_text_message(phone, text_out)


async def _handle_listing(phone: str) -> dict:
    """Handle property listing request."""
    return await send_interactive_message(
        to_phone=phone,
        header_text="List Your Property",
        body_text=(
            "🏠 *List your property on Vestra*\n\n"
            "Reach thousands of verified buyers and tenants.\n\n"
            "✅ AI Trust Score on every listing\n"
            "✅ M-Pesa integrated payments\n"
            "✅ WhatsApp + Web + App exposure\n\n"
            "Visit our website to create your listing in 3 minutes.\n"
            "🌐 https://vestra.co.ke/properties/new"
        ),
        buttons=[
            {"id": "list_now", "title": "List on Website"},
            {"id": "learn_listing", "title": "How It Works"},
            {"id": "agent_badge", "title": "Agent Badge"},
        ],
    )


# ── Webhook Event Processing ───────────────────────────────────────────────────

async def process_webhook_event(entry: dict) -> list[dict]:
    """
    Process a single WhatsApp webhook entry.
    Returns list of response messages sent.
    """
    responses = []

    for change in entry.get("changes", []):
        value = change.get("value", {})
        messages = value.get("messages", [])

        for msg in messages:
            from_phone = msg.get("from", "")
            from_name = value.get("contacts", [{}])[0].get("profile", {}).get("name", "there")
            msg_type = msg.get("type", "text")

            if msg_type == "text":
                text = msg.get("text", {}).get("body", "")
                response = await handle_incoming_message(from_phone, from_name, text)
                responses.append(response)

            elif msg_type == "interactive":
                # Handle button/list replies
                interactive = msg.get("interactive", {})
                button_id = (
                    interactive.get("button_reply", {}).get("id") or
                    interactive.get("list_reply", {}).get("id")
                )
                if button_id:
                    response = await _handle_button_reply(from_phone, from_name, button_id)
                    responses.append(response)

            elif msg_type in ("image", "document"):
                caption = msg.get(msg_type, {}).get("caption", "Document received")
                response = await send_text_message(
                    from_phone,
                    f"📎 Received your {msg_type}. Our team will review it and get back to you.\n\n"
                    f"For instant AI verification, visit: https://vestra.co.ke/verify"
                )
                responses.append(response)

    return responses


async def _handle_button_reply(phone: str, name: str, button_id: str) -> dict:
    """Handle interactive button replies from users."""
    handlers = {
        "view_web": lambda: send_text_message(phone, "🌐 Visit https://vestra.co.ke/market to browse all verified properties."),
        "search": lambda: send_text_message(phone, "Tell me what you're looking for.\nExample: *SEARCH 2br apartment in Westlands under 80k*"),
        "help": lambda: _handle_help(phone),
        "pay_verify": lambda: send_payment_request(phone, 500, "Property Verification Report"),
        "pay_badge": lambda: send_payment_request(phone, 5000, "Agent Verified Badge (Monthly)"),
        "pay_listing": lambda: send_payment_request(phone, 500, "Property Listing Fee"),
        "list_now": lambda: send_text_message(phone, "🌐 Go to https://vestra.co.ke/properties/new to list your property in 3 minutes."),
        "agent_badge": lambda: send_text_message(phone, "🏅 The Vestra Verified Agent Badge costs KES 5,000/month and includes:\n✅ Trust badge on all your listings\n✅ Priority in search results\n✅ WhatsApp business profile\n\nVisit https://vestra.co.ke/dashboard to subscribe."),
        "learn_listing": lambda: send_text_message(phone, "📋 *How to List on Vestra:*\n1️⃣ Create a free account\n2️⃣ Enter property details + photos\n3️⃣ Upload documents (title deed, etc.)\n4️⃣ Pay listing fee via M-Pesa\n5️⃣ Get AI Trust Score\n6️⃣ Go live to thousands of buyers!\n\n🌐 Start at https://vestra.co.ke/properties/new"),
    }

    if button_id in handlers:
        return await handlers[button_id]()

    # Handle dynamic buttons like verify_<id>
    if button_id.startswith("verify_"):
        prop_id = button_id.replace("verify_", "")
        return await send_text_message(
            phone,
            f"🛡 To verify property #{prop_id}, reply *YES* and we'll send an M-Pesa STK Push for KES 500 to this number."
        )

    if button_id == "view_property":
        return await send_text_message(phone, "🌐 Visit https://vestra.co.ke/market to browse properties with full photos and details.")

    return await send_text_message(phone, "I received your selection. How else can I help?")


# ── Low-Level API Call ─────────────────────────────────────────────────────────

async def _send_message(to_phone: str, message: dict) -> dict:
    """
    Send a message via the WhatsApp Cloud API.
    Returns the API response or error dict.
    """
    if not WHATSAPP_PHONE_NUMBER_ID or not WHATSAPP_ACCESS_TOKEN:
        logger.warning('{"event":"whatsapp_not_configured"}')
        return {"error": "WhatsApp not configured", "sent": False}

    to_phone = _normalize_phone(to_phone)

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        **message,
    }

    url = f"{WHATSAPP_API_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            result = response.json()

            if response.status_code == 200:
                logger.info(
                    '{"event":"whatsapp_sent","to":"%s","msg_id":"%s"}',
                    to_phone, result.get("messages", [{}])[0].get("id", ""),
                )
            else:
                logger.error(
                    '{"event":"whatsapp_error","status":%d,"error":"%s"}',
                    response.status_code, result.get("error", {}).get("message", ""),
                )

            return result

    except Exception as e:
        logger.error('{"event":"whatsapp_failed","error":"%s"}', str(e))
        return {"error": str(e), "sent": False}


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to WhatsApp format: 254XXXXXXXXX"""
    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if not phone.startswith("254"):
        phone = "254" + phone
    return phone


def _url_encode(text: str) -> str:
    """URL-encode text for web links."""
    import urllib.parse
    return urllib.parse.quote(text)
