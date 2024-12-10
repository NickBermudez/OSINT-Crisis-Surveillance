import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

def main():
    # Load environment variables from .env
    load_dotenv()

    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    if not all([POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]):
        print("Missing required database environment variables. Please check your .env file.")
        sys.exit(1)

    # Construct the SQLAlchemy connection URI
    connection_uri = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"
    engine = create_engine(connection_uri)

    # Query for messages that have not been embedded
    query = "SELECT id, message_text FROM messages WHERE embedding IS NULL"
    df = pd.read_sql(query, engine)

    if df.empty:
        print("No new messages to embed.")
        return

    # Initialize the SBERT model
    # If you have a GPU, set device='cuda', else set device='cpu'
    # If device='cuda' fails, you can try a fallback or just remove the device argument.
    try:
        model = SentenceTransformer('paraphrase-MiniLM-L6-v2', device='cuda')
    except Exception as e:
        print("CUDA not available or an error occurred using GPU. Falling back to CPU.")
        model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

    texts = df['message_text'].tolist()
    batch_size = 256
    all_embeddings = []

    # Batch encode messages for efficiency
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start+batch_size]
        batch_embeddings = model.encode(batch)
        all_embeddings.extend(batch_embeddings)

    # Update the database with the newly generated embeddings
    # We'll do a direct connection with psycopg2 for updating
    import psycopg2
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    cursor = conn.cursor()

    # Update each message with its embedding
    for i, msg_id in enumerate(df['id']):
        embedding_list = all_embeddings[i].tolist()
        cursor.execute("UPDATE messages SET embedding = %s WHERE id = %s", (embedding_list, msg_id))

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Updated {len(df)} messages with embeddings.")

if __name__ == "__main__":
    main()