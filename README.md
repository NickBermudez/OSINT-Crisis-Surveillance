Kaizen is an OSINT analyst recommender system that leverages pairwise ranking of SBERT embeddings and background batch processing to learn user preferences.

Data
-------------------------
The datasets used for this project can be found at:
https://drive.google.com/drive/u/1/folders/1Lbh-AujxMt6E7ZQM768pL36RqiK7-Cyt

Includes posts scraped from Telegram channels:
IntelSlavaZ
bellamactanews
Contains the dataset "Shaping the Narratives of the Russia-Ukraine War for Western Audiences: An Exploration of English-language Telegram Channels".
https://figshare.com/articles/dataset/_Dataset_Shaping_the_Narratives_of_the_Russia-Ukraine_War_for_Western_Audiences_An_Exploration_of_English-language_Telegram_Channels/25139276

Additional files include:

-Pre-computed SBERT embeddings saved as a pickle file
-A Telegram pandas DataFrame saved as a pickle file, which can be regenerated using the notebooks in the scripts folder.
Scripts

'scripts' folder
-------------------------
bandit_model_visualizations.ipynb
Contains the contextual bandit model, training, and visualizations of its performance. (Note: This model was not modularized due to suboptimal NDCG performance.)

create_embeddings.ipynb
Generates and saves SBERT embeddings used to train the contextual bandit and pairwise ranking models.

dataframe_gen.ipynb
Combines data from the scraped IntelSlavaZ, bellamactanews channels, and the mixed Russia-Ukraine war datasets. It also generates synthetic user scores for posts.

pairwise_model.py
Modularizes the pairwise ranking agent for use in the web application.

pairwise_model_visualizations.ipynb
Trains the pairwise ranking model through hyperparameter tuning and generates performance visualizations.

'website' folder
-------------------------
website.py
Contains the code to locally run a demo version of our app

Recommended Setup
-------------------------
-Download the dataset files from the provided Google Drive link and extract the contents into a folder named 'data'.

-Place the scripts into a separate folder named 'scripts'.

-Use the Jupyter notebooks in the scripts folder to generate embeddings, create dataframes, and train models.

-Make a copy of pairwise_model.py and place it in the same directory as website.py

-To run website.py locally, navigate to its directory and run the following command: streamlit run website.py 
      
