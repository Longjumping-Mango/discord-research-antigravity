# Command Reference

All commands support `--json` flag for machine-readable JSON Lines output.

## Global Options

| Flag              | Description                                     |
| ----------------- | ----------------------------------------------- |
| `--token <TOKEN>` | Override Discord token (alternative to env var) |

---

## 1. `user-info` — Validate Token

Checks if your token is valid and displays basic user info.

```bash
python src/discord_cli.py user-info
python src/discord_cli.py user-info --json
```

---

## 2. `list-servers` — List Servers

Lists all Discord servers you are a member of.

```bash
python src/discord_cli.py list-servers
python src/discord_cli.py list-servers --json
```

**Output:**

```
=== Discord Servers (25) ===
  🏠 My Server (ID: 123456789012345678)
  🏠 Another Server (ID: 987654321098765432)
```

---

## 3. `list-channels` — List Channels

Lists all channels in a server, grouped by category.

```bash
python src/discord_cli.py list-channels --server 123456789012345678
```

| Option     | Required | Description       |
| ---------- | -------- | ----------------- |
| `--server` | ✅       | Server (guild) ID |

---

## 4. `get-messages` — Fetch Messages

Fetches recent messages from a channel.

```bash
python src/discord_cli.py get-messages --channel 123456789012345678
python src/discord_cli.py get-messages --channel 123456789012345678 --limit 10 --json
python src/discord_cli.py get-messages --channel 123456789012345678 --after 1234567890123456
```

| Option      | Required | Default | Description                           |
| ----------- | -------- | ------- | ------------------------------------- |
| `--channel` | ✅       | —       | Channel ID                            |
| `--limit`   | ❌       | 50      | Max messages to fetch                 |
| `--before`  | ❌       | —       | Fetch messages before this message ID |
| `--after`   | ❌       | —       | Fetch messages after this message ID  |

---

## 5. `search` — Search Messages

Searches messages across a server with keyword and filters. Uses Discord's built-in search API.

```bash
# Basic search
python src/discord_cli.py search --server 123456 --query "transformer architecture"

# Search within a specific channel
python src/discord_cli.py search --server 123456 --channel 789012 --query "release notes"

# Search with filters
python src/discord_cli.py search --server 123456 --query "bug" --after-date 2024-01-01 --has link

# Search with relevance sorting
python src/discord_cli.py search --server 123456 --query "encoder" --sort relevance --max-results 50
```

| Option          | Required | Default   | Description                                                |
| --------------- | -------- | --------- | ---------------------------------------------------------- |
| `--server`      | ✅       | —         | Server (guild) ID                                          |
| `--channel`     | ❌       | —         | Narrow search to a specific channel                        |
| `--query`       | ✅       | —         | Search keyword or phrase                                   |
| `--author`      | ❌       | —         | Filter by author user ID                                   |
| `--before-date` | ❌       | —         | Messages before date (YYYY-MM-DD)                          |
| `--after-date`  | ❌       | —         | Messages after date (YYYY-MM-DD)                           |
| `--has`         | ❌       | —         | Filter by: link, embed, file, image, video, sound, sticker |
| `--sort`        | ❌       | timestamp | Sort by: timestamp or relevance                            |
| `--max-results` | ❌       | 25        | Maximum results to return                                  |

---

## 6. `get-context` — Surrounding Messages

Gets messages around a specific message to see the full conversation context.

```bash
python src/discord_cli.py get-context --channel 123456 --message 789012 --size 10
```

| Option      | Required | Default | Description                    |
| ----------- | -------- | ------- | ------------------------------ |
| `--channel` | ✅       | —       | Channel ID                     |
| `--message` | ✅       | —       | Center message ID              |
| `--size`    | ❌       | 25      | Number of surrounding messages |

---

## 7. `follow-replies` — Reply Chain

Follows a reply chain upward to find the original message and full thread.

```bash
python src/discord_cli.py follow-replies --channel 123456 --message 789012 --depth 5
```

| Option      | Required | Default | Description             |
| ----------- | -------- | ------- | ----------------------- |
| `--channel` | ✅       | —       | Channel ID              |
| `--message` | ✅       | —       | Starting message ID     |
| `--depth`   | ❌       | 5       | Maximum depth to follow |

---

## 8. `get-pins` — Pinned Messages

Gets all pinned messages in a channel. Pinned messages often contain the most important information.

```bash
python src/discord_cli.py get-pins --channel 123456789012345678
```

---

## 9. `get-threads` — List Threads

Lists active (and optionally archived) threads in a channel.

```bash
python src/discord_cli.py get-threads --channel 123456
python src/discord_cli.py get-threads --channel 123456 --include-archived
```

| Option               | Required | Default | Description              |
| -------------------- | -------- | ------- | ------------------------ |
| `--channel`          | ✅       | —       | Channel ID               |
| `--include-archived` | ❌       | false   | Include archived threads |

---

## 10. `extract-links` — Extract URLs

Extracts all URLs from messages in a channel. Useful for finding resources shared in discussions.

```bash
python src/discord_cli.py extract-links --channel 123456 --limit 200
```

| Option      | Required | Default | Description                    |
| ----------- | -------- | ------- | ------------------------------ |
| `--channel` | ✅       | —       | Channel ID                     |
| `--limit`   | ❌       | 100     | Max messages to scan for links |

---

## Tips

- **Use `--json`** for all commands to get machine-parseable output (JSON Lines format)
- **Server ID vs Channel ID**: Use `list-servers` first, then `list-channels --server <ID>` to find the IDs you need
- **Search is guild-level**: `--server` is always required for search. Use `--channel` to narrow results within that server
- **Cache**: Results are cached locally in SQLite. Guilds/channels cache for 1 hour, search for 15 minutes
