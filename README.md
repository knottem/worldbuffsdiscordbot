# Discord Buff Event Bot

This is a Discord bot that listens for specific messages in a channel and automatically adds relevant buff events to a linked Google Calendar. 
It is primarily designed for tracking scheduled events for World of Warcraft Classic Hardcore guilds. 
Made it in a day just to keep track of buffs so it's quite shit, 
but after [whenbuff](https://whenbuff.com/) came I abandonded this, go give some love to [Pomme](https://buymeacoffee.com/pomme)

Put it up on github now after a couple of months since I'm not really gonna touch it any more probably.

## Features

* Parses messages for specific mentions (e.g., `@Onyxia Alliance`, `@Onyxia Horde`, `@RendBuff`)
* Extracts dates, times, and optional guild names (e.g., `<Guild Name>`)
* Supports formats like:

    * `12-05-2025 19:00 @Onyxia Horde <Guild>`
    * `Tonight 20.30 @RendBuff <MyGuild>`
* Automatically creates Google Calendar events for valid inputs

## Requirements

* Python 3.8+
* Discord bot token
* Google Calendar API credentials
* `.env` file with necessary environment variables

## Setup

### 1. Clone the repository

```bash
git clone git@github.com:knottem/worldbuffsdiscordbot.git
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file

Create a `.env` file in the project root with the following content:

```env
DISCORD_TOKEN=your_discord_bot_token
GOOGLE_CALENDAR_ID=your_calendar_id@group.calendar.google.com
GOOGLE_CREDENTIALS=google-service-account.json
```

### 4. Setup Google Calendar API

* Create a service account in Google Cloud Console
* Enable Google Calendar API
* Download the service account JSON file
* Rename it to `google-service-account.json` or update the path in `.env`
* Share the Google Calendar with the service account email

### 5. Run the bot

Either just run the bot straight away

```bash
python bot.py
```
or run it as a docker, just make sure to change the volume in the docker-compose.yml to be your correct json

```bash
docker compose up -d
```

## How It Works

* The bot monitors messages in channels it has access to.
* It looks for specific mentions and a date/time pattern.
* If found, it adds an event to Google Calendar with the time, label, and optional guild tag.

## Example Messages

```
@Onyxia Alliance 16/05/2025 20:00 <MyGuild>
@RendBuff tonight 19.30 <RaidTeam>
```

## Notes

* Events are added in UTC to Google Calendar.
* Default timezone used for parsing is Europe/Stockholm.
* If no date is mentioned, "tonight" is interpreted as today's date.
