"""Token persistence tests."""

import stat

from r2d2_sdk.models import TokenPair
from r2d2_sdk.storage import FileTokenStore


def test_file_store_round_trip_and_permissions(tmp_path) -> None:
    path = tmp_path / "nested" / "tokens.json"
    store = FileTokenStore(path)
    assert store.load() is None
    tokens = TokenPair(
        access_token="access",
        refresh_token="r" * 40,
        token_type="bearer",
        expires_in=900,
    )
    store.save(tokens)
    assert store.load() == tokens
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    store.clear()
    assert not path.exists()
