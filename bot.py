import os
import re
import logging
import discord
import datetime
import pytz
import asyncio
import json
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

# Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
calendar_service = build("calendar", "v3", credentials=creds)

# Discord bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
client = discord.Client(intents=intents)

EVENT_COLORS = {
    "@onyxia alliance": "7",  # Blue
    "@onyxia horde": "11",  # Red
    "@rendbuff": "5",  # Banana
}

MENTION_REGEX = re.compile(r"(@Onyxia Alliance|@Onyxia Horde|@RendBuff)", re.IGNORECASE)
DATE_REGEX = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})?\b|\btonight\b", re.IGNORECASE)
TIME_REGEX = re.compile(r"\b(\d{1,2}[:.]\d{2}|\d{4})\s*(CET|ST)?\b")
GUILD_REGEX = re.compile(r"<([^>]+)>")

SERVER_TIME = "Europe/Paris"
SERVER_TZ = pytz.timezone(SERVER_TIME)

PROCESSED_MESSAGES_FILE = "processed_messages.json"
processed_messages = {}

def save_processed_messages():
    try:
        with open(PROCESSED_MESSAGES_FILE, "w") as f:
            json.dump({str(k): v.isoformat() for k, v in processed_messages.items()}, f)
        logging.info(f"✅ Processed messages saved to {PROCESSED_MESSAGES_FILE}")
    except Exception as e:
        logging.error(f"❌ Error saving processed messages: {e}")

def load_processed_messages():
    global processed_messages
    try:
        if os.path.exists(PROCESSED_MESSAGES_FILE):
            with open(PROCESSED_MESSAGES_FILE, "r") as f:
                loaded_data = json.load(f)
                processed_messages = {int(k): datetime.datetime.fromisoformat(v) for k, v in loaded_data.items()}
            logging.info(f"✅ Loaded {len(processed_messages)} processed messages from file.")
    except Exception as e:
        logging.error(f"❌ Error loading processed messages: {e}")

def normalize_date(date):
    if isinstance(date, str):
        if date.lower() == "tonight":
            return datetime.datetime.today().strftime("%d-%m-%Y")
        return None

    if len(date) < 2 or len(date) > 3:
        logging.error(f"❌ Invalid date format: {date}")
        return None

    day, month = date[:2]  # Extract first two parts: Day and Month
    year = date[2] if len(date) == 3 else str(datetime.datetime.today().year)  # Use current year if missing

    # Ensure day and month are always two digits
    day = day.zfill(2)
    month = month.zfill(2)

    # If the year is only two digits, assume it's 20YY
    if len(year) == 2:
        year = f"20{year}"

    normalized_date = f"{day}-{month}-{year}"  # Return DD-MM-YYYY format

    logging.info(f"✅ Normalized Date: {date} → {normalized_date}")
    return normalized_date


def parse_message(message):
    guild_match = GUILD_REGEX.search(message)
    guild_name = guild_match.group(1).strip() if guild_match else "Unknown"
    raw_dates = DATE_REGEX.findall(message)
    message = DATE_REGEX.sub("", message)
    mentions = MENTION_REGEX.findall(message)
    if not mentions:
        logging.warning(f"⚠️ No valid mentions found in: {message}")
        return []

    times = []
    for match in TIME_REGEX.findall(message):
        time_str = match[0].strip().replace(".", ":")
        if len(time_str) == 4 and time_str.isdigit():
            time_str = f"{time_str[:2]}:{time_str[2:]}"
        times.append(time_str)


    dates = [normalize_date(date) for date in raw_dates if any(date)]
    dates = [date for date in dates if date is not None]

    if "tonight" in message.lower():
        dates.append(datetime.datetime.today().strftime("%d-%m-%Y"))
    if not dates:
        dates = [datetime.datetime.today().strftime("%d-%m-%Y")] * len(times)

    logging.info(f"Extracted mentions: {mentions}")
    logging.info(f"Extracted dates: {dates}")
    logging.info(f"Extracted times: {times}")


    event_list = []
    for i in range(len(times)):
        date = dates[i] if i < len(dates) else dates[-1]
        time = times[i]
        mention = mentions[i] if i < len(mentions) else mentions[-1]
        timezone = "CET"

        try:
            event_datetime = datetime.datetime.strptime(f"{date} {time}", "%d-%m-%Y %H:%M")
            event_datetime = SERVER_TZ.localize(event_datetime)
        except ValueError:
            logging.error(f"Skipping invalid date: {date} {time}")
            continue

        event_list.append({
            "mention": mention,
            "datetime": event_datetime.isoformat(),
            "timezone": timezone,
            "color": EVENT_COLORS.get(mention.lower(), "7"),
            "guild": guild_name
        })

    return event_list

async def process_message(message):
    if message.id in processed_messages:
        return

    parsed_events = parse_message(message.content)

    if not parsed_events:
        logging.info(f"❌ Couldn't parse message: {message.content}")
        return

    for event in parsed_events:
        event_details = {
            "summary": event["mention"].replace("@", ""),
            "start": {"dateTime": event["datetime"], "timeZone": SERVER_TIME},
            "end": {"dateTime": event["datetime"], "timeZone": SERVER_TIME},
            "colorId": event["color"],
            "description": f"Buff by {event['guild']}"
        }

        event_st = datetime.datetime.fromisoformat(event['datetime']).astimezone(SERVER_TZ)

        event_date_st = event_st.strftime("%d-%m-%Y")
        event_time_st = event_st.strftime("%H:%M")

        try:
            response = calendar_service.events().insert(calendarId=CALENDAR_ID, body=event_details).execute()
            logging.info(f"✅ Event added to Google Calendar: {response['htmlLink']}")
            await message.channel.send(f"✅ **{event['mention']}** added for {event_date_st} {event_time_st} ST. [View Event](<{response['htmlLink']}>)")
        except Exception as e:
            logging.error(f"❌ Error adding event: {e}")
            await message.channel.send("❌ Failed to add event to Google Calendar.")

    processed_messages[message.id] = datetime.datetime.utcnow()
    save_processed_messages()

async def check_message_history():
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            logging.info(f"✅ Checking message history for missed events...")

            channel = client.get_channel(TARGET_CHANNEL_ID)
            if not channel:
                logging.warning(f"⚠️ Target channel {TARGET_CHANNEL_ID} not found. Skipping history check.")
                await asyncio.sleep(300)
                continue

            now = datetime.datetime.utcnow()
            one_hour_ago = now - datetime.timedelta(hours=1)

            async for message in channel.history(limit=50, after=one_hour_ago):
                if message.author == client.user:
                    continue

                if message.id not in processed_messages:
                    logging.info(f"🆕 Found missed message: {message.content}")
                    await process_message(message)
                else:
                    logging.info(f"🆕 Already processed message: {message.content}")

            old_keys = [msg_id for msg_id, timestamp in processed_messages.items() if timestamp < one_hour_ago]
            for msg_id in old_keys:
                logging.info(f"🗑️ Removing old processed message: {msg_id}")
                del processed_messages[msg_id]

            if old_keys:
                save_processed_messages()

            logging.info("✅ Message history check complete.")
            await cleanup_duplicates()
        except Exception as e:
            logging.error(f"❌ Error in check_message_history: {e}")

        await asyncio.sleep(300)

async def cleanup_duplicates():
    try:
        logging.info("🧹 Checking for duplicate events in calendar...")

        now = datetime.datetime.utcnow().isoformat() + "Z"
        future = (datetime.datetime.utcnow() + datetime.timedelta(days=3)).isoformat() + "Z"

        events_result = calendar_service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now,
            timeMax=future,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        seen = {}
        duplicates = []

        for event in events:
            key = (
                event.get('start', {}).get('dateTime'),
                event.get('summary', '').strip().lower(),
                event.get('description', '').strip().lower()
            )

            if key in seen:
                duplicates.append(event.get('id'))
            else:
                seen[key] = event.get('id')

        for dup_id in duplicates:
            try:
                calendar_service.events().delete(calendarId=CALENDAR_ID, eventId=dup_id).execute()
                logging.info(f"🗑️ Removed duplicate event with ID: {dup_id}")
            except Exception as e:
                logging.error(f"❌ Failed to delete event {dup_id}: {e}")

        if not duplicates:
            logging.info("✅ No duplicates found.")
    except Exception as e:
        logging.error(f"❌ Error during duplicate cleanup: {e}")

@client.event
async def on_ready():
    logging.info(f"✅ Bot is online as {client.user}")
    load_processed_messages()
    client.loop.create_task(check_message_history())

@client.event
async def on_message(message):
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    if message.author.bot:
        return

    logging.info(f"📥 New message detected: {message.content}")
    await process_message(message)

@client.event
async def on_raw_message_edit(payload):
    logging.info(f"🔄 Raw message edit detected in channel {payload.channel_id}")

    channel = client.get_channel(payload.channel_id)
    if not channel:
        logging.error(f"⚠️ Channel {payload.channel_id} not found.")
        return

    try:
        message = await channel.fetch_message(payload.message_id)
        logging.info(f"📥 Edited Message: {message.content}")
        await process_message(message)

    except discord.NotFound:
        logging.error(f"⚠️ Message {payload.message_id} not found in channel {payload.channel_id}")

client.run(DISCORD_TOKEN)