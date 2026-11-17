import ipaddress
import re
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_LENGTH = 200

LINK_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)
TRAILING_PUNCT = ".,;:!?)]}'\""
HOSTNAME_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$", re.IGNORECASE)


def extract_links(text: str) -> list[str]:
    return [m.group(0).rstrip(TRAILING_PUNCT) for m in LINK_PATTERN.finditer(text)]


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"CTA link '{url}' must start with http:// or https://")
    host = parsed.hostname
    if not host:
        raise ValueError(f"CTA link '{url}' has no host")
    if _is_ip(host):
        raise ValueError(f"CTA link '{url}' must use a domain name, not an IP address")
    labels = host.split(".")
    if len(labels) < 2 or not all(HOSTNAME_LABEL.match(label) for label in labels):
        raise ValueError(f"CTA link '{url}' has an invalid domain")
    if not re.fullmatch(r"[a-z]{2,63}", labels[-1], re.IGNORECASE):
        raise ValueError(f"CTA link '{url}' has an invalid top-level domain")


class PostRequest(BaseModel):
    message: str = Field(
        ...,
        description="Message to publish (max 200 characters, exactly one http(s) CTA link).",
        examples=["Check out our latest business platform and grow your online visibility. https://example.com"],
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be empty")
        if len(value) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"Message must not exceed {MAX_MESSAGE_LENGTH} characters (got {len(value)})"
            )
        links = extract_links(value)
        if len(links) == 0:
            raise ValueError("Message must include exactly one CTA link (found none)")
        if len(links) > 1:
            raise ValueError(f"Message must include exactly one CTA link (found {len(links)})")
        validate_url(links[0])
        if not LINK_PATTERN.sub("", value).strip():
            raise ValueError("Message must contain text in addition to the CTA link")
        return value

    @property
    def cta_link(self) -> str:
        return extract_links(self.message)[0]


class PostStatus(str, Enum):
    success = "success"
    failed = "failed"


class PlatformResult(BaseModel):
    platform: str
    status: PostStatus
    posted_url: Optional[str] = None
    public_access: bool = False
    date: Optional[str] = None
    time: Optional[str] = None
    error: Optional[str] = None


class PostResponse(BaseModel):
    success: bool = Field(..., description="True when at least one platform succeeded.")
    message: str
    total_platforms: int
    successful: int
    failed: int
    results: list[PlatformResult]


class ErrorResponse(BaseModel):
    success: bool = False
    errors: list[str]
