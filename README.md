# Automated Multi-Platform Posting System

A **FastAPI** application that takes a short message through one REST endpoint and publishes it to **7 third-party platforms** through their official APIs. Each platform is handled on its own: if one fails, the others still post, and the response reports a separate result for every platform.

```
POST http://localhost:4000/posting
        │
        ├── Telegraph      (telegra.ph)
        ├── Mastodon
        ├── Bluesky        (AT Protocol)
        ├── Telegram       (Bot API)
        ├── Discord        (Webhook)
        ├── GitHub Gist
        └── Hugging Face   (LLM platform)
```

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Integrated Platforms](#integrated-platforms)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Installation](#installation)
7. [Configuration (.env)](#configuration-env)
8. [Running the Server](#running-the-server)
9. [How to Test](#how-to-test)
10. [API Reference](#api-reference)
11. [Input Validation Rules](#input-validation-rules)
12. [Error Handling](#error-handling)
13. [Design Decisions](#design-decisions)
14. [Screenshots and Logs](#screenshots-and-logs)
15. [Troubleshooting](#troubleshooting)
16. [Security](#security)

---

## Features

- A single REST endpoint: `POST /posting`
- Strict input validation: at most 200 characters, exactly one CTA link, URL format checks
- The application chooses the platforms itself; the client never selects them
- **Concurrent posting** with `asyncio.gather` and a shared `httpx.AsyncClient`
- **Platforms are isolated**: one failure never stops the rest
- A structured result for each platform: status, URL, public access, date, time and error
- API credentials loaded from environment variables
- A `/health` endpoint that shows which platforms are configured
- Logs written to the console and to `logs/posting.log`
- 16 automated tests with all HTTP calls mocked, so no network or credentials are needed

## Tech Stack

| Component        | Technology                  |
|------------------|-----------------------------|
| Language         | Python 3.10+                |
| Web framework    | FastAPI                     |
| ASGI server      | Uvicorn                     |
| Validation       | Pydantic v2                 |
| Settings         | pydantic-settings (`.env`)  |
| HTTP client      | HTTPX (async)               |
| Testing          | Pytest + `httpx.MockTransport` |

---

## Integrated Platforms

| # | Platform | Official API | Authentication | Public URL |
|---|----------|--------------|----------------|------------|
| 1 | **Telegraph** | [Telegraph API](https://telegra.ph/api): `createAccount`, `createPage` | None (account created automatically) | Yes |
| 2 | **Mastodon** | [`POST /api/v1/statuses`](https://docs.joinmastodon.org/methods/statuses/#create) | Bearer token (`write:statuses`) | Yes |
| 3 | **Bluesky** | [AT Protocol](https://docs.bsky.app/docs/advanced-guides/posts): `createSession`, `createRecord` | Handle + App Password | Yes |
| 4 | **Telegram** | [Bot API `sendMessage`](https://core.telegram.org/bots/api#sendmessage) | Bot token | Yes for a public channel |
| 5 | **Discord** | [Execute Webhook](https://discord.com/developers/docs/resources/webhook#execute-webhook) | Webhook URL | No, server members only |
| 6 | **GitHub Gist** | [`POST /gists`](https://docs.github.com/en/rest/gists/gists#create-a-gist) | Personal Access Token (`gist`) | Yes |
| 7 | **Hugging Face** | [Hub Discussions API](https://huggingface.co/docs/huggingface_hub/guides/community) | Write token | Yes |

### Implementation notes

- **Bluesky:** links only become clickable when sent as *rich-text facets* with UTF-8 **byte** offsets. The integration calculates these offsets so the CTA link stays clickable.
- **Mastodon:** every request sends an `Idempotency-Key` header, so a retried request cannot create a duplicate post.
- **Discord:** the webhook is called with `?wait=true` so that Discord returns the created message. `allowed_mentions` is empty, so the message can never ping `@everyone`.
- **Telegram:** a public channel returns a `https://t.me/<channel>/<id>` link. A private channel is reported as `public_access: false`.
- **Telegraph:** needs no credentials, so the project works right after cloning.

---

## Project Structure

```
automated-posting/
│
├── app/
│   ├── main.py                    # FastAPI app, routes, validation error handler
│   ├── schemas.py                 # Request/response models and message validation
│   ├── config.py                  # Environment-based settings
│   ├── platforms/
│   │   ├── __init__.py            # Platform registry (internal platform selection)
│   │   ├── base.py                # Abstract BasePlatform and shared error mapping
│   │   ├── telegraph.py
│   │   ├── mastodon.py
│   │   ├── bluesky.py
│   │   ├── telegram.py
│   │   ├── discord.py
│   │   ├── github_gist.py
│   │   └── huggingface.py
│   └── services/
│       └── posting_service.py     # Concurrent fan-out, error isolation, timestamps
│
├── tests/
│   └── test_posting.py            # 16 tests (validation, posting, failures)
│
├── .env.example                   # Template for credentials
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Prerequisites

- **Python 3.10 or newer** (check with `python --version`)
- **pip**
- **Git**
- Optional: accounts on the platforms you want to post to (see [Configuration](#configuration-env))

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/SwAsTiK-KuL/Automated-Multi-Platform-Posting-System.git
cd Automated-Multi-Platform-Posting-System
```

### 2. Create and activate a virtual environment

**Windows (PowerShell / CMD)**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

> On Windows, if PowerShell blocks the activation script, run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create your environment file

**Windows**
```powershell
copy .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

---

## Configuration (.env)

Open `.env` and fill in the credentials for the platforms you want to use. Any platform left blank is reported as `failed` with the error `Not configured: missing <VARIABLE>`, and the other platforms still post.

> If you are not using a platform, leave its values **empty**. Do not leave placeholder text such as `yourname.bsky.social`, because the app will try to use it and report an authentication failure.

| Variable | Where to get it |
|----------|-----------------|
| `TELEGRAPH_ACCESS_TOKEN` | Optional. Leave empty and an account is created automatically. |
| `MASTODON_INSTANCE_URL` | Your server, e.g. `https://mastodon.social` |
| `MASTODON_ACCESS_TOKEN` | Mastodon → Preferences → Development → **New application** → tick `write:statuses` → Submit → open the app → copy **Your access token** |
| `BLUESKY_HANDLE` | Your full handle, e.g. `yourname.bsky.social` |
| `BLUESKY_APP_PASSWORD` | bsky.app → Settings → Privacy and security → **App passwords** → Add |
| `TELEGRAM_BOT_TOKEN` | Message **@BotFather** on Telegram → `/newbot` → copy the token |
| `TELEGRAM_CHAT_ID` | Create a **public** channel, add your bot as **admin**, use `@channelusername` |
| `DISCORD_WEBHOOK_URL` | Discord Server Settings → Integrations → Webhooks → **New Webhook** → Copy URL |
| `DISCORD_GUILD_ID` | Optional. Right-click the server → Copy Server ID (needs Developer Mode) |
| `GITHUB_TOKEN` | github.com/settings/tokens → Generate new token (classic) → tick `gist` |
| `HUGGINGFACE_TOKEN` | huggingface.co/settings/tokens → New token with **write** access |
| `HUGGINGFACE_REPO_ID` | A repo you own, e.g. `username/my-model` |
| `HUGGINGFACE_REPO_TYPE` | `model`, `dataset` or `space` |
| `REQUEST_TIMEOUT` | HTTP timeout in seconds (default `15`) |
| `TIMEZONE` | Time zone for the date/time fields (default `Asia/Kolkata`) |

Example `.env`:

```env
REQUEST_TIMEOUT=15
TIMEZONE=Asia/Kolkata

MASTODON_INSTANCE_URL=https://mastodon.social
MASTODON_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

BLUESKY_HANDLE=yourname.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

TELEGRAM_BOT_TOKEN=123456789:AAxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=@your_channel

GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Running the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Expected output:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:4000 (Press CTRL+C to quit)
```

| URL | Purpose |
|-----|---------|
| http://localhost:4000/docs | Swagger UI (interactive API docs) |
| http://localhost:4000/redoc | ReDoc documentation |
| http://localhost:4000/health | Shows which platforms are configured |

> Open the server in your browser at `localhost` or `127.0.0.1`, **not** `0.0.0.0`.
> After changing `.env`, stop the server with `Ctrl+C` and start it again.

---

## How to Test

There are four ways to test the application.

### Option 1: Swagger UI (easiest)

1. Start the server.
2. Open **http://localhost:4000/docs**.
3. Expand **`POST /posting`** and click **Try it out**.
4. Paste this request body:
   ```json
   {
     "message": "Check out our latest business platform and grow your online visibility. https://example.com"
   }
   ```
5. Click **Execute** and look at the **Response body**.
6. Open each `posted_url` in the response to check that the post is live.

To check configuration, expand **`GET /health`** and click **Execute**.

### Option 2: curl (macOS / Linux / Git Bash)

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

```bash
curl http://localhost:4000/health
```

### Option 3: PowerShell (Windows)

```powershell
$body = @{ message = "Check out our latest business platform and grow your online visibility. https://example.com" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:4000/posting -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 5
```

```powershell
Invoke-RestMethod http://localhost:4000/health | ConvertTo-Json
```

### Option 4: Automated tests (pytest)

The test suite mocks every external API with `httpx.MockTransport`, so it runs **without internet access or credentials**.

```bash
pytest -q
```

Expected output:

```
................                                                [100%]
16 passed in 0.9s
```

Run with detailed output:

```bash
pytest -v
```

**What the tests cover**

| Area | Test cases |
|------|------------|
| Validation | Message longer than 200 characters, no link, two links, `www.` link without a scheme, `localhost` host, IP address host, invalid top-level domain, link with no text, empty message, missing field |
| Link parsing | Trailing punctuation (`https://example.com.`) is not treated as part of the URL |
| Posting | All 7 platforms succeed and each returns the expected URL format |
| Isolation | GitHub returns 401 and Telegram times out, while the other 5 still succeed |
| Configuration | Unconfigured platforms fail cleanly with `Not configured` |
| Overall status | `success: false` when every platform fails |
| Health | `/health` lists all 7 platforms |
| Bluesky | Link facet byte offsets match the URL exactly |

### Validation test examples

Try these in Swagger or curl to see the validation errors:

| Request message | Expected result |
|-----------------|-----------------|
| `"Hello world"` | 422: no CTA link |
| `"Visit https://a.com and https://b.com"` | 422: found 2 links |
| `"Visit www.example.com"` | 422: must start with http:// or https:// |
| `"Visit http://192.168.1.1"` | 422: IP address not allowed |
| A message longer than 200 characters | 422: exceeds 200 characters |
| `"https://example.com"` | 422: text required besides the link |

---

## API Reference

### `POST /posting`

Publishes the message to every platform.

**Request**

```http
POST /posting HTTP/1.1
Host: localhost:4000
Content-Type: application/json

{
  "message": "Check out our latest business platform and grow your online visibility. https://example.com"
}
```

**Response `200 OK`**

`success` is `true` when **at least one** platform posted. Every platform always appears in `results`.

```json
{
  "success": true,
  "message": "Check out our latest business platform and grow your online visibility. https://example.com",
  "total_platforms": 7,
  "successful": 5,
  "failed": 2,
  "results": [
    {
      "platform": "Telegraph",
      "status": "success",
      "posted_url": "https://telegra.ph/Check-out-our-latest-business-platform-and-grow-your-online-visibility-11-17",
      "public_access": true,
      "date": "2026-11-17",
      "time": "20:30:12",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@yourname/113512345678901234",
      "public_access": true,
      "date": "2026-11-17",
      "time": "20:30:12",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Not configured: missing DISCORD_WEBHOOK_URL"
    }
  ]
}
```

> The response above is an example. Replace it with the real output from your run.

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `platform` | string | Platform name |
| `status` | `success` / `failed` | Result of the post |
| `posted_url` | string / null | URL of the published content |
| `public_access` | boolean | Whether anyone can view the content without logging in |
| `date` | string / null | Posting date (`YYYY-MM-DD`) |
| `time` | string / null | Posting time (`HH:MM:SS`) |
| `error` | string / null | Error details when the post failed |

**Response `422 Unprocessable Entity`** (validation error)

```json
{
  "success": false,
  "errors": ["message: Message must include exactly one CTA link (found 2)"]
}
```

### `GET /health`

```json
{
  "status": "ok",
  "platforms": {
    "Telegraph": "configured",
    "Mastodon": "configured",
    "Bluesky": "configured",
    "Telegram": "configured",
    "Discord": "missing DISCORD_WEBHOOK_URL",
    "GitHub Gist": "configured",
    "Hugging Face": "missing HUGGINGFACE_TOKEN, HUGGINGFACE_REPO_ID"
  }
}
```

---

## Input Validation Rules

| Rule | Error message |
|------|---------------|
| Message is required and not blank | `Message must not be empty` |
| At most **200** characters | `Message must not exceed 200 characters (got N)` |
| **Exactly one** CTA link | `Message must include exactly one CTA link (found N)` |
| Link uses `http://` or `https://` | `CTA link '...' must start with http:// or https://` |
| Link has a valid domain | `CTA link '...' has an invalid domain` |
| Link is not an IP address | `CTA link '...' must use a domain name, not an IP address` |
| Link has a valid top-level domain | `CTA link '...' has an invalid top-level domain` |
| Message has text besides the link | `Message must contain text in addition to the CTA link` |

---

## Error Handling

Every platform runs in its own error boundary, so no failure can affect another platform.

| Situation | Reported error |
|-----------|----------------|
| Missing credentials | `Not configured: missing MASTODON_ACCESS_TOKEN` |
| Invalid token (401/403) | `Authentication failed (401): <provider message>` |
| Rate limit (429) | `Rate limited by <platform> (429): ...` |
| Other HTTP error | `HTTP <code> from <platform>: <provider message>` |
| Timeout | `Request to <platform> timed out after 15.0s` |
| Network error | `Network error contacting <platform>: ...` |
| Unexpected response | `Unexpected error: ...` (also logged with a stack trace) |

---

## Design Decisions

- **Plugin-style platforms:** each platform is a class that extends `BasePlatform` and implements one `publish()` method. Adding a platform takes one new file and one line in `app/platforms/__init__.py`.
- **Internal platform selection:** the registry decides which platforms receive the message. The API client only sends the message.
- **Concurrent posting:** all platforms are called in parallel, so the response time is about the time of the slowest platform, not the sum of all of them.
- **Dependency injection:** `PostingService` accepts an optional HTTPX transport, so tests can replace the network with a mock.
- **Configuration from the environment:** all credentials come from environment variables through `pydantic-settings`, and none are hard-coded.

---

## Screenshots and Logs

### Swagger UI
![Swagger UI](screenshots/swagger.png)

### Successful API response
![API Response](screenshots/response.png)

### Live posts
![Telegraph](screenshots/telegraph.png)
![Mastodon](screenshots/mastodon.png)
![Bluesky](screenshots/bluesky.png)

### Test results
![Pytest](screenshots/pytest.png)

### Sample log (`logs/posting.log`)

```
2026-11-17 20:30:11,902 INFO    posting: Posting to 7 platforms: 'Check out our latest business platform ... https://example.com'
2026-11-17 20:30:12,410 INFO    posting: [Telegraph] SUCCESS https://telegra.ph/Check-out-our-latest-business-platform-11-17 (public=True)
2026-11-17 20:30:12,655 INFO    posting: [Mastodon] SUCCESS https://mastodon.social/@yourname/113512345678901234 (public=True)
2026-11-17 20:30:12,661 WARNING posting: [Discord] FAILED Not configured: missing DISCORD_WEBHOOK_URL
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ERR_ADDRESS_INVALID` in the browser | Use `http://localhost:4000/docs`, not `0.0.0.0` |
| `ZoneInfoNotFoundError: Asia/Kolkata` (Windows) | Run `pip install tzdata` (it is already in `requirements.txt`) |
| `python` is not recognized | Use `py` instead, or add Python to PATH |
| PowerShell blocks `activate` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| A platform shows `Not configured` | Add its variables to `.env` and restart the server |
| `Authentication failed (401)` | Check the token or password. Bluesky needs an **App Password**, not your login password |
| Telegram `chat not found` | Make sure the channel is public and the bot is an **admin** |
| Port 4000 already in use | Stop the other process or use `--port 4001` |

---

## Security

- `.env` is listed in `.gitignore` and is **never committed**.
- Only `.env.example` (without real values) is in the repository.
- Tokens use the minimum required scopes (`gist`, `write:statuses`, an App Password).
- Remove any tokens from screenshots before sharing them.

---

## Author

**Swastik Kulkarni**
GitHub: [@SwAsTiK-KuL](https://github.com/SwAsTiK-KuL)
