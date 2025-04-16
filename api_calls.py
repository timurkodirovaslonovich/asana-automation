import requests
import os
import json

ASANA_PAT = "2/1209909519983743/1209911182091554:d83f97c5c730ce7ddcb871b0af84a2ab"

headers = {
    "Authorization": f"Bearer {ASANA_PAT}"
}

response = requests.get(
    "https://app.asana.com/api/1.0/users?opt_fields=name,email",
    headers=headers
)

try:
    data = response.json()
    if "data" in data:
        users = data["data"]
        for user in users:
            name = user.get("name", "Unnamed")
            email = user.get("email", "N/A")
            gid = user.get("gid", "N/A")
            print(f"{name} ({email}): {gid}")
    else:
        print("❌ Unexpected response format:")
        print(data)
except ValueError:
    print("❌ Failed to parse JSON.")
    print("Raw response:", response.text)
