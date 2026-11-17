"""Telegram Bot API – https://core.telegram.org/bots/api#sendmessage

Posts to a channel the bot is an admin of. Public channels (with a @username)
produce a public t.me link; private channels produce a members-only link.
"""
import httpx

from app.platforms.base import BasePlatform, PlatformError, PublishResult


class TelegramPlatform(BasePlatform):
    name = "Telegram"
    required_settings = ("telegram_bot_token", "telegram_chat_id")

    async def publish(self, message: str, link: str, client: httpx.AsyncClient) -> PublishResult:
        self.ensure_configured()
        resp = await client.post(
            f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
            json={"chat_id": self.settings.telegram_chat_id, "text": message},
        )
        body = resp.json() if resp.content else {}
        if not body.get("ok"):
            if resp.status_code == 401:
                raise PlatformError("Authentication failed: invalid Telegram bot token")
            raise PlatformError(f"Telegram API error: {body.get('description', resp.text[:200])}")

        result = body["result"]
        chat = result.get("chat", {})
        msg_id = result["message_id"]
        if chat.get("username"):
            return PublishResult(posted_url=f"https://t.me/{chat['username']}/{msg_id}", public_access=True)
        internal_id = str(chat.get("id", "")).removeprefix("-100")
        return PublishResult(posted_url=f"https://t.me/c/{internal_id}/{msg_id}", public_access=False)
