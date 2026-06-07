# Drift

Telegram bot for personal memory capture. Single user, no auth needed.

## Stack
- Python 3.11+
- aiogram 3.x (async Telegram bot framework)
- SQLite via aiosqlite (async)
- APScheduler 3.x (in-process scheduler for daily reminder)
- Deployed on GCE free tier e2-micro (US region)

## Commands to run
- `python main.py` — start the bot (long polling)
- `pytest tests/` — run tests
- `pip install -r requirements.txt` — install deps

## Key principles (non-negotiable, from PRD)
- Raw message is NEVER modified. Store verbatim, always.
- One inbox. Every capture lands in the same stream.
- Nothing is silently deleted. Only explicit "Let go" removes.
- Snoozed items hide until next day, then reappear automatically.
- Zero required fields at capture — plain message = captured.

## Data model
Table: `memos`
- id INTEGER PRIMARY KEY
- text TEXT NOT NULL          -- verbatim, never modified
- created_at DATETIME
- status TEXT                 -- 'active' | 'done' | 'dropped'
- snoozed_until DATE          -- nullable; hides item until this date
- source TEXT                 -- nullable; for forwarded messages or trusted sender name

Active list = status='active' AND (snoozed_until IS NULL OR snoozed_until <= today)

Table: `trusted_users`
- user_id INTEGER PRIMARY KEY
- name TEXT
- added_at DATETIME

## Bot behaviour
- Any plain message → capture → save → ack with "Got it."
- Forwarded message → capture with source = original sender name
- Voice message → save file_id as text ref, ack "Voice stored."
- /review → show all active memos, each with 3 inline buttons
- /time HH:MM → set daily reminder time (stored in settings table)
- /adduser <id> [name] → add a trusted sender (stored in trusted_users table)
- /removeuser <id> → revoke a trusted sender
- /listusers → list all trusted senders
- /help → show command list

## Inline keyboard per memo
- ✓ Done  → status = 'done'
- 💤 Snooze → snoozed_until = tomorrow
- 🗑 Let go → status = 'dropped'
After action: edit the message to show "Done." / "Snoozed." / "Gone." and remove buttons.

## Scheduler
APScheduler AsyncIOScheduler, CronTrigger.
Reads reminder time from settings table at startup.
/time command reschedules the job live without restart.

## Environment variables (.env)
- BOT_TOKEN — from @BotFather
- ALLOWED_USER_ID — your Telegram user ID (single-user guard)
- DB_PATH — path to SQLite file (default: ./drift.db)
- REMINDER_TIME — default HH:MM if not set in DB (e.g. 08:00)

## Code style
- Async everywhere (aiogram 3 is fully async)
- Use aiosqlite for all DB calls, never sqlite3 directly
- Keep handlers thin — business logic in db/models.py
- No global state except the scheduler instance
- Type hints on all functions
