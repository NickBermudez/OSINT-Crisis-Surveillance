FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed (e.g., for psycopg2 if not using binary)
# For Apple Silicon considerations and libpq, often the binary version psycopg2-binary is simpler.
# RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the session file into the container
COPY session_name.session session_name.session

# Copy the scraper code
COPY telegram_scraper.py telegram_scraper.py

# (Optional) If you need additional modules or scripts, copy them as well:
# COPY utils/ utils/

# By default, no command is specified. We'll specify a command at run-time.