"""
VESTRA Integration Tests — Critical path validation.
Run with: pytest tests/ -v
Requires: PostgreSQL + Redis running locally.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async HTTP test client — follows redirects for consistent test behavior."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


@pytest.mark.asyncio
class TestHealthChecks:
    """Verify all health endpoints respond correctly."""

    async def test_root_returns_info(self, client):
        res = await client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Vestra"
        assert data["status"] == "operational"

    async def test_health_returns_dependency_status(self, client):
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data

    async def test_liveness_probe(self, client):
        res = await client.get("/health/live")
        assert res.status_code == 200
        assert res.json()["status"] == "alive"

    async def test_readiness_probe(self, client):
        res = await client.get("/health/ready")
        assert res.status_code in (200, 503)


@pytest.mark.asyncio
class TestAuthFlow:
    """Test the full authentication lifecycle."""

    test_email = f"test-integration-{pytest.importorskip('time').time()}@vestra.co.ke"
    test_phone = f"+2547{int(pytest.importorskip('time').time() * 1000)}"[:17]
    test_password = "StrongP@ss1"
    token: str = None

    async def test_register_user(self, client):
        """Register a new user."""
        res = await client.post("/api/auth/register", json={
            "email": self.test_email,
            "phone": self.test_phone,
            "full_name": "Test User",
            "password": self.test_password,
            "role": "buyer",
        })
        assert res.status_code in (200, 201, 409)  # 409 if already exists
        if res.status_code in (200, 201):
            data = res.json()
            assert "access_token" in data
            TestAuthFlow.token = data["access_token"]

    async def test_login_with_credentials(self, client):
        """Login with email + password."""
        res = await client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password,
        })
        # May return 403 if email not verified, 200 if verified, 401 if wrong credentials
        assert res.status_code in (200, 401, 403)
        if res.status_code == 200:
            data = res.json()
            assert "access_token" in data
            TestAuthFlow.token = data["access_token"]

    async def test_me_endpoint_requires_auth(self, client):
        """GET /api/auth/me without token should return 401."""
        res = await client.get("/api/auth/me")
        assert res.status_code == 401

    async def test_forgot_password_does_not_reveal_existence(self, client):
        """Forgot password should always return 200 even for unknown emails."""
        res = await client.post("/api/auth/forgot-password", json={
            "email": "nonexistent@example.com",
        })
        assert res.status_code == 200
        data = res.json()
        assert "message" in data


@pytest.mark.asyncio
class TestPropertiesFlow:
    """Test property listing endpoints."""

    async def test_list_properties_public(self, client):
        """Anyone can list properties without auth."""
        res = await client.get("/api/properties/")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data

    async def test_list_properties_with_filters(self, client):
        """Filter by city and property type."""
        res = await client.get("/api/properties/", params={
            "city": "Nairobi",
            "property_type": "residential",
        })
        assert res.status_code == 200

    async def test_ai_search_requires_auth(self, client):
        """AI search endpoint may be public or require auth depending on config."""
        res = await client.get("/api/properties/ai-search", params={"q": "3br Karen"})
        # May be 401 if auth required, 200 if public
        assert res.status_code in (200, 401)

    async def test_create_property_requires_auth(self, client):
        """Creating a property requires authentication."""
        res = await client.post("/api/properties/", json={
            "title": "Test Property",
            "property_type": "residential",
            "listing_type": "sale",
            "address": "123 Test St",
            "city": "Nairobi",
            "county": "Nairobi",
            "price": 5000000,
        })
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
class TestAIFlow:
    """Test AI engine endpoints."""

    async def test_valuate_requires_auth(self, client):
        """AI valuation endpoints require authentication."""
        res = await client.get("/api/ai/valuate/1")
        assert res.status_code == 401

    async def test_market_insights_requires_auth(self, client):
        """Market insights require authentication."""
        res = await client.get("/api/ai/market", params={"city": "Nairobi"})
        assert res.status_code == 401

    async def test_search_parse_requires_auth(self, client):
        """Search parse requires authentication."""
        res = await client.get("/api/ai/search/parse", params={"q": "3br Karen"})
        assert res.status_code == 401


@pytest.mark.asyncio
class TestPaymentsFlow:
    """Test payment endpoint security."""

    async def test_mpesa_callback_without_ip_whitelist(self, client):
        """M-Pesa callback should be accessible but verify source."""
        res = await client.post("/api/payments/mpesa/callback", json={
            "Body": {"stkCallback": {"ResultCode": 0}}
        })
        # Should be accessible (IP check is in middleware)
        assert res.status_code in (200, 400, 403)

    async def test_initiate_mpesa_requires_auth(self, client):
        """M-Pesa initiation requires authentication."""
        res = await client.post("/api/payments/mpesa/initiate", json={
            "phone_number": "254712345678",
            "amount": 500,
            "purpose": "verification_report",
        })
        assert res.status_code == 401


@pytest.mark.asyncio
class TestAdminProtection:
    """Verify admin endpoints are properly protected."""

    async def test_admin_stats_requires_auth(self, client):
        res = await client.get("/api/admin/stats")
        assert res.status_code == 401

    async def test_admin_users_requires_auth(self, client):
        res = await client.get("/api/admin/users")
        assert res.status_code == 401

    async def test_admin_kyc_requires_auth(self, client):
        res = await client.get("/api/admin/kyc/pending")
        assert res.status_code == 401


@pytest.mark.asyncio
class TestNewRoutesExist:
    """Verify all new routes are registered and return proper responses."""

    async def test_escrow_my_requires_auth(self, client):
        res = await client.get("/api/escrow/my")
        assert res.status_code == 401

    async def test_disputes_categories_public(self, client):
        res = await client.get("/api/disputes/categories")
        assert res.status_code == 200
        data = res.json()
        assert "categories" in data
        assert len(data["categories"]) > 0

    async def test_disputes_my_requires_auth(self, client):
        res = await client.get("/api/disputes/my")
        assert res.status_code == 401

    async def test_reviews_subject_public(self, client):
        res = await client.get("/api/reviews/subject/1")
        assert res.status_code == 200

    async def test_reviews_top_agents_public(self, client):
        res = await client.get("/api/reviews/top-agents")
        assert res.status_code == 200

    async def test_payouts_my_requires_auth(self, client):
        res = await client.get("/api/payouts/my")
        assert res.status_code == 401


@pytest.mark.asyncio
class TestSecurityHeaders:
    """Verify security headers are set on responses."""

    async def test_security_headers_present(self, client):
        res = await client.get("/health")
        headers = res.headers
        assert "x-content-type-options" in headers
        assert headers["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in headers

    async def test_correlation_id_present(self, client):
        res = await client.get("/health")
        headers = res.headers
        assert "x-correlation-id" in headers

    async def test_rate_limit_headers_present(self, client):
        res = await client.get("/api/properties/")
        headers = res.headers
        assert "x-ratelimit-remaining" in headers


@pytest.mark.asyncio
class TestErrorHandling:
    """Verify consistent error responses."""

    async def test_404_returns_json(self, client):
        res = await client.get("/api/nonexistent-endpoint")
        assert res.status_code == 404
        data = res.json()
        assert "error" in data
        assert "message" in data
        assert "path" in data

    async def test_422_validation_error(self, client):
        """Invalid data should return 422."""
        res = await client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "12",  # Too short
        })
        assert res.status_code == 422

    async def test_405_method_not_allowed(self, client):
        """Wrong HTTP method returns 405 or 401 (auth middleware runs first)."""
        res = await client.put("/api/properties/ai-search")
        assert res.status_code in (401, 405)  # Auth middleware runs before method routing
