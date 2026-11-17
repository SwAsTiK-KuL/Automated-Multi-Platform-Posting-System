import asyncio
import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

from app.config import Settings
from app.platforms.base import BasePlatform, PlatformError
from app.schemas import PlatformResult, PostRequest, PostResponse, PostStatus

logger = logging.getLogger("posting")


class PostingService:
    def __init__(
        self,
        settings: Settings,
        platforms: list[BasePlatform],
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.settings = settings
        self.platforms = platforms
        self.transport = transport
        self.tz = ZoneInfo(settings.timezone)

    async def _post_one(self, platform: BasePlatform, req: PostRequest, client: httpx.AsyncClient) -> PlatformResult:
        try:
            published = await platform.publish(req.message, req.cta_link, client)
        except PlatformError as exc:
            error = str(exc)
        except httpx.TimeoutException:
            error = f"Request to {platform.name} timed out after {self.settings.request_timeout}s"
        except httpx.HTTPError as exc:
            error = f"Network error contacting {platform.name}: {exc.__class__.__name__}: {exc}"
        except Exception as exc:
            logger.exception("Unexpected error on %s", platform.name)
            error = f"Unexpected error: {exc.__class__.__name__}: {exc}"
        else:
            now = datetime.now(self.tz)
            logger.info("[%s] SUCCESS %s (public=%s)", platform.name, published.posted_url, published.public_access)
            return PlatformResult(
                platform=platform.name,
                status=PostStatus.success,
                posted_url=published.posted_url,
                public_access=published.public_access,
                date=now.strftime("%Y-%m-%d"),
                time=now.strftime("%H:%M:%S"),
            )
        logger.warning("[%s] FAILED %s", platform.name, error)
        return PlatformResult(platform=platform.name, status=PostStatus.failed, error=error)

    async def post(self, req: PostRequest) -> PostResponse:
        logger.info("Posting to %d platforms: %r", len(self.platforms), req.message)
        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout,
            transport=self.transport,
            headers={"User-Agent": "automated-posting/1.0"},
        ) as client:
            results = await asyncio.gather(*(self._post_one(p, req, client) for p in self.platforms))

        ok = sum(r.status == PostStatus.success for r in results)
        return PostResponse(
            success=ok > 0,
            message=req.message,
            total_platforms=len(results),
            successful=ok,
            failed=len(results) - ok,
            results=list(results),
        )
