import httpx

from app.platforms.base import BasePlatform, PublishResult


class DiscordPlatform(BasePlatform):
    name = "Discord"
    required_settings = ("discord_webhook_url",)

    async def publish(self, message: str, link: str, client: httpx.AsyncClient) -> PublishResult:
        self.ensure_configured()
        resp = await client.post(
            self.settings.discord_webhook_url,
            params={"wait": "true"},
            json={"content": message, "allowed_mentions": {"parse": []}},
        )
        self.raise_for_status(resp, self.name)
        body = resp.json()
        guild = body.get("guild_id") or self.settings.discord_guild_id
        url = None
        if guild:
            url = f"https://discord.com/channels/{guild}/{body['channel_id']}/{body['id']}"
        return PublishResult(posted_url=url, public_access=False)
