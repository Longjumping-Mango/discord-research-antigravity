"""
Discord Research Tool — CLI Entry Point
10 subcommands for browsing, searching, and analyzing Discord messages.
Usage: python discord_cli.py <command> [options]
"""

import argparse
import asyncio
import json
import sys
import os

# Ensure the script's directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from discord_client import DiscordClient, set_token
from cache import (
    get_cached_guilds, cache_guilds,
    get_cached_channels, cache_channels,
    get_cached_messages, cache_messages,
    get_cached_search, cache_search,
    get_cache_stats,
)
from utils import (
    date_to_snowflake, parse_date_arg,
    format_messages_block, format_channels_block, format_guilds_block,
    format_message_text, format_message_json,
    extract_links_from_messages,
    print_output, print_error,
)


async def cmd_user_info(args):
    """Validate token and show current user."""
    client = DiscordClient()
    try:
        user = await client.get_current_user()
        if not user:
            print_error("ERROR: Could not authenticate. Check your token.")
            sys.exit(1)

        if args.json:
            print_output(json.dumps(user, ensure_ascii=False))
        else:
            username = user.get("global_name") or user.get("username", "?")
            user_id = user.get("id", "?")
            discriminator = user.get("discriminator", "0")
            print_output("=== Discord User Info ===")
            print_output(f"  Username: {username}")
            print_output(f"  ID: {user_id}")
            print_output(f"  Discriminator: #{discriminator}")
            print_output("  Token: Valid ✅")

            stats = get_cache_stats()
            if stats.get("exists"):
                print_output("\n=== Cache Stats ===")
                print_output(f"  Messages cached: {stats['messages_cached']}")
                print_output(f"  Channels tracked: {stats['channels_tracked']}")
                print_output(f"  Search queries cached: {stats['search_queries_cached']}")
                print_output(f"  DB size: {stats['db_size_bytes'] / 1024:.1f} KB")
    finally:
        await client.close()


async def cmd_list_servers(args):
    """List all Discord servers."""
    # Check cache first
    cached = get_cached_guilds()
    if cached:
        print_error("  [Cache] Using cached guild list")
        print_output(format_guilds_block(cached, json_mode=args.json))
        return

    client = DiscordClient()
    try:
        guilds = await client.get_guilds()
        if not guilds:
            print_output("No servers found.")
            return
        cache_guilds(guilds)
        print_output(format_guilds_block(guilds, json_mode=args.json))
    finally:
        await client.close()


async def cmd_list_channels(args):
    """List channels in a server."""
    server_id = args.server

    # Check cache
    cached = get_cached_channels(server_id)
    if cached:
        print_error("  [Cache] Using cached channel list")
        print_output(format_channels_block(cached, guild_name=f"Server {server_id}", json_mode=args.json))
        return

    client = DiscordClient()
    try:
        channels = await client.get_guild_channels(server_id)
        if not channels:
            print_output(f"No channels found in server {server_id}.")
            return
        cache_channels(server_id, channels)

        # Get guild name
        guilds = get_cached_guilds()
        guild_name = server_id
        if guilds:
            for g in guilds:
                if g.get("id") == server_id:
                    guild_name = g.get("name", server_id)
                    break

        print_output(format_channels_block(channels, guild_name=guild_name, json_mode=args.json))
    finally:
        await client.close()


async def cmd_get_messages(args):
    """Fetch messages from a channel."""
    channel_id = args.channel
    limit = args.limit

    client = DiscordClient()
    try:
        # Check cache and freshness
        cached_msgs, latest_cached_id = get_cached_messages(channel_id, limit)
        cache_from = 0
        fresh_count = 0
        all_messages = []

        if cached_msgs and latest_cached_id:
            # Check for new messages since cached
            new_msgs = await client.get_messages(channel_id, limit=limit, after=latest_cached_id)
            if new_msgs:
                cache_messages(channel_id, new_msgs)
                fresh_count = len(new_msgs)

            # Combine: use fresh + cached
            all_messages = cached_msgs + new_msgs
            cache_from = len(cached_msgs)
            # Trim to requested limit, keeping newest
            if len(all_messages) > limit:
                all_messages = all_messages[-limit:]
        else:
            # No cache, fetch fresh
            before_id = args.before if hasattr(args, 'before') and args.before else None
            after_id = args.after if hasattr(args, 'after') and args.after else None
            all_messages = await client.get_messages(channel_id, limit=limit,
                                                      before=before_id, after=after_id)
            fresh_count = len(all_messages)
            if all_messages:
                cache_messages(channel_id, all_messages)

        print_output(format_messages_block(
            all_messages,
            title=f"Messages in channel {channel_id}",
            cache_from=cache_from,
            fresh_count=fresh_count,
            json_mode=args.json,
        ))
    finally:
        await client.close()


async def cmd_search(args):
    """Search messages in a server (with optional channel filter)."""
    query = args.query
    server_id = args.server
    channel_id = getattr(args, 'channel', None)
    max_results = args.max_results

    # Convert date args to snowflake IDs
    min_id = None
    max_id = None
    if args.after_date:
        min_id = date_to_snowflake(parse_date_arg(args.after_date))
    if args.before_date:
        max_id = date_to_snowflake(parse_date_arg(args.before_date))

    # Build filter dict for cache key
    filters = {
        "has": args.has, "author": args.author,
        "sort": args.sort, "max_results": max_results,
        "after": args.after_date, "before": args.before_date,
    }

    # Check search cache
    cached = get_cached_search(
        guild_id=server_id or "",
        channel_id=channel_id or "",
        query=query,
        **filters
    )
    if cached:
        print_error(f"  [Cache] Using cached search results for '{query}'")
        print_output(format_messages_block(
            cached,
            title=f"Search Results for \"{query}\" (cached)",
            cache_from=len(cached),
            fresh_count=0,
            json_mode=args.json,
        ))
        return

    if not server_id:
        print_error("ERROR: --server is required for search")
        sys.exit(1)

    client = DiscordClient()
    try:
        results = await client.search_guild(
            guild_id=server_id,
            content=query,
            channel_id=channel_id,
            author_id=args.author,
            min_id=min_id,
            max_id=max_id,
            has=args.has,
            sort_by=args.sort,
            max_results=max_results,
        )

        if results:
            cache_search(
                guild_id=server_id or "",
                channel_id=channel_id or "",
                query=query,
                results=results,
                **filters
            )

        title = f"Search Results for \"{query}\""
        if server_id:
            title += f" in server {server_id}"
        if channel_id:
            title += f" in channel {channel_id}"

        print_output(format_messages_block(
            results,
            title=title,
            cache_from=0,
            fresh_count=len(results),
            json_mode=args.json,
        ))
    finally:
        await client.close()


async def cmd_get_context(args):
    """Get messages around a specific message."""
    client = DiscordClient()
    try:
        messages = await client.get_messages_around(args.channel, args.message, args.size)
        print_output(format_messages_block(
            messages,
            title=f"Context around message {args.message} in channel {args.channel}",
            fresh_count=len(messages),
            json_mode=args.json,
        ))
    finally:
        await client.close()


async def cmd_follow_replies(args):
    """Follow a reply chain."""
    client = DiscordClient()
    try:
        chain = await client.follow_reply_chain(args.channel, args.message, args.depth)
        print_output(format_messages_block(
            chain,
            title=f"Reply chain for message {args.message} ({len(chain)} messages, depth={args.depth})",
            fresh_count=len(chain),
            json_mode=args.json,
        ))
    finally:
        await client.close()


async def cmd_get_pins(args):
    """Get pinned messages in a channel."""
    client = DiscordClient()
    try:
        pins = await client.get_pins(args.channel)
        print_output(format_messages_block(
            pins,
            title=f"Pinned messages in channel {args.channel}",
            fresh_count=len(pins),
            json_mode=args.json,
        ))
    finally:
        await client.close()


async def cmd_get_threads(args):
    """List threads in a channel."""
    client = DiscordClient()
    try:
        threads = await client.get_threads(args.channel, include_archived=args.include_archived)
        if args.json:
            for t in threads:
                print_output(json.dumps(t, ensure_ascii=False))
        else:
            print_output(f"=== Threads in channel {args.channel} ({len(threads)} found) ===\n")
            for t in threads:
                name = t.get("name", "Unnamed")
                tid = t.get("id", "?")
                msg_count = t.get("message_count", "?")
                archived = "📁 archived" if t.get("thread_metadata", {}).get("archived") else "🟢 active"
                print_output(f"  🧵 {name} (ID: {tid}) — {msg_count} messages — {archived}")
            print_output("\n=== End ===")
    finally:
        await client.close()


async def cmd_extract_links(args):
    """Extract all URLs from messages in a channel."""
    client = DiscordClient()
    try:
        messages = await client.get_messages(args.channel, limit=args.limit)
        links = extract_links_from_messages(messages)

        if args.json:
            for l in links:
                print_output(json.dumps(l, ensure_ascii=False))
        else:
            total_links = sum(len(l["links"]) for l in links)
            print_output(f"=== Links from channel {args.channel} ({total_links} links from {len(links)} messages) ===\n")
            for entry in links:
                print_output(f"[{entry['timestamp']}] @{entry['author']}:")
                for url in entry["links"]:
                    print_output(f"  🔗 {url}")
                print_output("")
            print_output("=== End ===")
    finally:
        await client.close()


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="discord_cli",
        description="Discord Research Tool — Browse, search, and analyze Discord messages",
    )

    # Global --token flag
    parser.add_argument("--token", default=None,
                        help="Discord user token (overrides DISCORD_USER_TOKEN env var)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # user-info
    p = subparsers.add_parser("user-info", help="Validate token and show user info")
    p.add_argument("--json", action="store_true", help="Output in JSON format")

    # list-servers
    p = subparsers.add_parser("list-servers", help="List all Discord servers")
    p.add_argument("--json", action="store_true")

    # list-channels
    p = subparsers.add_parser("list-channels", help="List channels in a server")
    p.add_argument("--server", required=True, help="Server (guild) ID")
    p.add_argument("--json", action="store_true")

    # get-messages
    p = subparsers.add_parser("get-messages", help="Fetch messages from a channel")
    p.add_argument("--channel", required=True, help="Channel ID")
    p.add_argument("--limit", type=int, default=50, help="Max messages to fetch (default: 50)")
    p.add_argument("--before", default=None, help="Fetch messages before this message ID")
    p.add_argument("--after", default=None, help="Fetch messages after this message ID")
    p.add_argument("--json", action="store_true")

    # search
    p = subparsers.add_parser("search", help="Search messages by keyword")
    p.add_argument("--server", required=True, help="Server (guild) ID")
    p.add_argument("--channel", default=None, help="Channel ID (optional, narrows search)")
    p.add_argument("--query", required=True, help="Search query")
    p.add_argument("--author", default=None, help="Filter by author ID")
    p.add_argument("--before-date", default=None, help="Messages before date (YYYY-MM-DD)")
    p.add_argument("--after-date", default=None, help="Messages after date (YYYY-MM-DD)")
    p.add_argument("--has", default=None, choices=["link", "embed", "file", "image", "video", "sound", "sticker"],
                   help="Filter by content type")
    p.add_argument("--sort", default="timestamp", choices=["timestamp", "relevance"],
                   help="Sort results by (default: timestamp)")
    p.add_argument("--max-results", type=int, default=25, help="Max results (default: 25)")
    p.add_argument("--json", action="store_true")

    # get-context
    p = subparsers.add_parser("get-context", help="Get messages around a specific message")
    p.add_argument("--channel", required=True, help="Channel ID")
    p.add_argument("--message", required=True, help="Message ID")
    p.add_argument("--size", type=int, default=25, help="Number of surrounding messages (default: 25)")
    p.add_argument("--json", action="store_true")

    # follow-replies
    p = subparsers.add_parser("follow-replies", help="Follow a reply chain")
    p.add_argument("--channel", required=True, help="Channel ID")
    p.add_argument("--message", required=True, help="Message ID to start from")
    p.add_argument("--depth", type=int, default=5, help="Max depth to follow (default: 5)")
    p.add_argument("--json", action="store_true")

    # get-pins
    p = subparsers.add_parser("get-pins", help="Get pinned messages in a channel")
    p.add_argument("--channel", required=True, help="Channel ID")
    p.add_argument("--json", action="store_true")

    # get-threads
    p = subparsers.add_parser("get-threads", help="List threads in a channel")
    p.add_argument("--channel", required=True, help="Channel ID")
    p.add_argument("--include-archived", action="store_true", help="Include archived threads")
    p.add_argument("--json", action="store_true")

    # extract-links
    p = subparsers.add_parser("extract-links", help="Extract URLs from messages")
    p.add_argument("--channel", required=True, help="Channel ID")
    p.add_argument("--limit", type=int, default=100, help="Max messages to scan (default: 100)")
    p.add_argument("--json", action="store_true")

    return parser


COMMAND_MAP = {
    "user-info": cmd_user_info,
    "list-servers": cmd_list_servers,
    "list-channels": cmd_list_channels,
    "get-messages": cmd_get_messages,
    "search": cmd_search,
    "get-context": cmd_get_context,
    "follow-replies": cmd_follow_replies,
    "get-pins": cmd_get_pins,
    "get-threads": cmd_get_threads,
    "extract-links": cmd_extract_links,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Apply --token override if provided
    if args.token:
        set_token(args.token)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handler = COMMAND_MAP.get(args.command)
    if not handler:
        print_error(f"Unknown command: {args.command}")
        sys.exit(1)

    try:
        asyncio.run(handler(args))
    except KeyboardInterrupt:
        print_error("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        print_error(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
