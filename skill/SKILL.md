---
name: discord-research
description: Search, browse, and analyze Discord messages to find information in Discord communities using a Python CLI tool.
---

# Discord Research Skill

## Purpose

Give the agent the ability to search and analyze Discord messages across any server the user is a member of. This skill provides **read-only** access to Discord through 10 CLI commands.

## Triggers

Activate this skill when the user mentions: discord, server, channel, community chat, discord messages, discord search, or wants to find information from Discord communities.

## CLI Location

```
python <INSTALL_DIR>/src/discord_cli.py <command> [options]
```

> **IMPORTANT**: Replace `<INSTALL_DIR>` with the actual path where the repository was cloned. For example: `~/.gemini/antigravity/mcp_servers/discord-research`

## Commands Reference

### 1. `user-info` — Validate token

```bash
python <INSTALL_DIR>/src/discord_cli.py user-info
```

### 2. `list-servers` — List all servers

```bash
python <INSTALL_DIR>/src/discord_cli.py list-servers
```

### 3. `list-channels` — List channels in a server

```bash
python <INSTALL_DIR>/src/discord_cli.py list-channels --server <SERVER_ID>
```

### 4. `get-messages` — Fetch messages

```bash
python <INSTALL_DIR>/src/discord_cli.py get-messages --channel <CHANNEL_ID> --limit 50
```

### 5. `search` — Search messages by keyword

```bash
python <INSTALL_DIR>/src/discord_cli.py search --server <SERVER_ID> --query "keyword"
python <INSTALL_DIR>/src/discord_cli.py search --server <SERVER_ID> --channel <CHANNEL_ID> --query "keyword"
python <INSTALL_DIR>/src/discord_cli.py search --server <SERVER_ID> --query "keyword" --has link --after-date 2024-01-01
```

Options: `--server` (required), `--channel`, `--query`, `--author <USER_ID>`, `--before-date YYYY-MM-DD`, `--after-date YYYY-MM-DD`, `--has [link|embed|file|image|video|sound|sticker]`, `--sort [timestamp|relevance]`, `--max-results N`.

### 6. `get-context` — Get surrounding messages

```bash
python <INSTALL_DIR>/src/discord_cli.py get-context --channel <CHANNEL_ID> --message <MSG_ID> --size 10
```

### 7. `follow-replies` — Trace a reply chain

```bash
python <INSTALL_DIR>/src/discord_cli.py follow-replies --channel <CHANNEL_ID> --message <MSG_ID> --depth 5
```

### 8. `get-pins` — Get pinned messages

```bash
python <INSTALL_DIR>/src/discord_cli.py get-pins --channel <CHANNEL_ID>
```

### 9. `get-threads` — List threads

```bash
python <INSTALL_DIR>/src/discord_cli.py get-threads --channel <CHANNEL_ID> --include-archived
```

### 10. `extract-links` — Extract URLs

```bash
python <INSTALL_DIR>/src/discord_cli.py extract-links --channel <CHANNEL_ID> --limit 100
```

All commands support `--json` for machine-readable output.

---

## Deep Research Protocol

When conducting deep research on a Discord topic, follow this strategy:

### Phase 1: Semantic Channel Selection

1. Run `list-servers` to identify relevant servers.
2. Run `list-channels --server <ID>` for each relevant server.
3. **Analyze channel names and topics semantically** — rank them by likely relevance to the research query. Don't just match keywords; consider synonyms, related concepts, and typical Discord naming conventions (e.g., `#help` for support questions, `#general` for broad discussions, `#dev` or `#development` for technical topics).

### Phase 2: Iterative Keyword Search

1. Generate at **minimum 5 keyword variants** of the user's query:
   - Exact phrase
   - Synonyms
   - Abbreviations / acronyms
   - Related technical terms
   - Common misspellings
2. Search each keyword variant in the most relevant channels/servers.
3. **Expand keywords from results** — if search results contain new relevant terms not in your initial set, add them and search again.
4. **Stop at 70% saturation** — when new searches produce mostly previously-seen results.

### Phase 3: Deep Investigation

For the most relevant messages found:

1. **Get context**: Use `get-context` to read surrounding conversation.
2. **Follow replies**: Use `follow-replies` to trace full conversations.
3. **Check pins**: Use `get-pins` on relevant channels for curated information.
4. **Check threads**: Use `get-threads` for in-depth discussions.
5. **Extract links**: Use `extract-links` for referenced URLs and resources.

### Phase 4: Cross-Reference

- Validate Discord findings with `search_web` or `read_url_content`.
- Check referenced GitHub repos with `mcp_github_*` tools.
- Compare information across multiple Discord sources for accuracy.

## Temporal Rules

- Prioritize **recent messages** (last 6 months) for rapidly-evolving topics.
- Use `--after-date` and `--before-date` to narrow searches to relevant time periods.
- If information seems outdated, note it explicitly in your response.

## Cache Behavior

- Guilds and channels cache for **1 hour**.
- Search results cache for **15 minutes**.
- Messages use **freshness logic** — cached messages are supplemented with new ones on subsequent calls.

## Error Handling

- **401/403**: Token is invalid or expired. Tell the user to update their `DISCORD_USER_TOKEN`.
- **429**: Rate limited. The CLI automatically retries with backoff — just wait.
- **Empty results**: Try different keywords, check channel permissions, or broaden the search.

## Anti-Patterns to Avoid

- ❌ Do NOT search all 25 servers at once — be selective.
- ❌ Do NOT use only one keyword — always generate 5+ variants.
- ❌ Do NOT ignore channel names — semantic pre-selection is critical.
- ❌ Do NOT skip `get-context` — isolated messages often lack meaning without context.
- ❌ Do NOT present raw search results — always synthesize and summarize findings.
