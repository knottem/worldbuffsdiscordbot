import os
import re
import logging
import discord
import datetime
import pytz
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS")

# Google Calendar Setup
SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
calendar_service = build("calendar", "v3", credentials=creds)

# Discord bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# Allowed event mentions
VALID_MENTIONS = ["@Onyxia Alliance", "@Onyxia Horde", "@RendBuff"]

# Color mapping
EVENT_COLORS = {
    "@Onyxia Alliance": "7",  # Blue
    "@Onyxia Horde": "11",  # Red
    "@RendBuff": "11",  # Red
}

MENTION_REGEX = re.compile(r"(@Onyxia Alliance|@Onyxia Horde|@RendBuff)")
DATE_REGEX = re.compile(r"\b\d{2}[-/.]\d{2}[-/.]\d{4}\b|\btonight\b", re.IGNORECASE)
TIME_REGEX = re.compile(r"\b(\d{1,2}[:.]\d{2})\s*(CET|ST)?\b")
GUILD_REGEX = re.compile(r"<([^>]+)>")

# Timezone
STOCKHOLM_TZ = pytz.timezone("Europe/Stockholm")

def parse_message(message):
    logging.info(f"Processing message: {message}")

    guild_match = GUILD_REGEX.search(message)
    guild_name = guild_match.group(1).strip() if guild_match else "Unknown"

    # Extract and remove dates first
    raw_dates = DATE_REGEX.findall(message)
    message = DATE_REGEX.sub("", message)  # Remove dates from message to avoid interference

    # Extract mentions
    mentions = MENTION_REGEX.findall(message)

    # Extract times AFTER removing dates
    times = [match[0].strip().replace(".", ":") for match in TIME_REGEX.findall(message)]  # Convert "." to ":"

    # Process valid dates
    dates = [date.strip().replace(".", "-").replace("/", "-") for date in raw_dates if date and date.lower() != "tonight"]

    # Handle "tonight"
    if "tonight" in message.lower():
        dates.append(datetime.datetime.today().strftime("%d-%m-%Y"))

    # If no dates found, assume today for each event
    if not dates:
        dates = [datetime.datetime.today().strftime("%d-%m-%Y")] * len(times)

    logging.info(f"Extracted mentions: {mentions}")
    logging.info(f"Extracted dates: {dates}")
    logging.info(f"Extracted times: {times}")

    # Match mentions, dates, and times correctly
    event_list = []
    for i in range(len(times)):  # Iterate over times, since times determine number of events
        date = dates[i] if i < len(dates) else dates[-1]  # Ensure correct date matching
        time = times[i]
        mention = mentions[i] if i < len(mentions) else mentions[-1]  # Ensure correct mention matching
        timezone = "CET"

        try:
            event_datetime = datetime.datetime.strptime(f"{date} {time}", "%d-%m-%Y %H:%M")
            event_datetime = STOCKHOLM_TZ.localize(event_datetime).astimezone(pytz.utc)
        except ValueError:
            logging.error(f"Skipping invalid date: {date} {time}")
            continue

        event_list.append({
            "mention": mention,
            "datetime": event_datetime.isoformat(),
            "timezone": timezone,
            "color": EVENT_COLORS.get(mention, "7"),
            "guild": guild_name
        })

    return event_list

@client.event
async def on_ready():
    logging.info(f"✅ Bot is online as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    parsed_events = parse_message(message.content)
    if not parsed_events:
        logging.info(f"Couldn't parse this correctly: {message.content}")
        return

    for parsed_event in parsed_events:
        event_details = {
            "summary": parsed_event["mention"].replace("@", ""),
            "start": {"dateTime": parsed_event["datetime"], "timeZone": "UTC"},
            "end": {"dateTime": parsed_event["datetime"], "timeZone": "UTC"},
            "colorId": parsed_event["color"],
            "description": f"Buff by {parsed_event['guild']}"
        }

        try:
            response = calendar_service.events().insert(calendarId=CALENDAR_ID, body=event_details).execute()
            logging.info(f"✅ Event added to Google Calendar: {response['htmlLink']}")
            await message.reply(f"✅ Event added to Google Calendar: {response['htmlLink']}")
        except Exception as e:
            logging.error(f"❌ Error adding event: {e}")
            await message.reply("❌ Failed to add event to Google Calendar.")

# Run the bot
client.run(DISCORD_TOKEN)