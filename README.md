# 🔍 Discord Research for Antigravity

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)

**Give your [Antigravity](https://google.com/antigravity) AI agent the ability to search and analyze Discord messages.**

AI assistants can search the web — but they can't access the massive knowledge hidden in Discord communities. This tool changes that. It provides 10 CLI commands that let your Antigravity agent browse servers, search messages, follow conversations, extract links, and more.

---

> [!WARNING]
> **This tool uses Discord user tokens, which is against Discord's Terms of Service.**
> Use of user tokens may result in account termination. This project is provided for **educational and personal use only**. The author assumes no responsibility for misuse or consequences to your Discord account. By using this tool, you acknowledge and accept these risks.

---

## ✨ Features

- 🔎 **Search messages** across any server with keyword, date, author, and content-type filters
- 📨 **Fetch messages** from any channel with pagination
- 📌 **Read pinned messages** — often the most important curated info
- 🧵 **Browse threads** — access in-depth discussions
- 🔗 **Extract links** — find all URLs shared in a channel
- 💬 **Follow reply chains** — trace full conversations
- 🔄 **Get context** — read messages around any specific message
- 💾 **Local SQLite cache** — repeated searches are instant
- 🛡️ **Anti-detection** — mimics Discord web client with proper headers and rate limiting
- 📊 **JSON output** — all commands support `--json` for machine-parseable output

---

## 🚀 Quick Start

### Step 1: Clone the Repository

```bash
git clone https://github.com/Longjumping-Mango/discord-research-antigravity.git
cd discord-research-antigravity
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Set Your Discord Token

```bash
# Windows (Command Prompt)
setx DISCORD_USER_TOKEN "your-token-here"

# Windows (PowerShell)
[System.Environment]::SetEnvironmentVariable("DISCORD_USER_TOKEN", "your-token-here", "User")

# Mac/Linux
export DISCORD_USER_TOKEN="your-token-here"
```

Don't know your token? See [How to Get Your Discord Token](#-how-to-get-your-discord-token) below.

### Step 4: Test It

```bash
python src/discord_cli.py user-info
```

You should see:

```
=== Discord User Info ===
  Username: YourName
  ID: 1234567890
  Token: Valid ✅
```

---

## 🔑 How to Get Your Discord Token

> [!CAUTION]
> Your Discord token is like your password. **Never share it** with anyone or paste it in public places.

1. Open **Discord in your web browser** at [discord.com/app](https://discord.com/app)
2. Press **F12** to open Developer Tools
3. Click the **Network** tab
4. In Discord, navigate to any channel or send a message to trigger network requests
5. In the Network tab, click on any request to `discord.com/api`
6. Scroll down in the right panel to **Request Headers**
7. Find the **`Authorization`** header — the value is your token
8. Copy it and set it as an environment variable (see Step 3 above)

**Alternative**: You can also pass the token directly via CLI:

```bash
python src/discord_cli.py --token "your-token-here" user-info
```

---

## 🤖 Antigravity Integration

This is where the magic happens. Once installed, your Antigravity agent can autonomously search Discord to answer your questions.

### Option A: One-Prompt Auto-Install (Recommended)

Copy and paste this prompt into Antigravity to let it install everything automatically:

> **Prompt to paste in Antigravity:**

```
I need you to set up the discord-research skill for Antigravity. Here's everything you need:

1. The repo is already cloned at: <PASTE_YOUR_CLONE_PATH_HERE>
   (e.g., ~/.gemini/antigravity/mcp_servers/discord-research)

2. Install Python dependencies:
   pip install -r <CLONE_PATH>/requirements.txt

3. Set the Discord user token — the user has set the DISCORD_USER_TOKEN environment variable,
   OR write it directly in <CLONE_PATH>/src/discord_client.py on line 22:
   USER_TOKEN = "paste-token-here"

4. Create the Antigravity skill:
   - Create directory: ~/.antigravity/skills/discord-research/
   - Copy <CLONE_PATH>/skill/SKILL.md to ~/.antigravity/skills/discord-research/SKILL.md
   - In the copied SKILL.md, replace ALL instances of <INSTALL_DIR> with the actual clone path

5. Add to my GEMINI.md (the user rules file at ~/.gemini/GEMINI.md).
   Find the section for skill activation (or create one) and add:
   `discord-research` — ACTIVATE when: searching Discord, researching Discord communities,
   analyzing Discord channels/messages/threads. Triggers: "discord", "server", "channel",
   "community chat", "messages from discord".

6. Verify by running: python <CLONE_PATH>/src/discord_cli.py user-info
   It should show "Token: Valid ✅"

Report back what you did and if everything is working.
```

### Option B: Manual Installation

If you prefer to do it yourself:

#### 1. Clone the repo to a persistent location

```bash
git clone https://github.com/Longjumping-Mango/discord-research-antigravity.git ~/.gemini/antigravity/mcp_servers/discord-research
cd ~/.gemini/antigravity/mcp_servers/discord-research
pip install -r requirements.txt
```

#### 2. Create the skill directory

```bash
mkdir -p ~/.antigravity/skills/discord-research
cp skill/SKILL.md ~/.antigravity/skills/discord-research/SKILL.md
```

#### 3. Update the SKILL.md paths

Open `~/.antigravity/skills/discord-research/SKILL.md` and replace all `<INSTALL_DIR>` with your actual install path. For example:

```
# Before:
python <INSTALL_DIR>/src/discord_cli.py search --server ...

# After:
python ~/.gemini/antigravity/mcp_servers/discord-research/src/discord_cli.py search --server ...
```

#### 4. Add to GEMINI.md

Open your `~/.gemini/GEMINI.md` and add the following under your skill activation rules:

```markdown
`discord-research` — ACTIVATE when: searching Discord, researching Discord communities,
analyzing Discord channels/messages/threads. Triggers: "discord", "server", "channel",
"community chat", "messages from discord".
```

#### 5. Verify

```bash
python src/discord_cli.py user-info
python src/discord_cli.py list-servers
```

---

## 📋 Commands

| Command                                        | Description                        |
| ---------------------------------------------- | ---------------------------------- |
| `user-info`                                    | Validate token and show user info  |
| `list-servers`                                 | List all Discord servers you're in |
| `list-channels --server <ID>`                  | List channels in a server          |
| `get-messages --channel <ID>`                  | Fetch messages from a channel      |
| `search --server <ID> --query "text"`          | Search messages by keyword         |
| `get-context --channel <ID> --message <ID>`    | Get surrounding messages           |
| `follow-replies --channel <ID> --message <ID>` | Trace a reply chain                |
| `get-pins --channel <ID>`                      | Get pinned messages                |
| `get-threads --channel <ID>`                   | List threads in a channel          |
| `extract-links --channel <ID>`                 | Extract all URLs from messages     |

👉 **Full command reference with all options**: [docs/COMMANDS.md](docs/COMMANDS.md)

---

## 🏗️ How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│   Antigravity    │────▶│  discord_cli.py  │────▶│  Discord API  │
│   (AI Agent)     │     │  (10 commands)   │     │   (REST v10)  │
└─────────────────┘     └──────────────────┘     └───────────────┘
                              │                         │
                              ▼                         │
                        ┌──────────────┐                │
                        │  SQLite Cache │◀───────────────┘
                        │  (local DB)   │
                        └──────────────┘
```

1. **Antigravity** detects a Discord-related question and activates the `discord-research` skill
2. The skill instructs the agent to use `discord_cli.py` commands via `run_command`
3. The CLI sends requests to Discord's REST API with anti-detection headers
4. Results are cached locally in SQLite for fast repeated access
5. The agent synthesizes findings and presents them to you

### Anti-Detection Features

- Dynamic Discord build number fetched from live assets
- Browser-like `X-Super-Properties` headers
- Per-route rate limiting with automatic 429 retry
- Human-like request pacing (150-500ms random delay)

### Cache Behavior

| Data Type        | TTL                                         |
| ---------------- | ------------------------------------------- |
| Guilds (servers) | 1 hour                                      |
| Channels         | 1 hour                                      |
| Search results   | 15 minutes                                  |
| Messages         | Freshness check (fetches only new messages) |

---

## 📜 License

[MIT License](LICENSE) — Use it however you want. No strings attached.

---

## 🤝 Contributing

Found a bug? Have a feature idea? Open an issue or submit a PR. All contributions welcome.

---

## ⚠️ Disclaimer

This project is for **educational and personal use only**. It interacts with Discord using user tokens, which violates Discord's Terms of Service. The author is not responsible for any consequences resulting from the use of this tool, including but not limited to account suspension or termination. Use at your own risk and responsibility. This project does not store, transmit, or share any user data to third parties. All data is processed locally on your machine.
