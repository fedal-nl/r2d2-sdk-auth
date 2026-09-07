# Authentication example

The [`basic.py`](basic.py) example logs a user into the R2D2 API, stores the
returned access and refresh tokens, and calls the authenticated `/auth/me`
endpoint through the SDK.

## 1. Start the R2D2 API

Clone the API repository if necessary. From that repository, configure
`JWT_SECRET_KEY`, start Docker, and apply the database migrations:

```bash
git clone https://github.com/fedal-nl/fedal-r2d2.git
cd fedal-r2d2
docker compose up -d
docker compose exec api uv run alembic upgrade head
```

The example expects the API at `http://127.0.0.1:8000` by default.

## 2. Install the SDK

Clone and install the SDK repository:

```bash
git clone https://github.com/fedal-nl/r2d2-sdk-auth.git
cd r2d2-sdk-auth
uv sync
```

Do not run `uv add --editable ../r2d2-sdk-auth` from this directory. That would
try to add the SDK to itself. Use that command only from another project, such as
`spanglish-cli`.

## 3. Create an account once

The example performs login, so the user must already exist. Create an account
with the API documentation at <http://127.0.0.1:8000/docs>, or with curl:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "fedal",
    "email": "fedal@example.com",
    "password": "choose-a-long-password"
  }'
```

Registration is needed only once. A `409 Conflict` response means that the
username or email is already registered, in which case you can proceed to login.

## 4. Run the example

```bash
uv run python examples/basic.py
```

Enter the registered email and password when prompted:

```text
Email: fedal@example.com
Password:
Authenticated as fedal (the-user-uuid)
```

To use a different API server, set `R2D2_API_URL`:

```bash
R2D2_API_URL=https://api.example.com uv run python examples/basic.py
```

## Token storage

The example stores the session in:

```text
~/.config/r2d2/tokens.json
```

The file is created with mode `0600`, so only the current operating-system user
can read or write it. Do not commit this file or copy it between machines.

The SDK automatically attaches the access token to authenticated requests. If
the access token expires, it rotates the refresh token and retries the request
once. Call `client.logout()` when you want to revoke the refresh session and
remove the stored token file.

## Use the SDK from another project

From the `spanglish-cli` repository—not from this SDK repository—install the SDK
directly from GitHub:

```bash
uv add "r2d2-sdk-auth @ git+https://github.com/fedal-nl/r2d2-sdk-auth.git"
```

You can then import it with:

```python
from r2d2_sdk import FileTokenStore, R2D2Client
```
