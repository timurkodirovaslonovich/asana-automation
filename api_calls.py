import requests
import os
import json

ASANA_PAT = "2/1209909519983743/1209911182091554:d83f97c5c730ce7ddcb871b0af84a2ab"

import requests

url = 'https://api.fireflies.ai/graphql'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer 69d8ba25-6900-4e36-8185-392da42a3d90}'
}
data = '{"query": "query Transcript($transcriptId: String!) { transcript(id: $transcriptId) { title id } }", "variables": {"transcriptId": "your_transcript_id"}}'

response = requests.post(url, headers=headers, data=data)
print(response.json())