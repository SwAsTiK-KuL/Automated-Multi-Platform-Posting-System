"""Mastodon – https://docs.joinmastodon.org/methods/statuses/#create"""
import uuid

import httpx

from app.platforms.base import BasePlatform, PublishResult


class MastodonPlatform(BasePlatform):
    name = "Mastodon"
    required_settings = ("mastodon_instance_url", "mastodon_access_token")

    async def publish(self, message: str, link: str, client: httpx.AsyncClient) -> PublishResult:
        self.ensure_configured()
        base = self.settings.mastodon_instance_url.rstrip("/")
        resp = await client.post(
            f"{base}/api/v1/statuses",
            headers={
                "Authorization": f"Bearer {self.settings.mastodon_access_token}",
                "Idempotency-Key": str(uuid.uuid4()),
            },
            data={"status": message, "visibility": "public"},
        )
        self.raise_for_status(resp, self.name)
        body = resp.json()
        return PublishResult(posted_url=body.get("url"), public_access=body.get("visibility") == "public")
