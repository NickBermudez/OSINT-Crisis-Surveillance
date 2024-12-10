# Telegram OSINT Reader

## Telegram Scraper

The Telegram Scraper fetches messages from specified public Telegram channels and stores them in a PostgreSQL database. It is designed to integrate with an embedding and ranking pipeline, enabling you to build OSINT dashboards and apply learning-to-rank models down the line.

### Features
- **Automated Scraping**: Periodically fetches new messages from public Telegram channels.
- **Incremental Updates**: Skips previously scraped messages, improving efficiency.
- **Database Integration**: Stores messages and metadata (text, views, forwards, timestamps) directly in a PostgreSQL database.
- **Flexible Configuration**: Set channel list, API credentials, and database details via environment variables.

### Prerequisites
- **Python 3.9+**
- **Telegram API Credentials**:
  - Obtain `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org).
  - A phone number associated with a Telegram account to authenticate the scraper.
- **PostgreSQL Database**:
  - A running Postgres instance accessible by the scraper.
  - A user with the necessary permissions to insert and update records.
- **Dependencies**:
  - `telethon` for Telegram API interactions
  - `psycopg2-binary` for PostgreSQL connectivity
  - `python-dotenv` for environment variable management (optional)

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/telegram-osint-reader.git
   cd telegram-osint-reader
   ```

2.	Set Up a Virtual Environment (optional but recommended):

```
python3 -m venv venv
source venv/bin/activate
```


3.	Install Dependencies:

```
pip install -r requirements.txt
```


Configuration

1.	Environment Variables:

Create a .env file at the project root:

TELEGRAM_API_ID=<your_api_id>
TELEGRAM_API_HASH=<your_api_hash>
TELEGRAM_PHONE=<your_telegram_phone_number>

POSTGRES_HOST=<your_postgres_host>
POSTGRES_DB=<your_database_name>
POSTGRES_USER=<your_db_username>
POSTGRES_PASSWORD=<your_db_password>


2.	Channels to Scrape:
Update the channels list in telegram_scraper.py (or a separate config file) with desired channel usernames or links:

```
channels = [
    'https://t.me/intelslava',
    '@BellumActaNews',
    'https://t.me/CIG_telegram'
]
```

3.	Database Schema:

Ensure your database is initialized with a suitable messages table:

```
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    channel_id INTEGER,
    channel_name TEXT,
    message_id INTEGER,
    message_text TEXT,
    date TIMESTAMP,
    views INTEGER,
    forwards INTEGER,
    embedding vector(384),     -- Optional, requires pgvector.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

#Note: If using pgvector for embeddings, run:

CREATE EXTENSION IF NOT EXISTS vector;
```


Usage

1.	First Run:

python telegram_scraper.py

On the first run, the scraper may prompt for a Telegram code (and possibly a 2FA password). Once authenticated, a session file is created to avoid repeated prompts.

2.	Subsequent Runs:

•	The scraper will skip previously scraped messages.

•	Integrate it into a cron job, systemd timer, or CI/CD pipeline to run periodically:

```
# Example cron (run every hour)
0 * * * * /path/to/your/env/bin/python /path/to/telegram_scraper.py >> /path/to/logs/scraper.log 2>&1
```


Troubleshooting

•	Missing Environment Variables:

If you see ValueError: Missing required environment variables, check your .env file and ensure all credentials are set.

•	Database Connection Errors:

Verify that POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD are correct and that your network/firewall settings allow connections.

•	Telegram Authentication Issues:

If the phone number or code is incorrect, the scraper will raise an error. Recheck your credentials and ensure your Telegram account is active.

Next Steps

•	Embedding Pipeline:
Once messages are stored, a separate embedding pipeline can process message_text and populate the embedding column.

•	Learning-to-Rank Model:
With embeddings in place, you can apply a pairwise LTR model to rank messages for OSINT analysis.

•	Web Dashboard:
Integrate the database with a FastAPI-based dashboard to serve ranked, filtered, and searchable messages to end-users.

License

This project is licensed under the MIT License – see the LICENSE file for details.

This README provides a comprehensive starting point. Adjust environment variable names, table schemas, and commands as needed to fit your exact environment and workflow.

