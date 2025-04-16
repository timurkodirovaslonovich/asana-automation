import requests
import nltk
from nltk.tokenize import word_tokenize

# Ensure you have the necessary NLTK data
nltk.download('punkt')
url = 'https://api.fireflies.ai/graphql'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer 69d8ba25-6900-4e36-8185-392da42a3d90'
}
data = '{"query": "query Transcript($transcriptId: String!) { transcript(id: $transcriptId) { title id sentences{speaker_name text}} }", "variables": {"transcriptId": "01JRB3FFPDHVYFN1CMK38307K6"}}'

response = requests.post(url, headers=headers, data=data)

sentences = response.json()['data']['transcript']['sentences']

transcript = ''
for i in sentences:
    transcript += i['speaker_name'] + '-' + i['text'] + ' '

tokens = word_tokenize(transcript)
token_count = len(tokens)
print(f"Token count: {token_count}")