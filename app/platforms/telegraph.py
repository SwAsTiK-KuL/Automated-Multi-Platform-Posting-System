"""Telegraph (telegra.ph) – https://telegra.ph/api

Works without any pre-shared credentials: if TELEGRAPH_ACCESS_TOKEN is empty an
anonymous account is created via `createAccount` and its token is reused.
"""
import json

import httpx

from app.platforms.base import BasePlatform, PlatformError, PublishResult

API = "https://api.telegra.ph"


class TelegraphPlatform(BasePlatform):
    name = "Telegraph"
    required_settings = ()

    _cached_token: str | None = None

    async def _token(self, client: httpx.AsyncClient) -> str:
        if self.settings.telegraph_access_token:
            return self.settings.telegraph_access_token
        if TelegraphPlatform._cached_token:
            return TelegraphPlatform._cached_token
        resp = await client.post(
            f"{API}/createAccount",
            data={"short_name": "autoposter", "author_name": self.settings.telegraph_author_name},
        )
        data = self._parse(resp)
        TelegraphPlatform._cached_token = data["access_token"]
        return TelegraphPlatform._cached_token

    def _parse(self, resp: httpx.Response) -> dict:
        self.raise_for_status(resp, self.name)
        body = resp.json()
        if not body.get("ok"):
            raise PlatformError(f"Telegraph API error: {body.get('error', 'unknown error')}")
        return body["result"]

    @staticmethod
    def _content(message: str, link: str) -> list:
        before, _, after = message.partition(link)
        children: list = []
        if before:
            children.append(before)
        children.append({"tag": "a", "attrs": {"href": link}, "children": [link]})
        if after:
            children.append(after)
        return [{"tag": "p", "children": children}]

    async def publish(self, message: str, link: str, client: httpx.AsyncClient) -> PublishResult:
        token = await self._token(client)
        title = message.replace(link, "").strip(" -–:|") or "Announcement"
        resp = await client.post(
            f"{API}/createPage",
            data={
                "access_token": token,
                "title": title[:256],
                "author_name": self.settings.telegraph_author_name,
                "content": json.dumps(self._content(message, link)),
                "return_content": "false",
            },
        )
        result = self._parse(resp)
        return PublishResult(posted_url=result["url"], public_access=True)
