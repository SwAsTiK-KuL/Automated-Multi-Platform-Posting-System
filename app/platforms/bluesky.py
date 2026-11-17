"""Bluesky (AT Protocol)

- Auth:  com.atproto.server.createSession  https://docs.bsky.app/docs/api/com-atproto-server-create-session
- Post:  com.atproto.repo.createRecord      https://docs.bsky.app/docs/advanced-guides/posts
Links are only clickable on Bluesky when sent as a "facet" with UTF-8 byte offsets.
"""
from datetime import datetime, timezone

import httpx

from app.platforms.base import BasePlatform, PlatformError, PublishResult


class BlueskyPlatform(BasePlatform):
    name = "Bluesky"
    required_settings = ("bluesky_handle", "bluesky_app_password")

    @staticmethod
    def _link_facet(message: str, link: str) -> list[dict]:
        idx = message.find(link)
        if idx < 0:
            return []
        start = len(message[:idx].encode("utf-8"))
        end = start + len(link.encode("utf-8"))
        uri = link if link.lower().startswith("http") else f"https://{link}"
        return [{
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": uri}],
        }]

    async def publish(self, message: str, link: str, client: httpx.AsyncClient) -> PublishResult:
        self.ensure_configured()
        pds = self.settings.bluesky_pds_url.rstrip("/")

        session = await client.post(
            f"{pds}/xrpc/com.atproto.server.createSession",
            json={"identifier": self.settings.bluesky_handle, "password": self.settings.bluesky_app_password},
        )
        self.raise_for_status(session, self.name)
        s = session.json()

        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "facets": self._link_facet(message, link),
            "langs": ["en"],
        }
        resp = await client.post(
            f"{pds}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {s['accessJwt']}"},
            json={"repo": s["did"], "collection": "app.bsky.feed.post", "record": record},
        )
        self.raise_for_status(resp, self.name)
        uri = resp.json().get("uri", "")  # at://did:plc:xxx/app.bsky.feed.post/<rkey>
        if not uri:
            raise PlatformError("Bluesky did not return a record URI")
        rkey = uri.rsplit("/", 1)[-1]
        handle = s.get("handle", self.settings.bluesky_handle)
        return PublishResult(posted_url=f"https://bsky.app/profile/{handle}/post/{rkey}", public_access=True)
