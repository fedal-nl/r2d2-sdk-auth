# r2d2-sdk-auth

[![CI](https://github.com/fedal-nl/r2d2-sdk-auth/actions/workflows/ci.yml/badge.svg)](https://github.com/fedal-nl/r2d2-sdk-auth/actions/workflows/ci.yml)

A small, typed Python SDK for authenticating with the R2D2 API. It validates API
data with Pydantic, attaches bearer tokens automatically, rotates refresh tokens,
and retries a request once when an access token expires.

## Requirements

- Python 3.13 or newer
- An R2D2 API with the `/api/v1/auth` endpoints enabled

## Install

Install directly from GitHub in another project:

```bash
uv add "r2d2-sdk-auth @ git+https://github.com/fedal-nl/r2d2-sdk-auth.git"
```

To develop the SDK itself, clone and synchronize the repository:

```bash
git clone https://github.com/fedal-nl/r2d2-sdk-auth.git
cd r2d2-sdk-auth
uv sync
```

For local development of two adjacent repositories, you can instead run
`uv add --editable ../r2d2-sdk-auth` from the consuming project. That editable
path is a development convenience and is not suitable for another device.

## Quick start

Create an account once:

```python
from r2d2_sdk import R2D2Client

with R2D2Client("http://127.0.0.1:8000") as client:
    user = client.register("fedal", "fedal@example.com", "a-long-password")
    print(user.id)
```

Log in and make authenticated requests:

```python
from pathlib import Path

from r2d2_sdk import FileTokenStore, R2D2Client

store = FileTokenStore(Path.home() / ".config/spanglish/tokens.json")

with R2D2Client("http://127.0.0.1:8000", token_store=store) as client:
    user = client.login("fedal@example.com", "a-long-password", client_type="cli")
    print(f"Logged in as {user.username}")

    quiz = client.request(
        "POST",
        "/spanglish/quizzes",
        json={
            "source_language_id": 1,
            "target_language_id": 2,
            "question_count": 10,
        },
    )
    print(quiz["quiz_id"])
```

`base_url` can be either the server root or a URL already ending in `/api/v1`.
The SDK adds `/api/v1` when necessary.

## Authentication lifecycle

`login()` stores the returned access and refresh tokens. `request()` attaches the
access token. If a request returns `401`, the SDK exchanges the refresh token for
a new token pair, saves it, and retries exactly once. When refresh fails, stored
credentials are cleared and `AuthenticationError` asks the application to log in
again.

```python
from r2d2_sdk import AuthenticationError

try:
    profile = client.me()
except AuthenticationError:
    profile = client.login(email, password)
```

Logout revokes the server-side refresh session and clears the local token store:

```python
client.logout()
```

## Token storage

The default `MemoryTokenStore` lasts only for the current Python process.
`FileTokenStore` persists a session and writes the file atomically with mode
`0600`. It is useful for a dedicated Linux service account on a Raspberry Pi:

```python
store = FileTokenStore("/var/lib/my-device/r2d2-tokens.json")
client = R2D2Client(api_url, token_store=store)
```

Do not commit token files or passwords. Restrict the containing directory to the
service account. Desktop applications should implement the three-method
`TokenStore` protocol using Keychain, Credential Manager, or Secret Service.

For a permanently unattended device, a revocable device credential is preferable
to storing a person's password. The current API implements user login; device
credentials can later use the same client interface.

## Errors and validation

- `AuthenticationError`: missing login, invalid credentials, or expired session
- `R2D2Error`: another API error or a response that fails Pydantic validation
- `pydantic.ValidationError`: invalid caller input

SDK exceptions expose the HTTP status as `status_code` when available.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

Run the interactive example against the local API:

```bash
R2D2_API_URL=http://127.0.0.1:8000 uv run python examples/basic.py
```

Tests use `httpx.MockTransport`; they do not require a running API or database.
