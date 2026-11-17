import httpx

from app.platforms.base import BasePlatform, PlatformError, PublishResult

HF = "https://huggingface.co"


class HuggingFacePlatform(BasePlatform):
    name = "Hugging Face"
    required_settings = ("huggingface_token", "huggingface_repo_id")

    async def publish(self, message: str, link: str, client: httpx.AsyncClient) -> PublishResult:
        self.ensure_configured()
        repo_type = self.settings.huggingface_repo_type.lower()
        if repo_type not in ("model", "dataset", "space"):
            raise PlatformError("HUGGINGFACE_REPO_TYPE must be model, dataset or space")
        repo_id = self.settings.huggingface_repo_id
        title = message.replace(link, "").strip(" -–:|")[:200] or "Announcement"

        resp = await client.post(
            f"{HF}/api/{repo_type}s/{repo_id}/discussions",
            headers={"Authorization": f"Bearer {self.settings.huggingface_token}"},
            json={"title": title, "description": message, "pullRequest": False},
        )
        self.raise_for_status(resp, self.name)
        num = resp.json().get("num")
        if num is None:
            raise PlatformError("Hugging Face did not return a discussion number")
        prefix = {"model": "", "dataset": "datasets/", "space": "spaces/"}[repo_type]
        return PublishResult(posted_url=f"{HF}/{prefix}{repo_id}/discussions/{num}", public_access=True)
