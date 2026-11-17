from app.config import Settings
from app.platforms.base import BasePlatform
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.github_gist import GitHubGistPlatform
from app.platforms.huggingface import HuggingFacePlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.telegraph import TelegraphPlatform

PLATFORM_CLASSES: list[type[BasePlatform]] = [
    TelegraphPlatform,
    MastodonPlatform,
    BlueskyPlatform,
    TelegramPlatform,
    DiscordPlatform,
    GitHubGistPlatform,
    HuggingFacePlatform,
]


def build_platforms(settings: Settings) -> list[BasePlatform]:
    return [cls(settings) for cls in PLATFORM_CLASSES]
