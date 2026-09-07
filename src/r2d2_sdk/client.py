"""Friendly synchronous R2D2 authentication client."""

from typing import Any

import httpx
from pydantic import ValidationError

from r2d2_sdk.errors import AuthenticationError, R2D2Error
from r2d2_sdk.models import Login, Refresh, Registration, TokenPair, User
from r2d2_sdk.storage import MemoryTokenStore, TokenStore


class R2D2Client:
    """Authenticate once and make automatically refreshed API requests."""

    def __init__(
        self,
        base_url: str,
        *,
        token_store: TokenStore | None = None,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        normalized = base_url.rstrip("/")
        if not normalized.endswith("/api/v1"):
            normalized = f"{normalized}/api/v1"
        self._http = httpx.Client(
            base_url=normalized, timeout=timeout, transport=transport
        )
        self.token_store = token_store or MemoryTokenStore()

    def __enter__(self) -> "R2D2Client":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def register(self, username: str, email: str, password: str) -> User:
        payload = Registration(username=username, email=email, password=password)
        response = self._send(
            "POST", "/auth/register", json=payload.model_dump(mode="json")
        )
        return self._validate(User, response)

    def login(
        self, email: str, password: str, *, client_type: str = "python-sdk"
    ) -> User:
        payload = Login(email=email, password=password, client_type=client_type)
        response = self._send(
            "POST", "/auth/login", json=payload.model_dump(mode="json")
        )
        self.token_store.save(self._validate(TokenPair, response))
        return self.me()

    def me(self) -> User:
        return self._validate(User, self.request("GET", "/auth/me"))

    def logout(self) -> None:
        tokens = self.token_store.load()
        if tokens is None:
            return
        try:
            self._send(
                "POST",
                "/auth/logout",
                json={"refresh_token": tokens.refresh_token},
            )
        finally:
            self.token_store.clear()

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an authenticated request, refreshing and retrying once on 401."""
        tokens = self.token_store.load()
        if tokens is None:
            raise AuthenticationError("Not logged in; call client.login() first")
        custom_headers = kwargs.pop("headers", None)
        response = self._http.request(
            method,
            path,
            headers=self._headers(custom_headers, tokens.access_token),
            **kwargs,
        )
        if response.status_code == 401:
            tokens = self._refresh(tokens.refresh_token)
            response = self._http.request(
                method,
                path,
                headers=self._headers(custom_headers, tokens.access_token),
                **kwargs,
            )
        return self._response_data(response)

    def _refresh(self, refresh_token: str) -> TokenPair:
        payload = Refresh(refresh_token=refresh_token)
        try:
            response = self._send(
                "POST", "/auth/refresh", json=payload.model_dump(mode="json")
            )
        except R2D2Error as exc:
            self.token_store.clear()
            raise AuthenticationError(
                "Session expired; log in again", status_code=exc.status_code
            ) from exc
        tokens = self._validate(TokenPair, response)
        self.token_store.save(tokens)
        return tokens

    def _send(self, method: str, path: str, **kwargs: Any) -> Any:
        return self._response_data(self._http.request(method, path, **kwargs))

    @staticmethod
    def _headers(existing: dict[str, str] | None, token: str) -> dict[str, str]:
        return {**(existing or {}), "Authorization": f"Bearer {token}"}

    @staticmethod
    def _response_data(response: httpx.Response) -> Any:
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            error = AuthenticationError if response.status_code == 401 else R2D2Error
            raise error(str(detail), status_code=response.status_code)
        return response.json() if response.content else None

    @staticmethod
    def _validate(model, value):
        try:
            return model.model_validate(value)
        except ValidationError as exc:
            raise R2D2Error("The API returned an invalid response") from exc
