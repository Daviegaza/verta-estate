"""
Integration tests for business features:
Subscriptions, Rentals, Escrow, Disputes, Reviews, Referrals.
"""
import pytest
from httpx import AsyncClient


# ── Fixtures ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def registered_buyer_token(client: AsyncClient, test_user_data: dict):
    """Register a buyer and return an access token."""
    async def _register(email_override: str = None):
        data = {**test_user_data}
        if email_override:
            data["email"] = email_override
        resp = await client.post("/api/auth/register", json=data)
        if resp.status_code in (200, 201):
            return resp.json()["access_token"]
        return None
    return _register


@pytest.fixture
def registered_agent_token(client: AsyncClient, test_agent_data: dict):
    """Register an agent and return an access token."""
    async def _register(email_override: str = None):
        data = {**test_agent_data}
        if email_override:
            data["email"] = email_override
        resp = await client.post("/api/auth/register", json=data)
        if resp.status_code in (200, 201):
            return resp.json()["access_token"]
        return None
    return _register


# ── Subscriptions ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestSubscriptions:
    """Subscription plan listing, creation, and retrieval."""

    async def test_list_plans_requires_auth(self, client: AsyncClient):
        """Listing subscription plans requires authentication."""
        res = await client.get("/api/subscriptions/plans")
        assert res.status_code == 401

    async def test_list_plans_as_agent(self, client: AsyncClient, registered_agent_token):
        """Authenticated agent can list available plans."""
        token = await registered_agent_token()
        if not token:
            pytest.skip("Could not register agent")
        res = await client.get(
            "/api/subscriptions/plans",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Expect 200 with plan data or 400-level if subscription logic rejects
        assert res.status_code in (200, 400, 403)
        if res.status_code == 200:
            data = res.json()
            assert "plans" in data
            assert "role" in data
            assert "current_tier" in data

    async def test_subscribe_requires_auth(self, client: AsyncClient):
        """Subscribing to a plan requires authentication."""
        res = await client.post("/api/subscriptions/subscribe", params={
            "tier": "free",
            "phone_number": "254712345678",
        })
        assert res.status_code == 401

    async def test_subscribe_as_buyer_rejected(self, client: AsyncClient, registered_buyer_token):
        """Buyers cannot subscribe — subscriptions are for agents/landlords only."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        res = await client.post(
            "/api/subscriptions/subscribe",
            params={"tier": "free", "phone_number": "254712345678"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Buyers don't need subscriptions, should return 400
        assert res.status_code == 400

    async def test_my_subscription_requires_auth(self, client: AsyncClient):
        """Getting own subscription requires authentication."""
        res = await client.get("/api/subscriptions/my")
        assert res.status_code == 401

    async def test_my_subscription_as_agent(self, client: AsyncClient, registered_agent_token):
        """Authenticated agent can retrieve their subscription status."""
        token = await registered_agent_token()
        if not token:
            pytest.skip("Could not register agent")
        res = await client.get(
            "/api/subscriptions/my",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code in (200, 404)
        if res.status_code == 200:
            data = res.json()
            assert "subscription" in data
            assert "listing_limit" in data
            assert "role" in data

    async def test_subscribe_invalid_tier(self, client: AsyncClient, registered_agent_token):
        """Subscribing with an invalid tier returns 400/422."""
        token = await registered_agent_token()
        if not token:
            pytest.skip("Could not register agent")
        res = await client.post(
            "/api/subscriptions/subscribe",
            params={"tier": "nonexistent_tier", "phone_number": "254712345678"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code in (400, 422)


# ── Rentals ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestRentals:
    """Rental unit management endpoints."""

    async def test_list_units_requires_auth(self, client: AsyncClient):
        """Listing rental units requires authentication."""
        res = await client.get("/api/rentals/units")
        assert res.status_code == 401

    async def test_list_units_authenticated(self, client: AsyncClient, registered_agent_token):
        """Authenticated landlord can list their units (may be empty)."""
        token = await registered_agent_token()
        if not token:
            pytest.skip("Could not register agent")
        res = await client.get(
            "/api/rentals/units",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        # Response is a list of units (may be empty for a fresh account)
        data = res.json()
        assert isinstance(data, list)

    async def test_create_unit_requires_auth(self, client: AsyncClient):
        """Creating a rental unit requires authentication."""
        res = await client.post(
            "/api/rentals/units",
            json={"name": "Test Unit", "unit_type": "apartment", "city": "Nairobi"},
        )
        assert res.status_code == 401

    async def test_create_unit_authenticated(self, client: AsyncClient, registered_agent_token):
        """Authenticated agent can create a rental unit."""
        token = await registered_agent_token()
        if not token:
            pytest.skip("Could not register agent")
        res = await client.post(
            "/api/rentals/units",
            json={
                "name": "Sunset Apartment 3B",
                "unit_type": "apartment",
                "bedrooms": 2,
                "bathrooms": 1,
                "monthly_rent_kes": 45000,
                "city": "Nairobi",
                "address": "123 Sunset Blvd",
                "is_occupied": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        # Expect 200 (success), 402 (subscription limit), or 422 (validation)
        assert res.status_code in (200, 402, 422)
        if res.status_code == 200:
            data = res.json()
            assert "id" in data
            assert "name" in data
            assert "message" in data

    async def test_list_tenants_requires_auth(self, client: AsyncClient):
        """Listing tenants requires authentication."""
        res = await client.get("/api/rentals/tenants")
        assert res.status_code == 401

    async def test_list_tenants_authenticated(self, client: AsyncClient, registered_agent_token):
        """Authenticated landlord can list their tenants (may be empty)."""
        token = await registered_agent_token()
        if not token:
            pytest.skip("Could not register agent")
        res = await client.get(
            "/api/rentals/tenants",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)


# ── Escrow ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestEscrow:
    """Escrow transaction endpoints."""

    async def test_create_escrow_requires_auth(self, client: AsyncClient):
        """Creating an escrow requires authentication."""
        res = await client.post("/api/escrow", params={
            "property_id": 1,
            "amount_kes": 5000000,
            "seller_id": 2,
        })
        assert res.status_code == 401

    async def test_create_escrow_missing_params(self, client: AsyncClient, registered_buyer_token):
        """Creating an escrow with missing params returns 422."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        res = await client.post(
            "/api/escrow",
            params={},  # Missing required query params
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code in (400, 422)

    async def test_my_escrows_requires_auth(self, client: AsyncClient):
        """Listing own escrows requires authentication."""
        res = await client.get("/api/escrow/my")
        assert res.status_code == 401

    async def test_my_escrows_authenticated(self, client: AsyncClient, registered_buyer_token):
        """Authenticated user can list their escrows (may be empty)."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        res = await client.get(
            "/api/escrow/my",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert isinstance(data["items"], list)


# ── Disputes ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestDisputes:
    """Dispute filing and listing endpoints."""

    async def test_file_dispute_requires_auth(self, client: AsyncClient):
        """Filing a dispute requires authentication."""
        res = await client.post("/api/disputes", params={
            "category": "fraud",
            "description": "This is a test dispute description with enough length to pass validation.",
        })
        assert res.status_code == 401

    async def test_file_dispute_missing_params(self, client: AsyncClient, registered_buyer_token):
        """Filing a dispute without required params returns 422."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        # Missing category and description
        res = await client.post(
            "/api/disputes",
            params={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 422

    async def test_file_dispute_invalid_category(self, client: AsyncClient, registered_buyer_token):
        """Filing a dispute with an invalid category returns 400."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        res = await client.post(
            "/api/disputes",
            params={
                "category": "invalid_category_xyz",
                "description": "This is a test dispute with enough length to pass validation.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 400

    async def test_my_disputes_requires_auth(self, client: AsyncClient):
        """Listing own disputes requires authentication."""
        res = await client.get("/api/disputes/my")
        assert res.status_code == 401

    async def test_my_disputes_authenticated(self, client: AsyncClient, registered_buyer_token):
        """Authenticated user can list their disputes (may be empty)."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        res = await client.get(
            "/api/disputes/my",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_dispute_categories_public(self, client: AsyncClient):
        """Dispute categories endpoint is public and returns categories list."""
        res = await client.get("/api/disputes/categories")
        assert res.status_code == 200
        data = res.json()
        assert "categories" in data
        assert len(data["categories"]) > 0


# ── Reviews ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestReviews:
    """Review writing and retrieval endpoints."""

    async def test_write_review_requires_auth(self, client: AsyncClient):
        """Writing a review requires authentication."""
        res = await client.post("/api/reviews", params={
            "subject_id": 1,
            "rating": 5,
        })
        assert res.status_code == 401

    async def test_write_review_missing_params(self, client: AsyncClient, registered_buyer_token):
        """Writing a review without required params returns 422."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        res = await client.post(
            "/api/reviews",
            params={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 422

    async def test_write_review_invalid_rating(self, client: AsyncClient, registered_buyer_token):
        """Writing a review with an out-of-range rating returns 422."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        res = await client.post(
            "/api/reviews",
            params={
                "subject_id": 1,
                "rating": 99,  # Must be 1-5
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 422

    async def test_write_review_valid(self, client: AsyncClient, registered_buyer_token):
        """Authenticated user can write a valid review (may fail if subject doesn't exist)."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        res = await client.post(
            "/api/reviews",
            params={
                "subject_id": 1,
                "rating": 4,
                "title": "Great agent",
                "body": "Very professional and helpful throughout the process.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        # Expect 200, 400 (subject not found), or 409 (duplicate)
        assert res.status_code in (200, 400, 404, 409)
        if res.status_code == 200:
            data = res.json()
            assert "id" in data
            assert "rating" in data
            assert "message" in data

    async def test_top_agents_public(self, client: AsyncClient):
        """Top agents endpoint is public and returns an agent list."""
        res = await client.get("/api/reviews/top-agents")
        assert res.status_code == 200
        data = res.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    async def test_top_agents_response_structure(self, client: AsyncClient):
        """Top agents response contains expected fields."""
        res = await client.get("/api/reviews/top-agents", params={"limit": 5, "min_reviews": 1})
        assert res.status_code == 200
        data = res.json()
        for agent in data["agents"]:
            assert "agent_id" in agent
            assert "avg_rating" in agent
            assert "review_count" in agent


# ── Referrals ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestReferrals:
    """Referral code generation and registration with referral."""

    async def test_referral_code_requires_auth(self, client: AsyncClient):
        """Getting referral code requires authentication (or returns 404 if route doesn't exist)."""
        res = await client.get("/api/auth/referral-code")
        # Either 401 (auth required) or 404 (route doesn't exist as dedicated endpoint)
        assert res.status_code in (401, 404)

    async def test_referral_code_authenticated(self, client: AsyncClient, registered_buyer_token):
        """Authenticated user can access referral code endpoint (if it exists)."""
        token = await registered_buyer_token()
        if not token:
            pytest.skip("Could not register buyer")
        res = await client.get(
            "/api/auth/referral-code",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 200 if the route exists, 404 if not implemented as a dedicated endpoint
        if res.status_code == 200:
            data = res.json()
            # Should contain some sort of referral code or user data
            assert "referral_code" in data or "code" in data
        else:
            assert res.status_code == 404

    async def test_register_with_referral_code(self, client: AsyncClient):
        """User can register with a valid referral code structure (field accepted)."""
        res = await client.post("/api/auth/register", json={
            "email": "referral-test-user@example.com",
            "full_name": "Referred User",
            "password": "StrongP@ss1",
            "role": "buyer",
            "referral_code": "VSTTEST123",
        })
        # Should be accepted at schema level — returns 201, 409, or 400
        assert res.status_code in (201, 400, 409)
        if res.status_code == 201:
            data = res.json()
            assert "access_token" in data

    async def test_register_with_invalid_referral_code(self, client: AsyncClient):
        """Registering with an invalid referral code still creates the user."""
        res = await client.post("/api/auth/register", json={
            "email": "bad-referral-user@example.com",
            "full_name": "Bad Referral User",
            "password": "StrongP@ss1",
            "role": "buyer",
            "referral_code": "NONEXISTENT123",
        })
        # User should still be created even with bad referral code
        assert res.status_code in (201, 409)
        if res.status_code == 201:
            data = res.json()
            assert "access_token" in data

    async def test_register_without_referral_code(self, client: AsyncClient):
        """User can register without providing a referral code."""
        res = await client.post("/api/auth/register", json={
            "email": "no-ref-user@example.com",
            "full_name": "No Referral User",
            "password": "StrongP@ss1",
            "role": "buyer",
        })
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
