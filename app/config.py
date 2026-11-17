"""Application settings, loaded from environment variables / a local .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # General
    app_name: str = "Automated Multi-Platform Posting System"
    request_timeout: float = 15.0
    timezone: str = "Asia/Kolkata"
    max_message_length: int = 200

    # Telegraph (telegra.ph) – token optional, an account is created on the fly if empty
    telegraph_access_token: str = ""
    telegraph_author_name: str = "Automated Poster"

    # Mastodon
    mastodon_instance_url: str = ""          # e.g. https://mastodon.social
    mastodon_access_token: str = ""

    # Bluesky (AT Protocol)
    bluesky_handle: str = ""                 # e.g. yourname.bsky.social
    bluesky_app_password: str = ""
    bluesky_pds_url: str = "https://bsky.social"

    # Telegram Bot API
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""               # e.g. @your_public_channel

    # Discord webhook
    discord_webhook_url: str = ""
    discord_guild_id: str = ""               # optional, used to build a message link

    # GitHub Gists
    github_token: str = ""

    # Hugging Face Hub (LLM platform) – posts a community discussion on your own repo
    huggingface_token: str = ""
    huggingface_repo_id: str = ""            # e.g. username/my-model
    huggingface_repo_type: str = "model"     # model | dataset | space


@lru_cache
def get_settings() -> Settings:
    return Settings()
