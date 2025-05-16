FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy dependencies first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot's code into the container
COPY . .

# Start the bot
CMD ["python", "bot.py"]