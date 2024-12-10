from telethon import TelegramClient, events, sync
from telethon.errors import SessionPasswordNeededError, PasswordHashInvalidError
from telethon.tl.types import Channel, User
import asyncio
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
import re
import psycopg2

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Securely get credentials
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE = os.getenv('TELEGRAM_PHONE')
TWO_FA_PASSWORD = os.getenv('TELEGRAM_2FA_PASSWORD') 

# Database credentials for PostgreSQL
DB_HOST = os.getenv('POSTGRES_HOST')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')

# Validate credentials
if not all([API_ID, API_HASH, PHONE, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

def setup_database():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        c = conn.cursor()
        
        # Create messages table without media_type and media_path
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                channel_id INTEGER,
                channel_name TEXT,
                message_id INTEGER,
                message_text TEXT,
                date TIMESTAMP,
                views INTEGER,
                forwards INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table to track last scraped message ID per channel
        c.execute('''
            CREATE TABLE IF NOT EXISTS channels_progress (
                channel_id INTEGER PRIMARY KEY,
                channel_name TEXT UNIQUE,
                last_scraped_message_id INTEGER
            )
        ''')

        conn.commit()
        c.close()
        logger.info("Database setup completed successfully")
        return conn
    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        raise

class TelegramScraper:
    def __init__(self):
        self._validate_phone_number(PHONE)
        self.client = TelegramClient('session_name', API_ID, API_HASH)
        self.db_conn = setup_database()

    @staticmethod
    def _validate_phone_number(phone):
        pattern = r'^\+\d{1,15}$'
        
        if not phone:
            raise ValueError("Phone number is required")
            
        if not re.match(pattern, phone):
            raise ValueError(
                "Invalid phone number format. "
                "Must start with + followed by country code and number. "
                "Example: +14155552671"
            )
        
        return phone.strip()

    async def start(self):
        try:
            if not self.client.is_connected():
                await self.client.connect()

            if not await self.client.is_user_authorized():
                logger.info(f"Sending authentication code to {PHONE}")
                try:
                    await self.client.send_code_request(PHONE)
                except Exception as e:
                    if "phone_number_invalid" in str(e):
                        raise ValueError("Invalid phone number format. Check your PHONE in .env")
                    raise
                
                code = input('Enter the code you received: ')
                try:
                    await self.client.sign_in(PHONE, code)
                except SessionPasswordNeededError:
                    # 2FA is enabled
                    if not TWO_FA_PASSWORD:
                        password = input('Two-step verification is enabled. Enter your password: ')
                    else:
                        password = TWO_FA_PASSWORD
                    
                    try:
                        await self.client.sign_in(password=password)
                    except PasswordHashInvalidError:
                        raise ValueError("Invalid 2FA password provided")
                except Exception as e:
                    if "phone_code_invalid" in str(e):
                        raise ValueError("Invalid code entered")
                    raise
                
                logger.info("Successfully authenticated with Telegram")
            
            logger.info("Client started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start client: {str(e)}")
            raise

    async def initialize_channel(self, channel_id, channel_username, batch_size=50):
        # Check if we already have a record
        cursor = self.db_conn.cursor()
        cursor.execute('''
            SELECT last_scraped_message_id 
            FROM channels_progress
            WHERE channel_id = %s OR channel_name = %s
        ''', (channel_id, channel_username))
        row = cursor.fetchone()

        if row and row[0] and row[0] > 0:
            # Already initialized
            cursor.close()
            return row[0]
        else:
            # Need to initialize by fetching a small batch of recent messages
            channel = await self.client.get_entity(channel_username)

            recent_messages = []
            async for message in self.client.iter_messages(channel, limit=batch_size):
                # Only consider messages with text
                if message.text and message.text.strip():
                    recent_messages.append(message)

            if not recent_messages:
                # Channel might be empty or no text messages
                baseline_id = 0
            else:
                max_message_id = 0
                for msg in recent_messages:
                    self._store_message_db(
                        channel_id=channel.id,
                        channel_name=channel_username,
                        message_id=msg.id,
                        message_text=msg.text,
                        date=msg.date,
                        views=getattr(msg, 'views', 0),
                        forwards=getattr(msg, 'forwards', 0)
                    )
                    if msg.id > max_message_id:
                        max_message_id = msg.id

                baseline_id = max_message_id

            # Store the baseline in channels_progress
            cursor.execute('''
                INSERT INTO channels_progress (channel_id, channel_name, last_scraped_message_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (channel_id) DO UPDATE SET last_scraped_message_id = EXCLUDED.last_scraped_message_id
            ''', (channel_id, channel_username, baseline_id))
            self.db_conn.commit()
            cursor.close()

            return baseline_id

    async def scrape_channel(self, channel_username):
        try:
            channel = await self.client.get_entity(channel_username)
            logger.info(f"Scraping new messages for channel: {channel_username}")

            # Initialize or get the last scraped message ID with a batch of recent messages if needed.
            last_scraped_id = await self.initialize_channel(channel.id, channel_username, batch_size=50)

            async for message in self.client.iter_messages(channel, min_id=last_scraped_id):
                # Only scrape messages that contain text
                if not message.text or not message.text.strip():
                    continue

                self._store_message_db(
                    channel_id=channel.id,
                    channel_name=channel_username,
                    message_id=message.id,
                    message_text=message.text,
                    date=message.date,
                    views=getattr(message, 'views', 0),
                    forwards=getattr(message, 'forwards', 0)
                )
                logger.info(f"Scraped message {message.id} from {channel_username}")
                self._update_last_scraped_message_id(channel.id, channel_username, message.id)

        except Exception as e:
            logger.error(f"Error scraping channel {channel_username}: {str(e)}")
            raise

    def _store_message_db(self, channel_id, channel_name, message_id, message_text, date, views, forwards):
        cursor = self.db_conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO messages 
                (channel_id, channel_name, message_id, message_text, date, views, forwards)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                channel_id,
                channel_name,
                message_id,
                message_text,
                date,
                views,
                forwards
            ))
            self.db_conn.commit()
            logger.debug(f"Stored message {message_id} in database")
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            self.db_conn.rollback()
            raise
        finally:
            cursor.close()

    def _update_last_scraped_message_id(self, channel_id, channel_name, message_id):
        cursor = self.db_conn.cursor()
        try:
            cursor.execute('''
                UPDATE channels_progress
                SET last_scraped_message_id = %s
                WHERE channel_id = %s OR channel_name = %s
            ''', (message_id, channel_id, channel_name))
            if cursor.rowcount == 0:
                # If no record exists, insert it
                cursor.execute('''
                    INSERT INTO channels_progress (channel_id, channel_name, last_scraped_message_id)
                    VALUES (%s, %s, %s)
                ''', (channel_id, channel_name, message_id))
            self.db_conn.commit()
        except Exception as e:
            logger.error(f"Error updating last_scraped_message_id: {str(e)}")
            self.db_conn.rollback()
            raise
        finally:
            cursor.close()

    async def close(self):
        await self.client.disconnect()
        self.db_conn.close()
        logger.info("Scraper shutdown completed")

async def main():
    # List of channels to scrape
    channels = [
        'https://t.me/intelslava',
        '@BellumActaNews',
        'https://t.me/CIG_telegram'
        # Add more channels as needed
    ]
    
    scraper = TelegramScraper()
    
    try:
        await scraper.start()
        
        for channel in channels:
            try:
                await scraper.scrape_channel(channel)  
                logger.info(f"Completed scraping channel: {channel}")
            except Exception as e:
                logger.error(f"Failed to scrape channel {channel}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write('''TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_PHONE=''')
        logger.warning("Created .env file. Please fill in your credentials.")
        exit(1)
        
    asyncio.run(main())