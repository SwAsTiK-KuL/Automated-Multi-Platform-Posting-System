"""Common interface every platform integration implements."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import Settings


class PlatformError(Exception):
    """Raised by an integration with a human-readable failure reason."""


class PlatformNotConfigured(PlatformError):
    pass


@dataclass
class PublishResult:
    posted_url: Optional[str]
    public_access: bool


class BasePlatform(ABC):
    name: str = "Base"
    #: env vars that must be set for this platform to run
    required_settings: tuple[str, ...] = ()

    def __init__(self, settings: Settings):
        self.settings = settings

    def missing_settings(self) -> list[str]:
        return [s.upper() for s in self.required_settings if not getattr(self.settings, s, "")]

    def ensure_configured(self) -> None:
        missing = self.missing_settings()
        if missing:
            raise PlatformNotConfigured(f"Not configured: missing {', '.join(missing)}")

    @abstractmethod
    async def publish(self, message: str, link: str, client: httpx.AsyncClient) -> PublishResult:
        """Publish `message` and return where it lives. Raise PlatformError on failure."""

    # ---- helpers -------------------------------------------------------
    @staticmethod
    def raise_for_status(response: httpx.Response, platform: str) -> None:
        if response.is_success:
            return
        detail = response.text[:300]
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = (
                    body.get("error_description") or body.get("message") or body.get("error")
                    or body.get("description") or detail
                )
        except ValueError:
            pass
        if response.status_code in (401, 403):
            raise PlatformError(f"Authentication failed ({response.status_code}): {detail}")
        if response.status_code == 429:
            raise PlatformError(f"Rate limited by {platform} (429): {detail}")
        raise PlatformError(f"HTTP {response.status_code} from {platform}: {detail}")
