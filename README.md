# Automated Multi-Platform Posting System

A FastAPI service that takes one short message and publishes it to **7 third-party platforms** through their official APIs. It runs them concurrently and reports a result for each one. If one platform fails, the others still post.

```
POST http://localhost:4000/posting   →   Telegraph · Mastodon · Bluesky · Telegram · Discord · GitHub Gist · Hugging Face
```

## Platforms integrated

| # | Platform | API used | Auth | Public link? |
|---|----------|----------|------|--------------|
| 1 | **Telegraph** (telegra.ph) | [`createAccount`, `createPage`](https://telegra.ph/api) | None needed (account auto-created) | ✅ |
| 2 | **Mastodon** | [`POST /api/v1/statuses`](https://docs.joinmastodon.org/methods/statuses/#create) | Bearer token (`write:statuses`) | ✅ |
| 3 | **Bluesky** (AT Protocol) | [`createSession` + `createRecord`](https://docs.bsky.app/docs/advanced-guides/posts) | Handle + app password | ✅ |
| 4 | **Telegram** | [Bot API `sendMessage`](https://core.telegram.org/bots/api#sendmessage) | Bot token, bot is admin of channel | ✅ public channel / ❌ private |
| 5 | **Discord** | [Execute Webhook `?wait=true`](https://discord.com/developers/docs/resources/webhook#execute-webhook) | Webhook URL | ❌ members only |
| 6 | **GitHub Gist** | [`POST /gists`](https://docs.github.com/en/rest/gists/gists#create-a-gist) | PAT (`gist` scope) | ✅ |
| 7 | **Hugging Face Hub** (LLM platform) | [`POST /api/{type}s/{repo}/discussions`](https://huggingface.co/docs/huggingface_hub/guides/community) | Write token | ✅ |

Notes from the research:
- **Bluesky** only makes a link clickable if you send it as a *facet* with UTF-8 **byte** offsets, not character offsets. The integration works these out so the CTA link stays clickable even when the message has emoji or other non-ASCII text.
- **Mastodon** requests carry an `Idempotency-Key` header, so a retried request won't create a duplicate post.
- **Discord** webhooks return the created message only when you add `?wait=true`. `allowed_mentions` is set to empty so a message can't ping `@everyone`.
- **Telegram** and **Discord** report `public_access` honestly. A private channel or server link is returned with `public_access: false`.
- **Telegraph** needs no credentials, so you can try the project right after cloning.

## Project structure

```
automated-posting/
├── app/
│   ├── main.py                    # FastAPI app, /posting + /health, validation error handler
│   ├── schemas.py                 # Pydantic models + message/URL validation
│   ├── config.py                  # Settings from environment / .env
│   ├── platforms/
│   │   ├── __init__.py            # platform registry (internal platform selection)
│   │   ├── base.py                # BasePlatform interface + shared HTTP error mapping
│   │   ├── telegraph.py  mastodon.py  bluesky.py  telegram.py
│   │   └── discord.py    github_gist.py  huggingface.py
│   └── services/
│       └── posting_service.py     # concurrent fan-out, per-platform isolation, timestamps
├── tests/test_posting.py          # 16 tests, HTTP mocked with httpx.MockTransport
├── .env.example
├── requirements.txt
└── README.md
```

## Setup and run

```bash
git clone <this-repo> && cd automated-posting
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # add credentials for the platforms you use
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

- Swagger UI: http://localhost:4000/docs
- Configuration check: `GET http://localhost:4000/health` shows which platforms are configured.
- Logs: written to the console and to `logs/posting.log`.

Run the tests:

```bash
pytest -q
```

## API

### `POST /posting`

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

#### Validation rules (422 on failure)

| Rule | Example error |
|------|---------------|
| Message required and not blank | `message: Message must not be empty` |
| ≤ 200 characters | `message: Message must not exceed 200 characters (got 205)` |
| Exactly one CTA link | `message: Message must include exactly one CTA link (found 2)` |
| Link must be `http(s)://` | `message: CTA link 'www.example.com' must start with http:// or https://` |
| Valid domain, not an IP or `localhost` | `message: CTA link 'http://192.168.0.1/page' must use a domain name, not an IP address` |
| Text besides the link | `message: Message must contain text in addition to the CTA link` |

```json
{ "success": false, "errors": ["message: Message must include exactly one CTA link (found 2)"] }
```

#### Success response (200)

`success` is `true` when at least one platform posted. Every platform always gets an entry.

```json
{
  "success": true,
  "message": "Check out our latest business platform and grow your online visibility. https://example.com",
  "total_platforms": 7,
  "successful": 6,
  "failed": 1,
  "results": [
    {
      "platform": "Telegraph",
      "status": "success",
      "posted_url": "https://telegra.ph/Check-out-our-latest-business-platform-11-17",
      "public_access": true,
      "date": "2026-11-17",
      "time": "20:15:04",
      "error": null
    },
    {
      "platform": "GitHub Gist",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Authentication failed (401): Bad credentials"
    }
  ]
}
```

> Replace this sample with the real response from your own run (see *Screenshots* below).

## Error handling

- Each platform runs in its own `try` block inside `asyncio.gather`, so one failure never affects the others.
- Failures are turned into readable messages: missing config (`Not configured: missing X`), `401/403` (authentication failed), `429` (rate limited), other HTTP errors with the provider's own error text, timeouts, network errors, and unexpected response shapes.
- Every outgoing request uses a shared timeout (`REQUEST_TIMEOUT`, default 15s).
- Credentials come only from environment variables. `.env` is git-ignored.

## Design decisions

- **Platform selection is internal.** Every platform in `app/platforms/__init__.py` is used. Adding a platform means one new class with a `publish()` method, plus one line in the registry.
- **Concurrent posting.** One shared `httpx.AsyncClient` posts to all platforms in parallel, so the response takes about as long as the slowest platform, not the sum of all of them.
- **Testable without network access.** The service accepts an injectable `httpx` transport. The tests replay each provider's documented response format.

## Screenshots / logs

_Add a screenshot of `/docs`, the JSON response, and the live posts here, plus an excerpt of `logs/posting.log`._
