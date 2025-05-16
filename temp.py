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

message = """<Mortal> 
:ony: :alliance:  - 28.02.2025 - 19:45
:ony: :alliance:  - 01.03.2025 - 19:45
:ony: :alliance:  - 02.03.2025 - 19:45
@Onyxia Alliance"""

message2 = "<Nihilum> Will pop @Onyxia Alliance 23:00 CET tonight 28-02-2025"

message3 = """<Victory> will pop @RendBuff   - 14:00
<Victory> will pop @RendBuff  - 17:01
<Victory> will pop @RendBuff  - 20:02
<Victory> will pop @Onyxia Horde    - 20:02
+- few mins depending on layer cd
"""

message4 = """<Just Pull HC>
@Onyxia Alliance   27/02/2025 - 18.45 ST"""

message5 = """<Victory> will pop @RendBuff    - 20:00
+- few mins depending on layer cd"""

#print(parse_message(message))
#print(parse_message(message2)) 
#print(parse_message(message3)) 
#print(parse_message(message4)) 
print(parse_message(message5))