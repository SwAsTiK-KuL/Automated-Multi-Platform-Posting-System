from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Automated Multi-Platform Posting System"
    request_timeout: float = 15.0
    timezone: str = "Asia/Kolkata"
    max_message_length: int = 200

    telegraph_access_token: str = ""
    telegraph_author_name: str = "Automated Poster"

    mastodon_instance_url: str = ""
    mastodon_access_token: str = ""

    bluesky_handle: str = ""
    bluesky_app_password: str = ""
    bluesky_pds_url: str = "https://bsky.social"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    discord_webhook_url: str = ""
    discord_guild_id: str = ""

    github_token: str = ""

    huggingface_token: str = ""
    huggingface_repo_id: str = ""
    huggingface_repo_type: str = "model"


@lru_cache
def get_settings() -> Settings:
    return Settings()
