"""Public-client behavior against a simulated R2D2 API."""

from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from r2d2_sdk import AuthenticationError, MemoryTokenStore, R2D2Client, R2D2Error
from r2d2_sdk.models import Registration, TokenPair

USER = {
    "id": "22222222-2222-2222-2222-222222222222",
    "username": "fedal",
    "email": "fedal@example.com",
    "avatar_url": None,
    "is_active": True,
    "created_at": "2026-09-05T12:00:00Z",
    "last_login_at": None,
}
TOKENS = {
    "access_token": "access-1",
    "refresh_token": "r" * 40,
    "token_type": "bearer",
    "expires_in": 900,
}


def test_register_login_me_logout_and_url_normalization() -> None:
    requests = []

    def api(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/auth/register"):
            return httpx.Response(201, json=USER)
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, json=TOKENS)
        if request.url.path.endswith("/auth/me"):
            assert request.headers["Authorization"] == "Bearer access-1"
            return httpx.Response(200, json=USER)
        if request.url.path.endswith("/auth/logout"):
            return httpx.Response(204)
        raise AssertionError(request.url)

    store = MemoryTokenStore()
    with R2D2Client(
        "https://api.example.com/",
        token_store=store,
        transport=httpx.MockTransport(api),
    ) as client:
        registered = client.register("fedal", "fedal@example.com", "password123")
        assert registered.id == UUID(USER["id"])
        logged_in = client.login("fedal@example.com", "password123", client_type="cli")
        assert logged_in.username == "fedal"
        client.logout()
        assert store.load() is None
        client.logout()
    assert all("/api/v1/" in request.url.path for request in requests)


def test_401_refreshes_rotates_and_retries_with_custom_headers() -> None:
    calls = 0

    def api(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path.endswith("/auth/refresh"):
            return httpx.Response(200, json={**TOKENS, "access_token": "access-2"})
        calls += 1
        assert request.headers["X-Device"] == "pi"
        if calls == 1:
            return httpx.Response(401, json={"detail": "expired"})
        assert request.headers["Authorization"] == "Bearer access-2"
        return httpx.Response(200, json={"ok": True})

    store = MemoryTokenStore()
    store.save(TokenPair.model_validate(TOKENS))
    client = R2D2Client(
        "https://api.example.com/api/v1",
        token_store=store,
        transport=httpx.MockTransport(api),
    )
    assert client.request("GET", "/resource", headers={"X-Device": "pi"}) == {
        "ok": True
    }
    assert store.load().access_token == "access-2"  # type: ignore[union-attr]
    client.close()


def test_missing_and_failed_refresh_require_login() -> None:
    client = R2D2Client(
        "https://api.example.com",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(401, json={"detail": "invalid"})
        ),
    )
    with pytest.raises(AuthenticationError, match="Not logged in"):
        client.me()
    store = MemoryTokenStore()
    store.save(TokenPair.model_validate(TOKENS))
    client.token_store = store
    with pytest.raises(AuthenticationError, match="log in again") as error:
        client.request("GET", "/resource")
    assert error.value.status_code == 401
    assert store.load() is None


@pytest.mark.parametrize(
    ("status", "body", "exception"),
    [(400, {"detail": "bad"}, R2D2Error), (500, None, R2D2Error)],
)
def test_api_errors_are_friendly(status, body, exception) -> None:
    def api(_request):
        return (
            httpx.Response(status, json=body)
            if body is not None
            else httpx.Response(status, text="broken")
        )

    client = R2D2Client("https://api.example.com", transport=httpx.MockTransport(api))
    with pytest.raises(exception) as error:
        client.register("fedal", "fedal@example.com", "password123")
    assert error.value.status_code == status


def test_invalid_models_and_api_response() -> None:
    with pytest.raises(ValidationError):
        Registration(username="x", email="invalid", password="short")
    client = R2D2Client(
        "https://api.example.com",
        transport=httpx.MockTransport(lambda _request: httpx.Response(201, json={})),
    )
    with pytest.raises(R2D2Error, match="invalid response"):
        client.register("fedal", "fedal@example.com", "password123")


def test_memory_store_and_exception_metadata() -> None:
    store = MemoryTokenStore()
    assert store.load() is None
    tokens = TokenPair.model_validate(TOKENS)
    store.save(tokens)
    assert store.load() is tokens
    store.clear()
    assert store.load() is None
    error = R2D2Error("bad", status_code=418)
    assert str(error) == "bad" and error.status_code == 418
