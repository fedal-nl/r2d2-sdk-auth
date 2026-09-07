"""Pluggable token persistence."""

import os
from pathlib import Path
from typing import Protocol

from r2d2_sdk.models import TokenPair


class TokenStore(Protocol):
    def load(self) -> TokenPair | None: ...

    def save(self, tokens: TokenPair) -> None: ...

    def clear(self) -> None: ...


class MemoryTokenStore:
    """Process-local storage suitable for scripts and tests."""

    def __init__(self) -> None:
        self._tokens: TokenPair | None = None

    def load(self) -> TokenPair | None:
        return self._tokens

    def save(self, tokens: TokenPair) -> None:
        self._tokens = tokens

    def clear(self) -> None:
        self._tokens = None


class FileTokenStore:
    """Simple mode-0600 storage for headless machines.

    Desktop applications should provide an OS-keychain-backed TokenStore instead.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()

    def load(self) -> TokenPair | None:
        if not self.path.exists():
            return None
        return TokenPair.model_validate_json(self.path.read_text())

    def save(self, tokens: TokenPair) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(tokens.model_dump_json())
        temporary.chmod(0o600)
        os.replace(temporary, self.path)
        self.path.chmod(0o600)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
