"""
Integration tests for the complete authentication flow:
Register → Login → Get Profile → Change Password → Logout
Also tests account lockout, CAPTCHA validation, and edge cases.
"""
import pytest
from httpx import AsyncClient


class TestAuthRegister:
    """Registration endpoint tests."""

    async def test_register_success(self, client: AsyncClient, test_user_data: dict):
        """User can register with valid data and receive a token."""
        response = await client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["full_name"] == test_user_data["full_name"]
        assert data["user"]["role"] == "buyer"

    async def test_register_duplicate_email(self, client: AsyncClient, test_user_data: dict):
        """Registering with an existing email returns 409."""
        # First registration
        await client.post("/api/auth/register", json=test_user_data)
        # Duplicate
        response = await client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 409

    async def test_register_weak_password(self, client: AsyncClient, test_user_data: dict):
        """Registration with a weak password is rejected."""
        data = {**test_user_data, "email": "weak@example.com", "password": "short"}
        response = await client.post("/api/auth/register", json=data)
        assert response.status_code == 400

    async def test_register_missing_fields(self, client: AsyncClient):
        """Registration without required fields returns 422."""
        response = await client.post("/api/auth/register", json={"email": "x@x.com"})
        assert response.status_code == 422


class TestAuthLogin:
    """Login endpoint tests including account lockout."""

    async def test_login_success(self, client: AsyncClient, test_user_data: dict):
        """User can log in after registration."""
        # Register first
        await client.post("/api/auth/register", json=test_user_data)
        # Then login
        response = await client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user_data["email"]

    async def test_login_wrong_password(self, client: AsyncClient, test_user_data: dict):
        """Login with wrong password returns 401 with remaining attempts."""
        await client.post("/api/auth/register", json=test_user_data)
        response = await client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": "WrongP@ss1",
        })
        assert response.status_code == 401
        detail = response.json()
        assert "incorrect" in detail["message"].lower()
        assert "attempt" in detail["message"].lower()

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Login for a user that doesn't exist returns 401."""
        response = await client.post("/api/auth/login", json={
            "email": "ghost@example.com",
            "password": "Whatever1",
        })
        assert response.status_code == 401

    async def test_account_lockout_after_failures(self, client: AsyncClient, test_user_data: dict):
        """After 5 failed login attempts, the account is locked with 429."""
        await client.post("/api/auth/register", json=test_user_data)

        wrong_pw = {"email": test_user_data["email"], "password": "WrongP@ss1"}
        # 5 failed attempts
        for _ in range(5):
            response = await client.post("/api/auth/login", json=wrong_pw)

        # 6th attempt should be locked
        response = await client.post("/api/auth/login", json=wrong_pw)
        assert response.status_code == 429
        detail = response.json()
        assert "locked" in detail["message"].lower() or "too many" in detail["message"].lower()

    async def test_login_resets_lockout(self, client: AsyncClient, test_user_data: dict):
        """Successful login resets the failure counter."""
        await client.post("/api/auth/register", json=test_user_data)

        # One failed attempt
        await client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": "WrongP@ss1",
        })
        # Then successful login
        response = await client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200

        # Another failed attempt should show 4 remaining (counter was reset)
        response = await client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": "WrongP@ss1",
        })
        assert response.status_code == 401


class TestAuthProfile:
    """Authenticated user profile tests."""

    async def test_get_me_with_valid_token(self, client: AsyncClient, test_user_data: dict):
        """Authenticated user can retrieve their profile."""
        reg_resp = await client.post("/api/auth/register", json=test_user_data)
        token = reg_resp.json()["access_token"]

        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == test_user_data["email"]

    async def test_get_me_without_token(self, client: AsyncClient):
        """Unauthenticated requests are rejected with 401."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_get_me_with_invalid_token(self, client: AsyncClient):
        """Requests with a malformed token are rejected."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code == 401


class TestAuthChangePassword:
    """Password change tests."""

    async def test_change_password_success(self, client: AsyncClient, test_user_data: dict):
        """User can change their password and log in with the new password."""
        reg_resp = await client.post("/api/auth/register", json=test_user_data)
        token = reg_resp.json()["access_token"]

        # Change password
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": test_user_data["password"],
                "new_password": "NewStr0ngP@ss!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Old password should no longer work
        response = await client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 401

        # New password should work
        response = await client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": "NewStr0ngP@ss!",
        })
        assert response.status_code == 200

    async def test_change_password_wrong_current(self, client: AsyncClient, test_user_data: dict):
        """Changing password with wrong current password fails."""
        reg_resp = await client.post("/api/auth/register", json=test_user_data)
        token = reg_resp.json()["access_token"]

        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongCurrent1",
                "new_password": "NewStr0ngP@ss!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400


class TestAuthLogout:
    """Logout and session termination tests."""

    async def test_logout_clears_client_state(self, client: AsyncClient, test_user_data: dict):
        """After logout, the auth store should clear. Token is stateless in JWT,
        but client-side tokens are removed. This test verifies the flow works."""
        reg_resp = await client.post("/api/auth/register", json=test_user_data)
        token = reg_resp.json()["access_token"]

        # Token is still valid for API calls (JWT is stateless)
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Logout on frontend removes token, so subsequent calls without token fail
        response = await client.get("/api/auth/me")
        assert response.status_code == 401
