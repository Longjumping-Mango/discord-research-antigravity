"""
Discord Research Tool — Utility Functions
Snowflake/date conversion, message formatting, output helpers.
"""

import json
import sys
from datetime import datetime, timezone
from typing import Any, Optional

# Discord epoch: January 1, 2015 00:00:00 UTC (in milliseconds)
DISCORD_EPOCH = 1420070400000


def date_to_snowflake(dt: datetime) -> str:
    """Convert a datetime to a Discord snowflake ID."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    timestamp_ms = int(dt.timestamp() * 1000)
    snowflake = (timestamp_ms - DISCORD_EPOCH) << 22
    return str(snowflake)


def snowflake_to_datetime(snowflake: str | int) -> datetime:
    """Convert a Discord snowflake ID to a datetime."""
    snowflake_int = int(snowflake)
    timestamp_ms = (snowflake_int >> 22) + DISCORD_EPOCH
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def parse_date_arg(date_str: str) -> datetime:
    """Parse a date string in YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")


def format_timestamp(iso_timestamp: str) -> str:
    """Format an ISO timestamp to a readable format."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return iso_timestamp or "unknown"


def format_message_text(msg: dict) -> str:
    """Format a single message for text output."""
    timestamp = format_timestamp(msg.get("timestamp", ""))
    author = msg.get("author", {})
    author_name = author.get("global_name") or author.get("username", "Unknown")
    author_id = author.get("id", "?")
    content = msg.get("content", "")

    lines = [f"[{timestamp}] @{author_name} (ID: {author_id}):"]

    if content:
        # Indent content lines
        for line in content.split("\n"):
            lines.append(f"  {line}")
    else:
        lines.append("  [no text content]")

    # Attachments
    attachments = msg.get("attachments", [])
    for att in attachments:
        filename = att.get("filename", "file")
        size = att.get("size", 0)
        size_str = _format_size(size)
        url = att.get("url", "")
        lines.append(f"  📎 {filename} ({size_str})")
        if url:
            lines.append(f"     {url}")

    # Embeds
    embeds = msg.get("embeds", [])
    for embed in embeds:
        title = embed.get("title", "")
        url = embed.get("url", "")
        description = embed.get("description", "")
        if title:
            lines.append(f"  📦 Embed: {title}")
        if url:
            lines.append(f"     {url}")
        if description:
            # Truncate long descriptions
            desc_short = description[:200] + "..." if len(description) > 200 else description
            lines.append(f"     {desc_short}")

    # Reply reference
    ref = msg.get("referenced_message")
    if ref:
        ref_author = ref.get("author", {}).get("username", "?")
        ref_content = ref.get("content", "")
        ref_short = ref_content[:100] + "..." if len(ref_content) > 100 else ref_content
        lines.append(f"  ↩️ Reply to @{ref_author}: \"{ref_short}\"")
    elif msg.get("message_reference"):
        ref_data = msg["message_reference"]
        ref_msg_id = ref_data.get("message_id", "?")
        lines.append(f"  ↩️ Reply to message {ref_msg_id}")

    # Reactions
    reactions = msg.get("reactions", [])
    if reactions:
        reaction_strs = []
        for r in reactions:
            emoji = r.get("emoji", {})
            name = emoji.get("name", "?")
            count = r.get("count", 0)
            reaction_strs.append(f"{name}×{count}")
        lines.append(f"  🔄 Reactions: {' '.join(reaction_strs)}")

    # Pinned indicator
    if msg.get("pinned"):
        lines.append("  📌 Pinned")

    return "\n".join(lines)


def format_message_json(msg: dict) -> dict:
    """Format a message for JSON output (flat structure)."""
    author = msg.get("author", {})
    ref = msg.get("referenced_message")

    result = {
        "id": msg.get("id"),
        "channel_id": msg.get("channel_id"),
        "timestamp": msg.get("timestamp"),
        "author_id": author.get("id"),
        "author_name": author.get("global_name") or author.get("username"),
        "content": msg.get("content", ""),
        "attachment_count": len(msg.get("attachments", [])),
        "embed_count": len(msg.get("embeds", [])),
        "pinned": msg.get("pinned", False),
        "is_reply": msg.get("type") == 19 or msg.get("message_reference") is not None,
    }

    # Attachments
    attachments = msg.get("attachments", [])
    if attachments:
        result["attachments"] = [
            {"filename": a.get("filename"), "url": a.get("url"), "size": a.get("size")}
            for a in attachments
        ]

    # Links from embeds
    embeds = msg.get("embeds", [])
    if embeds:
        result["embed_urls"] = [e.get("url") for e in embeds if e.get("url")]

    # Reply info
    if ref:
        result["reply_to_author"] = ref.get("author", {}).get("username")
        result["reply_to_content_preview"] = (ref.get("content", ""))[:150]
        result["reply_to_id"] = ref.get("id")
    elif msg.get("message_reference"):
        result["reply_to_id"] = msg["message_reference"].get("message_id")

    return result


def format_messages_block(messages: list[dict], title: str, cache_from: int = 0,
                          fresh_count: int = 0, json_mode: bool = False) -> str:
    """Format a block of messages with header and footer."""
    if json_mode:
        output_lines = []
        for msg in messages:
            output_lines.append(json.dumps(format_message_json(msg), ensure_ascii=False))
        return "\n".join(output_lines)

    lines = [f"=== {title} ===", ""]
    for msg in messages:
        lines.append(format_message_text(msg))
        lines.append("")

    total = len(messages)
    lines.append(f"=== End ({total} messages, {cache_from} from cache, {fresh_count} fresh) ===")
    return "\n".join(lines)


def format_channels_block(channels: list[dict], guild_name: str = "",
                          json_mode: bool = False) -> str:
    """Format channel listing."""
    if json_mode:
        return "\n".join(json.dumps(ch, ensure_ascii=False) for ch in channels)

    # Group by category
    categories: dict[Optional[str], list[dict]] = {}
    category_names: dict[str, str] = {}

    # First pass: identify categories
    for ch in channels:
        if ch.get("type") == 4:  # Category
            category_names[ch["id"]] = ch.get("name", "Unknown Category")

    # Second pass: group channels
    for ch in channels:
        if ch.get("type") == 4:
            continue
        parent_id = ch.get("parent_id")
        cat_name = category_names.get(parent_id, "No Category") if parent_id else "No Category"
        if cat_name not in categories:
            categories[cat_name] = []
        categories[cat_name].append(ch)

    lines = [f"=== Channels in {guild_name} ===", ""]
    type_icons = {0: "#", 2: "🔊", 5: "📢", 15: "💬", 11: "🧵", 12: "🧵"}

    for cat_name, cat_channels in sorted(categories.items()):
        lines.append(f"📁 {cat_name.upper()}")
        for ch in sorted(cat_channels, key=lambda c: c.get("position", 0)):
            ch_type = ch.get("type", 0)
            icon = type_icons.get(ch_type, "#")
            name = ch.get("name", "unknown")
            ch_id = ch.get("id", "?")
            topic = ch.get("topic", "")
            topic_str = f" — {topic[:80]}..." if topic and len(topic) > 80 else (f" — {topic}" if topic else "")
            lines.append(f"  {icon} {name} (ID: {ch_id}){topic_str}")
        lines.append("")

    return "\n".join(lines)


def format_guilds_block(guilds: list[dict], json_mode: bool = False) -> str:
    """Format guild listing."""
    if json_mode:
        return "\n".join(json.dumps(g, ensure_ascii=False) for g in guilds)

    lines = [f"=== Discord Servers ({len(guilds)}) ===", ""]
    for g in guilds:
        name = g.get("name", "Unknown")
        gid = g.get("id", "?")
        lines.append(f"  🏠 {name} (ID: {gid})")
    lines.append("")
    lines.append("=== End ===")
    return "\n".join(lines)


def extract_links_from_messages(messages: list[dict]) -> list[dict]:
    """Extract all URLs from a list of messages."""
    import re
    url_pattern = re.compile(r'https?://[^\s<>"\')\]]+')
    results = []

    for msg in messages:
        msg_links = set()
        # From content
        content = msg.get("content", "")
        msg_links.update(url_pattern.findall(content))

        # From embeds
        for embed in msg.get("embeds", []):
            if embed.get("url"):
                msg_links.add(embed["url"])

        # From attachments
        for att in msg.get("attachments", []):
            if att.get("url"):
                msg_links.add(att["url"])

        if msg_links:
            author = msg.get("author", {})
            results.append({
                "message_id": msg.get("id"),
                "timestamp": format_timestamp(msg.get("timestamp", "")),
                "author": author.get("global_name") or author.get("username", "?"),
                "channel_id": msg.get("channel_id"),
                "links": sorted(msg_links),
            })

    return results


def print_output(text: str):
    """Print output to stdout."""
    print(text)


def print_error(text: str):
    """Print error to stderr."""
    print(text, file=sys.stderr)


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
