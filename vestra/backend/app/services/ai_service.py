"""
ai_service.py — Vestra AI Service
All intelligence runs through Vestra's own AI engine.
No external APIs. No Anthropic. No OpenAI.
All synchronous AI calls are wrapped in run_in_executor to avoid
blocking the async event loop.
"""

import asyncio
import logging
from app.ai.engine import vestra_ai

logger = logging.getLogger("vestra")


async def _run_in_executor(func, *args, **kwargs):
    """Run a synchronous function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def analyze_property_with_ai(
    property_data: dict,
    documents_info: list,
    agent_info: dict | None = None,
) -> dict:
    """
    Full property verification using Vestra's own AI engine.
    Runs synchronously in a thread executor to avoid blocking the event loop.
    """
    try:
        return await _run_in_executor(
            vestra_ai.verify_property,
            property_data=property_data,
            documents=documents_info,
            agent_info=agent_info,
        )
    except Exception as e:
        logger.error('{"event":"ai_verification_failed","error":"%s"}', str(e))
        return {
            "fraud_risk_score": 50,
            "trust_score": 50,
            "ai_recommendation": "review",
            "ai_summary": f"AI analysis encountered an error. Manual review recommended.",
            "document_flags": [],
            "error": str(e),
        }


async def analyze_property_description(
    description: str,
    city: str,
    property_type: str,
) -> dict:
    """Quick analysis using Vestra AI."""
    return await _run_in_executor(
        vestra_ai.verify_property,
        property_data={
            "title": description[:100],
            "description": description,
            "city": city,
            "property_type": property_type,
            "listing_type": "sale",
            "price": 0,
        },
        documents=[],
        agent_info=None,
    )


async def generate_ai_property_search(query: str) -> dict:
    """Parse natural language search query using Vestra AI."""
    return await _run_in_executor(vestra_ai.parse_search, query)


async def valuate_property_ai(property_data: dict) -> dict:
    """AI-powered property valuation using Vestra AI."""
    return await _run_in_executor(vestra_ai.valuate, property_data)


async def get_market_insights_ai(city: str, listing_type: str = "sale") -> dict:
    """Get market intelligence for a city using Vestra AI."""
    return await _run_in_executor(vestra_ai.market_insights, city, listing_type)
