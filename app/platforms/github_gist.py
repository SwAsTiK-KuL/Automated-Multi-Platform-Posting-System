import httpx

from app.platforms.base import BasePlatform, PublishResult


class GitHubGistPlatform(BasePlatform):
    name = "GitHub Gist"
    required_settings = ("github_token",)

    async def publish(self, message: str, link: str, client: httpx.AsyncClient) -> PublishResult:
        self.ensure_configured()
        resp = await client.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"Bearer {self.settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "description": message,
                "public": True,
                "files": {"announcement.md": {"content": f"{message.replace(link, f'[{link}]({link})')}\n"}},
            },
        )
        self.raise_for_status(resp, self.name)
        body = resp.json()
        return PublishResult(posted_url=body.get("html_url"), public_access=bool(body.get("public")))
