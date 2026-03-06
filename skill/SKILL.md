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

### Output to File (Windows Encoding Safety)

On Windows, **ALWAYS** prefer `--output-file` over PowerShell `>` redirection to avoid UTF-16LE encoding corruption:

```bash
# ✅ CORRECT — Python writes UTF-8 directly to file
python <INSTALL_DIR>/src/discord_cli.py --output-file results.txt search --server <ID> --query "test"

# ❌ WRONG — PowerShell converts to UTF-16LE, breaks view_file and text tools
python <INSTALL_DIR>/src/discord_cli.py search --server <ID> --query "test" > results.txt
```

**Note:** `--output-file` is a global flag that goes BEFORE the subcommand. It works with any command.
After writing, read the file with `view_file` or `mcp_filesystem_read_text_file`.

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

### Semantic Expansion Protocol (MANDATORY for all technical searches)

When searching for ANY technical topic (software versions, hardware models, firmware, libraries, tools, configurations, error codes), apply these 4 layers IN ORDER:

**Layer 1 — Exact Match:**
Search the literal terms provided by the user.
Example: `"KWCN54WW"`, `"FFmpeg 7.0"`, `"RTX 4080 undervolt"`

**Layer 2 — Contextual Abstraction:**
Abstract specific identifiers to broader semantic categories:
- Version numbers → temporal: `"latest"`, `"newest"`, `"recent update"`, month/year
- Version numbers → generational: `"gen 8"`, `"13th gen"`, `"Raptor Lake"`
- Model numbers → product names: `"legion pro 7"`, `"RTX 4080"`
- Feature names → functional: `"advanced bios"`, `"undervolt"`, `"unlock"`
- Error codes → symptoms: `"boot loop"`, `"crash"`, `"won't start"`
- Library versions → release names: `"stable"`, `"nightly"`, `"LTS"`

**Layer 3 — Community Jargon Expansion:**
Discord communities use informal language. Expand with:
- Abbreviations: `"UV"` for undervolt, `"OC"` for overclock, `"XMP"`
- Slang: `"bricked"`, `"modded bios"`, `"tweaked"`
- Tool/project names: `"ThrottleStop"`, `"SREP"`, `"HWiNFO"`
- People: known community experts (discovered from results)

**Layer 4 — Temporal + Iterative:**
- Re-run Layer 2-3 keywords with `--after-date` (last 3-6 months)
- Read returned results → extract NEW terms from message content
- Search with newly discovered terms
- STOP at 70% saturation (mostly repeated results)

**CRITICAL RULES:**
- ❌ NEVER declare "nothing found" after only Layer 1
- ❌ NEVER skip Layers 2-4 for technical topics
- ✅ ALWAYS attempt at least Layers 1+2 before reporting
- ✅ If Layer 1 returns 0 results, Layers 2-4 are MANDATORY
- ✅ Apply to ALL search tools (Discord, web, GitHub), not just Discord

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
