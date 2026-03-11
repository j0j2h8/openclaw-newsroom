# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

OpenClaw is a personal AI agent platform. This directory (`~/.openclaw`) is the runtime configuration and workspace for an always-on AI assistant that connects to messaging channels (Slack, WhatsApp, Telegram), runs on heartbeat polling, manages persistent memory, and executes cron jobs.

This is **not** a traditional code project — it's a deployed agent's home directory. There is no build system, test suite, or package manager.

## Directory Structure

- `workspace/` — The agent's working directory (has its own git repo)
  - `SOUL.md` — Agent personality and behavioral guidelines
  - `IDENTITY.md` — Agent's name, creature type, vibe, emoji
  - `USER.md` — Information about the human owner
  - `AGENTS.md` — Operational manual: startup sequence, memory rules, heartbeats, group chat behavior
  - `TOOLS.md` — Environment-specific notes (cameras, SSH hosts, TTS voices)
  - `HEARTBEAT.md` — Periodic check tasks (empty = skip heartbeat API calls)
  - `BOOTSTRAP.md` — First-run onboarding script (delete after initial setup)
  - `memory/` — Daily logs (`YYYY-MM-DD.md`) and curated long-term memory (`MEMORY.md`)
- `openclaw.json` — Main config: auth, model selection, channel configs (Slack tokens, gateway settings), hooks, tool profile
- `agents/main/` — Main agent session state
- `cron/jobs.json` — Scheduled tasks
- `memory/main.sqlite` — Persistent memory database
- `devices/` — Paired device registry
- `identity/` — Device auth and identity keys
- `settings/voicewake.json` — Voice wake word triggers (currently: "openclaw", "claude", "computer")
- `logs/` — Gateway logs (`gateway.log`, `gateway.err.log`) and config audit trail
- `completions/` — Shell completions (bash, zsh, fish, powershell)
- `canvas/index.html` — Canvas UI

## Key Configuration (openclaw.json)

- **Model:** `openai-codex/gpt-5.4`
- **Auth:** OpenAI Codex via OAuth
- **Channels:** Slack (socket mode, bot+app tokens, streaming enabled)
- **Gateway:** Local mode on port 18789, loopback-only, token auth
- **Denied commands:** camera.snap, camera.clip, screen.record, contacts.add, calendar.add, reminders.add, sms.send
- **Hooks:** boot-md and session-memory (internal, enabled)

## Working With This Repository

When modifying workspace files:
- `SOUL.md` changes are identity-altering — the agent should be informed
- `HEARTBEAT.md` controls what the agent checks on each poll cycle; empty file = no checks
- `openclaw.json` changes may require gateway restart
- Tokens and auth data in `openclaw.json`, `identity/`, and `devices/` are sensitive — never commit or expose them
- The workspace has its own git repo at `workspace/.git` — commit workspace changes there, not at the root level

## Agent Operational Model

The agent follows this session startup sequence (defined in `AGENTS.md`):
1. Read `SOUL.md` (identity/behavior)
2. Read `USER.md` (human context)
3. Read recent daily memory files
4. In main sessions only: read `MEMORY.md` (security — contains personal context)

Memory hierarchy: daily files (`memory/YYYY-MM-DD.md`) are raw logs; `MEMORY.md` is curated long-term memory. The agent periodically distills daily files into `MEMORY.md` during heartbeats.
