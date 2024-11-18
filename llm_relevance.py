from llamaapi import LlamaAPI
class LlamaGenerator:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.client = LlamaAPI(api_key)

    def send_prompt(self, prompt):
        api_request_json = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "max_tokens": 500,
            "temperature": 0.0
        }
        response = self.client.run(api_request_json)
        response = response.json()
        message = response['choices'][0]['message']['content']
        return message

    def get_base_truth(self, keywords, selected_posts):
        post_texts = ''
        keywords_text = ''
        for idx, text in selected_posts.items():
            combined_text = str(idx) + ' ' + text
            post_texts += combined_text
        for keyword in keywords:
            keywords_text += keyword + ', '
        prompt = (f'given these posts and the keywords, rank them in order of most\
                  relevant to least relevant based on what an OSINT analyst would find interesting, formatted as a list of their given indices [index,index,index...] \
                  with no repeating elements. Also, include a formatted list of 1s and 0s on a new line based on if the post is relevant or not, where 1\
                  is relevant, and 0 is not. for example,\
                  [1,0,1,1,0...] do not include\
                  any additional text in the response. keywords: {keywords_text}, posts: {post_texts}')

        return self.send_prompt(prompt)

    def get_keywords(self, num_responses):
        prompt = (f'generate {str(num_responses)} lists of 1 to 10 keywords an OSINT analyst might use\
                  when searching for information related to a crisis formatted as \
                  1. keyword 1, keyword 2 ...  2. keyword 1, keyword 2.... 3. keyword 1, keyword 2...')
        return self.send_prompt(prompt)
