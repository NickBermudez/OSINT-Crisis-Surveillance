"""
This script is used to initialize a user model
"""
# import dependencies
import torch
import torch.nn as nn
import torch.optim as optim


def get_ranking(score_1, score_2):
    """
    static method used to rank a pair of posts
    :param score_1: truncated tuple from self.user_dataset with
    (self.user_dataset index, relevance score)
    :param score_2: truncated tuple from self.user_dataset with
    (self.user_dataset index, relevance score)
    :return: float score 1 if first post is better, 0 if second post is better, 0.5 if posts are equal
    """
    if score_1 > score_2:
        return 1
    elif score_1 < score_2:
        return 0
    else:
        return 0.5


class RankingNetwork(nn.Module):
    """
    Neural network which shares parameters between 2 text embeddings and outputs the difference in scores
    between them.
    """
    def __init__(self, input_dim=384):
        """
        :param input_dim: feature size of embeddings, default 384 for SBERT
        """
        super(RankingNetwork, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, input_dim // 2),
            nn.ReLU(),
            nn.Linear(input_dim // 2, 1)
        )

    def forward(self, item_1, item_2):
        """
        :param item_1: text embedding from post 1
        :param item_2: text embedding from post 2
        :return: difference in scores used for loss calculation
        """
        score_1 = self.fc(item_1)
        score_2 = self.fc(item_2)
        return score_1 - score_2


class RankingAgent:
    """
    user specific model that ranks posts and updates to preferences over time
    """
    def __init__(self, input_dim=384, learning_rate=0.01, pretrained_model=None, train_size=15):
        """
        :param input_dim: feature size of embeddings, default 384 for SBERT
        :param learning_rate: learning rate of the optimizer, default 0.01 based on hyperparameter tuning
        :param pretrained_model: state dict for a previously optimized model
        :param train_size: number of posts after which the train method will execute
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = RankingNetwork(input_dim).to(self.device)
        if pretrained_model:
            self.model.load_state_dict(pretrained_model)
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.loss_fn = nn.BCEWithLogitsLoss()
        self.train_size = train_size
        self.user_dataset = []
        self.loss = 0

    def train(self):
        """
        Method used to train the pairwise model.
        :return: bool if model trained
        """
        # if not enough rankings exist, don't train
        if len(self.user_dataset) < self.train_size:
            return False
        self.model.train()
        # training_pairs will be used as a loader to optimize the model
        training_pairs = []
        for i in range(len(self.user_dataset)):
            for j in range(i + 1, len(self.user_dataset)):
                # user_dataset is a list of tuples [(relevance score, embedding)]
                label = get_ranking(self.user_dataset[i][0], self.user_dataset[j][0])
                training_pairs.append((self.user_dataset[i][1], self.user_dataset[j][1], label))
        # update the model according to rankings
        for pair in training_pairs:
            feature_1 = pair[0]
            feature_2 = pair[1]
            label = torch.tensor(pair[2]).to(self.device)
            ranking_score = self.model(feature_1, feature_2).squeeze()
            self.optimizer.zero_grad()
            loss = self.loss_fn(ranking_score, label.float())
            loss.backward()
            self.optimizer.step()
            self.user_dataset = []
            self.loss += loss.item()
        return True

    def predict_ranking(self, feature_1, feature_2):
        """
        Uses the model to predict which of two posts is more relevant
        :param feature_1: feature embeddings of first post
        :param feature_2: feature embeddings of second post
        :return: float of ranking score
        """
        self.model.eval()
        with torch.no_grad():
            ranking_score = self.model(feature_1.to(self.device), feature_2.to(self.device))
            return ranking_score.item()

    def rank_posts(self, post_embeddings):
        """
        ranks a list of posts
        :param post_embeddings: list of post embeddings
        :return: ranked indices of post embeddings
        """
        num_posts = len(post_embeddings)
        pairwise_scores = {}
        # for each possible pair of posts, predict which is more relevant than the other
        for i in range(num_posts):
            for j in range(i + 1, num_posts):
                score = self.predict_ranking(post_embeddings[i], post_embeddings[j])
                pairwise_scores[(i, j)] = score
        # initialize the cumulative scores for each post
        total_scores = [0] * num_posts
        # for each pair ranking, update the cumulative post score
        for (i, j), score in pairwise_scores.items():
            total_scores[i] += score
            total_scores[j] -= score
        # sorted indices by score for final ranking
        ranked_indices = sorted(range(num_posts), key=lambda idx: total_scores[idx], reverse=True)
        return ranked_indices

    def save_post_ranking(self, relevance_score, embedding):
        """
        saves user feedback for model training
        :param relevance_score: int, user relevance score
        :param embedding: text embedding for the suggested post
        :return: None
        """
        self.user_dataset.append((relevance_score, embedding))
        return
    