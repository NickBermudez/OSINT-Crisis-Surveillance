import streamlit as st
import pickle
import torch
from pairwise_model import RankingAgent
from functools import partial
import pandas as pd
import psycopg2
from sentence_transformers import SentenceTransformer

POSTGRES_DB = "telegram"
TABLE_NAME = "messages"
POSTGRES_HOST = st.secrets["postgres"]["host"]
POSTGRES_USER = st.secrets["postgres"]["user"]
POSTGRES_PASSWORD = st.secrets["postgres"]["password"]

if 'telegram_df' not in st.session_state:
    with st.spinner('Loading data from database...'):
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            dbname=POSTGRES_DB
        )
        cursor = conn.cursor()
        query = f"SELECT * FROM {TABLE_NAME};"
        cursor.execute(query)
    
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        st.session_state.telegram_df = pd.DataFrame(rows, columns=column_names)
        cursor.close()
        conn.close()
    st.success('Data loaded successfully!')

if 'embeddings' not in st.session_state:
    with st.spinner('Generating SBERT embeddings...'):
        model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        st.session_state.embeddings = []
        for i in range(len(st.session_state.telegram_df)):
            row = st.session_state.telegram_df.iloc[i]
            text = row['message_text']
            embedding = model.encode(text)
            st.session_state.embeddings.append(embedding)
        st.success('Embeddings generated successfully!')
        
if 'agent' not in st.session_state:
    try:
        with open('best_pairwise_model.pkl', 'rb') as file:
            pretrained_model = pickle.load(file)
    except:
        pretrained_model = None
    st.session_state.agent = RankingAgent(pretrained_model=pretrained_model)

if 'used_indices' not in st.session_state:
    st.session_state.used_indices = []
if 'posts' not in st.session_state:
    st.session_state.posts = []


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
st.title("KAIZEN")
st.subheader("a recommender system for OSINT analysts")
telegram_tensors = [torch.tensor(emb) for emb in st.session_state.embeddings]
telegram_tensors = torch.vstack(telegram_tensors)
telegram_tensors = telegram_tensors.to(device)
filtered_indices = [i for i in range(len(telegram_tensors)) if (i not in st.session_state.used_indices)]
filtered_tensors = telegram_tensors[filtered_indices]


def rank(tensors, indices):
    ranked_indices = []
    stop_idx = len(tensors)
    i = 0
    j = min(len(tensors), 50)
    while j < stop_idx:
        temp_posts = tensors[i:j]
        temp_indices = indices[i:j]
        ranked = st.session_state.agent.rank_posts(temp_posts)[:max(15, len(temp_posts))]
        ranked_temp = [temp_indices[idx] for idx in ranked]
        for idx in ranked_temp:
            ranked_indices.append(idx)
        i = j
        j += min(50, len(tensors) - j)

    return ranked_indices


def handle_button_click(j, idx, i):
    st.session_state.agent.save_post_ranking((j+1), telegram_tensors[idx])
    st.session_state.agent.train()
    st.session_state.posts.pop(i)


if len(st.session_state.agent.user_dataset) % 15 == 0:
    st.markdown("### Model update in progress: Selecting new posts...")
    selected_posts = rank(filtered_tensors, filtered_indices)
    st.session_state.posts = [(idx, st.session_state.telegram_df['message_text'][idx],
                               st.session_state.telegram_df['created_at'][idx]) for idx in selected_posts]

num_posts = min(10, len(st.session_state.posts))
for i in range(num_posts):
    idx, post, datetime = st.session_state.posts[i]
    st.session_state.used_indices.append(idx)
    st.markdown(f"""
        <div style="max-height: 150px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px;">
            <p><strong>Date:</strong> {datetime}</p>
            <p>{post}</p>
    """, unsafe_allow_html=True)

    cols = st.columns(5)
    for j in range(5):
        with cols[j]:
            st.button(f"{j + 1}", key=f"rating_button_{i}_{idx}_{j}", on_click=partial(handle_button_click, j, idx, i))



