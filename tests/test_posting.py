import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app, get_posting_service
from app.platforms import build_platforms
from app.platforms.telegraph import TelegraphPlatform
from app.services.posting_service import PostingService

VALID = "Check out our latest business platform and grow your online visibility. https://example.com"

FULL_SETTINGS = Settings(
    _env_file=None,
    telegraph_access_token="tg-token",
    mastodon_instance_url="https://mastodon.social",
    mastodon_access_token="m-token",
    bluesky_handle="me.bsky.social",
    bluesky_app_password="app-pass",
    telegram_bot_token="123:abc",
    telegram_chat_id="@mychannel",
    discord_webhook_url="https://discord.com/api/webhooks/1/xyz",
    discord_guild_id="999",
    github_token="gh-token",
    huggingface_token="hf-token",
    huggingface_repo_id="me/my-model",
)


def fake_api(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "api.telegra.ph/createPage" in url:
        return httpx.Response(200, json={"ok": True, "result": {"url": "https://telegra.ph/Check-out-11-17"}})
    if "mastodon.social/api/v1/statuses" in url:
        assert request.headers["Authorization"] == "Bearer m-token"
        return httpx.Response(200, json={"url": "https://mastodon.social/@me/1", "visibility": "public"})
    if "createSession" in url:
        return httpx.Response(200, json={"accessJwt": "jwt", "did": "did:plc:abc", "handle": "me.bsky.social"})
    if "createRecord" in url:
        record = json.loads(request.content)["record"]
        facet = record["facets"][0]["index"]
        assert record["text"].encode()[facet["byteStart"]:facet["byteEnd"]] == b"https://example.com"
        return httpx.Response(200, json={"uri": "at://did:plc:abc/app.bsky.feed.post/3kxyz", "cid": "c"})
    if "api.telegram.org" in url:
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42, "chat": {"id": -1001, "username": "mychannel"}}})
    if "discord.com/api/webhooks" in url:
        assert request.url.params["wait"] == "true"
        return httpx.Response(200, json={"id": "555", "channel_id": "777"})
    if "api.github.com/gists" in url:
        return httpx.Response(201, json={"html_url": "https://gist.github.com/me/abc", "public": True})
    if "huggingface.co/api/models/me/my-model/discussions" in url:
        return httpx.Response(200, json={"num": 3})
    return httpx.Response(404, json={"error": f"unmocked {url}"})


def make_client(settings: Settings, handler=fake_api) -> TestClient:
    service = PostingService(settings, build_platforms(settings), transport=httpx.MockTransport(handler))
    app.dependency_overrides[get_posting_service] = lambda: service
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)
    TelegraphPlatform._cached_token = None
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "message, expected",
    [
        ("x" * 190 + " https://a.com", "must not exceed 200 characters"),
        ("No link here at all", "found none"),
        ("Two links https://a.com and https://b.com", "found 2"),
        ("Bare www link www.example.com", "must start with http"),
        ("Bad host https://localhost/page", "invalid domain"),
        ("IP host http://192.168.0.1/page", "not an IP address"),
        ("Bad tld https://example.c0m", "invalid top-level domain"),
        ("https://example.com", "text in addition"),
        ("   ", "must not be empty"),
    ],
)
def test_validation_errors(message, expected):
    resp = make_client(FULL_SETTINGS).post("/posting", json={"message": message})
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert any(expected in e for e in body["errors"]), body


def test_missing_message_field():
    resp = make_client(FULL_SETTINGS).post("/posting", json={})
    assert resp.status_code == 422 and resp.json()["errors"][0].startswith("message")


def test_trailing_punctuation_is_not_part_of_link():
    resp = make_client(FULL_SETTINGS).post("/posting", json={"message": "Visit https://example.com."})
    assert resp.status_code == 200


def test_posts_to_all_platforms():
    resp = make_client(FULL_SETTINGS).post("/posting", json={"message": VALID})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True and body["successful"] == 7 and body["failed"] == 0
    urls = {r["platform"]: r["posted_url"] for r in body["results"]}
    assert urls == {
        "Telegraph": "https://telegra.ph/Check-out-11-17",
        "Mastodon": "https://mastodon.social/@me/1",
        "Bluesky": "https://bsky.app/profile/me.bsky.social/post/3kxyz",
        "Telegram": "https://t.me/mychannel/42",
        "Discord": "https://discord.com/channels/999/777/555",
        "GitHub Gist": "https://gist.github.com/me/abc",
        "Hugging Face": "https://huggingface.co/me/my-model/discussions/3",
    }
    for r in body["results"]:
        assert r["status"] == "success" and r["date"] and r["time"] and r["error"] is None
    assert {r["platform"]: r["public_access"] for r in body["results"]}["Discord"] is False


def test_one_failure_does_not_stop_others():
    def handler(request):
        if "api.github.com" in str(request.url):
            return httpx.Response(401, json={"message": "Bad credentials"})
        if "api.telegram.org" in str(request.url):
            raise httpx.ConnectTimeout("timed out")
        return fake_api(request)

    body = make_client(FULL_SETTINGS, handler).post("/posting", json={"message": VALID}).json()
    by_name = {r["platform"]: r for r in body["results"]}
    assert body["success"] is True and body["successful"] == 5 and body["failed"] == 2
    assert by_name["GitHub Gist"]["error"] == "Authentication failed (401): Bad credentials"
    assert "timed out" in by_name["Telegram"]["error"]
    assert by_name["GitHub Gist"]["posted_url"] is None and by_name["GitHub Gist"]["date"] is None


def test_unconfigured_platforms_fail_gracefully():
    settings = Settings(_env_file=None)

    def handler(request):
        if "createAccount" in str(request.url):
            return httpx.Response(200, json={"ok": True, "result": {"access_token": "new"}})
        return fake_api(request)

    body = make_client(settings, handler).post("/posting", json={"message": VALID}).json()
    by_name = {r["platform"]: r for r in body["results"]}
    assert by_name["Telegraph"]["status"] == "success"
    assert by_name["Mastodon"]["error"] == "Not configured: missing MASTODON_INSTANCE_URL, MASTODON_ACCESS_TOKEN"
    assert body["successful"] == 1 and body["failed"] == 6


def test_all_fail_returns_success_false():
    body = make_client(Settings(_env_file=None), lambda r: httpx.Response(500, text="boom")) \
        .post("/posting", json={"message": VALID}).json()
    assert body["success"] is False and body["successful"] == 0


def test_health_lists_platforms():
    body = make_client(FULL_SETTINGS).get("/health").json()
    assert body["status"] == "ok" and len(body["platforms"]) == 7
