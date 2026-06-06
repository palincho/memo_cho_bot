# Drift

A personal Telegram bot for memory capture. Single-user, zero friction.

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Usage

- Send any message → captured to inbox
- Forward a message → captured with original sender as source
- Send a voice message → file reference stored
- `/review` — show all active memos with action buttons
- `/time HH:MM` — set daily reminder time
- `/help` — show all commands

## Deploy

See `deploy/setup.sh` for GCE e2-micro setup instructions.
