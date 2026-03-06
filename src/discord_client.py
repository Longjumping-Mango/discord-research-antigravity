"""
Discord Research Tool — Discord REST API Client
Async HTTP client with anti-detection headers, rate limiting, and all API methods.
"""

import asyncio
import base64
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from utils import print_error

# Token: reads from environment variable or --token CLI flag
USER_TOKEN = os.environ.get("DISCORD_USER_TOKEN", "")

API_BASE = "https://discord.com/api/v10"

# Default build number (will be dynamically updated at startup)
_cached_build_number: Optional[int] = None
_build_number_fetched_at: float = 0


def set_token(token: str):
    """Override the token at runtime (used by --token CLI flag)."""
    global USER_TOKEN
    USER_TOKEN = token


def _get_system_timezone() -> str:
    """Get the system timezone name for Discord headers."""
    try:
        import time as _time
        offset = -_time.timezone if _time.daylight == 0 else -_time.altzone
        hours = offset // 3600
        if hours == 0:
            return "Etc/UTC"
        sign = "+" if hours > 0 else "-"
        return f"Etc/GMT{'+' if hours < 0 else '-'}{abs(hours)}"
    except Exception:
        return "Etc/UTC"


def _generate_super_properties(build_number: int = 250426) -> str:
    """Generate base64-encoded X-Super-Properties header mimicking Discord web client."""
    props = {
        "os": "Windows",
        "browser": "Chrome",
        "device": "",
        "system_locale": "en-US",
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "browser_version": "131.0.0.0",
        "os_version": "10",
        "referrer": "",
        "referring_domain": "",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": build_number,
        "client_event_source": None,
    }
    return base64.b64encode(json.dumps(props, separators=(",", ":")).encode()).decode()


def _get_headers(build_number: int = 250426) -> dict[str, str]:
    """Get request headers mimicking Discord web client."""
    return {
        "Authorization": USER_TOKEN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "X-Super-Properties": _generate_super_properties(build_number),
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": _get_system_timezone(),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


async def fetch_build_number() -> int:
    """Fetch current Discord client build number from web assets."""
    global _cached_build_number, _build_number_fetched_at

    # Cache for 24 hours
    if _cached_build_number and (time.time() - _build_number_fetched_at) < 86400:
        return _cached_build_number

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://discord.com/app", headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if resp.status_code != 200:
                print_error(f"Warning: Could not fetch Discord app page (status {resp.status_code}), using default build number")
                return 250426

            js_files = re.findall(r'/assets/([a-f0-9]+)\.js', resp.text)
            if not js_files:
                return 250426

            for js_hash in reversed(js_files[-5:]):
                js_url = f"https://discord.com/assets/{js_hash}.js"
                js_resp = await client.get(js_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                if js_resp.status_code == 200:
                    match = re.search(r'buildNumber["\s:=]+["\s]*(\d{5,7})', js_resp.text)
                    if not match:
                        match = re.search(r'"build_number","(\d{5,7})"', js_resp.text)
                    if not match:
                        match = re.search(r'client_build_number:\s*(\d{5,7})', js_resp.text)
                    if match:
                        _cached_build_number = int(match.group(1))
                        _build_number_fetched_at = time.time()
                        return _cached_build_number

    except Exception as e:
        print_error(f"Warning: Could not fetch build number: {e}, using default")

    return 250426


class RateLimiter:
    """Handles Discord API rate limiting."""

    def __init__(self):
        self._buckets: dict[str, dict] = {}
        self._global_lock = asyncio.Lock()
        self._global_reset_at: float = 0

    async def wait_if_needed(self, route: str):
        """Wait if rate limited for this route or globally."""
        now = time.time()
        if self._global_reset_at > now:
            wait = self._global_reset_at - now + 0.5
            print_error(f"  [Rate Limit] Global limit, waiting {wait:.1f}s...")
            await asyncio.sleep(wait)

        bucket = self._buckets.get(route)
        if bucket and bucket.get("remaining", 1) <= 0:
            reset_at = bucket.get("reset_at", 0)
            if reset_at > now:
                wait = reset_at - now + 1.0
                wait = min(wait, 60.0)
                print_error(f"  [Rate Limit] Route {route}, waiting {wait:.1f}s...")
                await asyncio.sleep(wait)

    def update_from_headers(self, route: str, headers: httpx.Headers):
        """Update rate limit state from response headers."""
        remaining = headers.get("x-ratelimit-remaining")
        reset_after = headers.get("x-ratelimit-reset-after")

        if remaining is not None:
            try:
                self._buckets[route] = {
                    "remaining": int(remaining),
                    "reset_at": time.time() + float(reset_after or 1),
                }
            except (ValueError, TypeError):
                pass

    def handle_429(self, headers: httpx.Headers, body: dict):
        """Handle a 429 Too Many Requests response."""
        retry_after = body.get("retry_after", headers.get("retry-after", 5))
        is_global = body.get("global", False)

        try:
            retry_after = float(retry_after)
        except (ValueError, TypeError):
            retry_after = 5.0

        retry_after = min(retry_after + 1.0, 60.0)

        if is_global:
            self._global_reset_at = time.time() + retry_after

        return retry_after


class DiscordClient:
    """Async Discord REST API client with anti-detection and rate limiting."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter()
        self._build_number = 250426
        self._initialized = False

    async def _ensure_initialized(self):
        """Initialize client on first use."""
        if self._initialized:
            return
        if not USER_TOKEN:
            raise RuntimeError(
                "No Discord token configured. Set the DISCORD_USER_TOKEN environment variable "
                "or use the --token flag. See README for instructions on how to get your token."
            )
        self._build_number = await fetch_build_number()
        self._client = httpx.AsyncClient(
            timeout=30,
            headers=_get_headers(self._build_number),
            follow_redirects=True,
        )
        self._initialized = True

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._initialized = False

    async def _request(self, method: str, path: str, params: Optional[dict] = None,
                       json_body: Optional[dict] = None, max_retries: int = 3) -> dict | list | None:
        """Make an API request with rate limiting and retry logic."""
        await self._ensure_initialized()
        url = f"{API_BASE}{path}"
        route = f"{method}:{path.split('?')[0]}"

        for attempt in range(max_retries):
            await self._rate_limiter.wait_if_needed(route)

            # Human-like pacing (150-500ms random delay)
            if attempt == 0:
                await asyncio.sleep(random.uniform(0.15, 0.5))

            try:
                response = await self._client.request(
                    method, url, params=params, json=json_body
                )

                self._rate_limiter.update_from_headers(route, response.headers)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 204:
                    return []
                elif response.status_code == 429:
                    body = response.json() if response.content else {}
                    retry_after = self._rate_limiter.handle_429(response.headers, body)
                    print_error(f"  [429] Rate limited, retrying in {retry_after:.1f}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_after)
                    continue
                elif response.status_code in (401, 403):
                    error_msg = response.json().get("message", "Unknown error") if response.content else "Unknown"
                    print_error(f"  [Auth Error {response.status_code}] {error_msg}")
                    return None
                elif response.status_code == 404:
                    return None
                else:
                    print_error(f"  [HTTP {response.status_code}] {response.text[:200]}")
                    if attempt < max_retries - 1:
                        wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                        await asyncio.sleep(wait)
                    continue

            except httpx.TimeoutException:
                print_error(f"  [Timeout] Attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
            except httpx.HTTPError as e:
                print_error(f"  [HTTP Error] {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue

        print_error(f"  [Failed] All {max_retries} retries exhausted for {path}")
        return None

    # ── User ──

    async def get_current_user(self) -> Optional[dict]:
        """Get the current authenticated user."""
        return await self._request("GET", "/users/@me")

    # ── Guilds ──

    async def get_guilds(self) -> list[dict]:
        """Get all guilds the user is a member of (auto-paginated)."""
        guilds = []
        after = "0"
        while True:
            batch = await self._request("GET", "/users/@me/guilds", params={
                "limit": "100",
                "after": after,
            })
            if not batch:
                break
            guilds.extend(batch)
            if len(batch) < 100:
                break
            after = batch[-1]["id"]
        return guilds

    # ── Channels ──

    async def get_guild_channels(self, guild_id: str) -> list[dict]:
        """Get all channels in a guild."""
        result = await self._request("GET", f"/guilds/{guild_id}/channels")
        return result or []

    # ── Messages ──

    async def get_messages(self, channel_id: str, limit: int = 50,
                           before: Optional[str] = None, after: Optional[str] = None) -> list[dict]:
        """Fetch messages from a channel (auto-paginated up to limit)."""
        all_messages = []
        remaining = limit
        current_before = before
        current_after = after

        while remaining > 0:
            batch_size = min(remaining, 100)
            params: dict[str, str] = {"limit": str(batch_size)}
            if current_before:
                params["before"] = current_before
            if current_after:
                params["after"] = current_after

            batch = await self._request("GET", f"/channels/{channel_id}/messages", params=params)
            if not batch:
                break

            all_messages.extend(batch)
            remaining -= len(batch)

            if len(batch) < batch_size:
                break

            if current_after:
                current_after = batch[0]["id"]
            else:
                current_before = batch[-1]["id"]

        all_messages.sort(key=lambda m: m.get("id", "0"))
        return all_messages

    async def get_messages_around(self, channel_id: str, message_id: str,
                                   limit: int = 50) -> list[dict]:
        """Get messages around a specific message."""
        capped = min(limit, 100)
        result = await self._request("GET", f"/channels/{channel_id}/messages", params={
            "around": message_id,
            "limit": str(capped),
        })
        if result:
            result.sort(key=lambda m: m.get("id", "0"))
        return result or []

    async def get_single_message(self, channel_id: str, message_id: str) -> Optional[dict]:
        """Get a single message by ID."""
        result = await self._request("GET", f"/channels/{channel_id}/messages", params={
            "around": message_id,
            "limit": "1",
        })
        if result:
            for msg in result:
                if msg.get("id") == message_id:
                    return msg
            return result[0] if result else None
        return None

    # ── Pins ──

    async def get_pins(self, channel_id: str) -> list[dict]:
        """Get pinned messages in a channel."""
        result = await self._request("GET", f"/channels/{channel_id}/pins")
        return result or []

    # ── Threads ──

    async def get_threads(self, channel_id: str, include_archived: bool = False) -> list[dict]:
        """Get threads in a channel."""
        threads = []

        offset = 0
        while True:
            params: dict[str, Any] = {
                "archived": "false",
                "sort_by": "last_message_time",
                "sort_order": "desc",
                "limit": "25",
                "offset": str(offset),
            }
            result = await self._request("GET", f"/channels/{channel_id}/threads/search", params=params)
            if not result or not result.get("threads"):
                break
            threads.extend(result["threads"])
            if not result.get("has_more", False):
                break
            offset += 25

        if include_archived:
            offset = 0
            while True:
                params = {
                    "archived": "true",
                    "sort_by": "last_message_time",
                    "sort_order": "desc",
                    "limit": "25",
                    "offset": str(offset),
                }
                result = await self._request("GET", f"/channels/{channel_id}/threads/search", params=params)
                if not result or not result.get("threads"):
                    break
                threads.extend(result["threads"])
                if not result.get("has_more", False):
                    break
                offset += 25

        return threads

    # ── Search ──

    async def search_guild(self, guild_id: str, content: Optional[str] = None,
                           author_id: Optional[str] = None, channel_id: Optional[str] = None,
                           min_id: Optional[str] = None, max_id: Optional[str] = None,
                           has: Optional[str] = None, sort_by: str = "timestamp",
                           sort_order: str = "desc", max_results: int = 25,
                           include_nsfw: bool = True) -> list[dict]:
        """Search messages across a guild."""
        params: dict[str, str] = {}
        if content:
            params["content"] = content
        if author_id:
            params["author_id"] = author_id
        if channel_id:
            params["channel_id"] = channel_id
        if min_id:
            params["min_id"] = min_id
        if max_id:
            params["max_id"] = max_id
        if has:
            params["has"] = has
        if include_nsfw:
            params["include_nsfw"] = "true"
        params["sort_by"] = sort_by
        params["sort_order"] = sort_order

        all_messages = []
        offset = 0

        while len(all_messages) < max_results:
            params["offset"] = str(offset)
            result = await self._request("GET", f"/guilds/{guild_id}/messages/search", params=params)
            if not result:
                break

            messages = result.get("messages", [])
            total_results = result.get("total_results", 0)

            if not messages:
                break

            for msg_group in messages:
                if msg_group:
                    all_messages.append(msg_group[0] if isinstance(msg_group, list) else msg_group)

            if len(all_messages) >= total_results or len(all_messages) >= max_results:
                break

            offset += 25
            await asyncio.sleep(2.0)

        return all_messages[:max_results]

    # ── Reply Chain ──

    async def follow_reply_chain(self, channel_id: str, message_id: str,
                                  depth: int = 5) -> list[dict]:
        """Follow a reply chain upward and collect the thread."""
        chain = []
        visited = set()
        current_id = message_id

        for _ in range(depth):
            if current_id in visited:
                break
            visited.add(current_id)

            msg = await self.get_single_message(channel_id, current_id)
            if not msg:
                break

            chain.insert(0, msg)

            ref = msg.get("message_reference")
            if ref and ref.get("message_id"):
                current_id = ref["message_id"]
                if ref.get("channel_id") and ref["channel_id"] != channel_id:
                    print_error(f"  [Reply Chain] Cross-channel reply to {ref['channel_id']}, stopping")
                    break
            else:
                break

        if message_id not in visited:
            msg = await self.get_single_message(channel_id, message_id)
            if msg:
                chain.append(msg)

        chain.sort(key=lambda m: m.get("id", "0"))

        seen = set()
        unique_chain = []
        for msg in chain:
            mid = msg.get("id")
            if mid not in seen:
                seen.add(mid)
                unique_chain.append(msg)

        return unique_chain
