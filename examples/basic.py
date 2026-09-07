"""Register once, then log in and call the authenticated user endpoint."""

import getpass
import os
from pathlib import Path

from r2d2_sdk import FileTokenStore, R2D2Client

api_url = os.getenv("R2D2_API_URL", "http://127.0.0.1:8000")
token_store = FileTokenStore(Path.home() / ".config/r2d2/tokens.json")

with R2D2Client(api_url, token_store=token_store) as client:
    email = input("Email: ")
    user = client.login(email, getpass.getpass("Password: "), client_type="example")
    print(f"Authenticated as {user.username} ({user.id})")
