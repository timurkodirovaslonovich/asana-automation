import os
import json
import requests
import time
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from langchain_openai import AzureChatOpenAI

# Load environment variables
load_dotenv()

FIRE_TASKS = []  # will be populated by REST API

# Required keys
FIREFLIES_API_KEY = os.getenv("FIREFLIES_API_KEY")
ASANA_PAT = os.getenv("ASANA_PAT")
ASANA_PROJECT_GID = os.getenv("ASANA_PROJECT_GID")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")

FIREFLIES_API_URL = "https://api.fireflies.ai/graphql"
FIREFLIES_REST_API_URL = "https://api.fireflies.ai/api/v2"
ASANA_API_URL = "https://app.asana.com/api/1.0/tasks"

# Constants (unchanged)
ASSIGNEE_ROUTING = {
    "smamatov@omadligroup.com": "1209776649222589",
    "oshomurotov@omadligroup.com": "1209738173846577",
    "tkodirov@omadligroup.com": "1209909519983743",
    "syusup@omadligroup.com": "1205806229284486",
    "zforsythe@omadligroup.com": "1202686874737490",
    "og@omadligroup.com": "1209738173846574",
    "dlidzhiev@omadligroup.com": "1204598360821384",
    "sruzikulov@omadligroup.com": "1205303290111136",
    "rmukhammadjonov@omadligroup.com": "1209654099637590",
    "rasul@omadligroup.com": "1204013969303087",
    "iforsythe@omadligroup.com": "1209091536692133",
    "vtailor@omadligroup.com": "1209266316106443",
    "ozayniddin@omadligroup.com": "1205607268949601",
    "msotvoldiyev@omadligroup.com": "1209366051319986",
}

PROJECT_ROUTING = {
    "ai workflow proposals": "1209449293721095",
    "ai agents": "1209591504094184",
    "archimedes books": "1209449293721095",
    "cedar": "1206964472917478",
    "datum": "1206352481131276",
    "flats": "1206964472917470",
    "safenest": "1209373081114179",
    "salient": "1208936376148012",
    "vcr": "1204013593345011",
    "vimocity": "1205188790228640",
    "default": ASANA_PROJECT_GID
}

NAME_TO_EMAIL = {
    "rasul": "rasul@omadligroup.com",
    "oybek": "ozayniddin@omadligroup.com",
    "ogabek": "oshomurotov@omadligroup.com",
    "timur": "tkodirov@omadligroup.com",
    "sarvar": "sruzikulov@omadligroup.com",
    "rico": "rmukhammadjonov@omadligroup.com",
    "omadli": "og@omadligroup.com",
    "dordzhi": "dlidzhiev@omadligroup.com",
    "victoria": "vtailor@omadligroup.com",
    "ian": "iforsythe@omadligroup.com",
    "zulfiya": "zforsythe@omadligroup.com",
    "muhammadqodir": "msotvoldiyev@omadligroup.com",
    "shohruh": "smamatov@omadligroup.com",
    "sukhrob": "syusup@omadligroup.com"
}

# Add email-to-name lookup for easier matching
EMAIL_TO_NAME = {email: name for name, email in NAME_TO_EMAIL.items()}

# Additional names mapping for better matching (include variations and capitalizations)
NAME_VARIATIONS = {
    "tim": "timur",
    "timurbek": "timur",
    "ian": "ian",
    "iain": "ian",
    "zulfiya": "zulfiya",
    "dordzhi": "dordzhi",
    "rasul": "rasul",
    "oybek": "oybek",
    "ogabek": "ogabek",
    "sarvar": "sarvar",
    "rico": "rico",
    "omadli": "omadli",
    "victoria": "victoria",
    "vicky": "victoria",
    "muhammadqodir": "muhammadqodir",
    "muhammad": "muhammadqodir",
    "shohruh": "shohruh",
    "sukhrob": "sukhrob"
}

TEAM_RESPONSIBILITIES = {
    "rasul": "Senior ai developer and data analyst",
    "ogabek": "outsource developer and ui designer",
    "shohruh": "Responsible for engineering architecture",
    "timur": "junior ai developer, backend(python) developer",
    "sarvar": "junior ai developer",
    "rico": "junior ai developer",
    "dordzhi": "senior ai developer",
    "ian": "project manager",
    "zulfiya": "CEO",
}


PROJECT_DESCRIPTIONS = {
    "ai workflow proposals": "AI workflow creation, proposal creations for clients.",
    "ai agents": "ai agent development",
    "cedar": "Internal or client tooling under the Cedar project.",
    "datum": "Data analysis, insights, or dashboards.",
    "flats": "Real estate or property management (Flats project).",
    "safenest": "Home automation or security (SafeNest project).",
    "salient": "Sales, CRM, or customer funnel tools.",
    "vcr": "Video recording tools, transcription, or playback.",
    "vimocity": "Mobility or performance partner projects.",
    "archimedes books": "platform to sell books",
    "default": "general tasks, organizational tasks"
}


NAME_TO_EMAIL.update({
    "all team members": None,  # Special case for group assignments
    "timurbek kodirov": "tkodirov@omadligroup.com",
    "rico mukhammadjonov": "rmukhammadjonov@omadligroup.com",
    "sarvar ruzikulov": "sruzikulov@omadligroup.com",
    "dordzhi lidzhiev": "dlidzhiev@omadligroup.com",
    "muhammadqodir sotvoldiyev": "msotvoldiyev@omadligroup.com",
    "ian forsythe": "iforsythe@omadligroup.com"
})

ASSIGNEE_ROUTING.update({
    "tkodirov@omadligroup.com": "1209909519983743",
    "rmukhammadjonov@omadligroup.com": "1209654099637590",
    "sruzikulov@omadligroup.com": "1205303290111136",
    "dlidzhiev@omadligroup.com": "1204598360821384",
    "msotvoldiyev@omadligroup.com": "1209366051319986",
    "iforsythe@omadligroup.com": "1209091536692133"
})

model = AzureChatOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_deployment=AZURE_DEPLOYMENT_NAME,
    temperature=0
)


def chunk_transcript(text, max_chars=4000):
    """Split transcript into overlapping chunks for processing"""
    chunks = []
    text_length = len(text)
    overlap = 500  # Characters of overlap between chunks

    for i in range(0, text_length, max_chars - overlap):
        end = min(i + max_chars, text_length)
        chunk = text[i:end]
        chunks.append(chunk)

        # If we've reached the end, break
        if end == text_length:
            break

    return chunks


# def get_transcript_data_rest_api(transcript_id):
#     """Get all transcript data using only the REST API"""

#     # Fireflies REST API for transcript metadata
#     rest_api_url = f"{FIREFLIES_REST_API_URL}/transcripts/{transcript_id}"
#     print(FIREFLIES_API_KEY)
#     headers = {"Authorization": f"Bearer {FIREFLIES_API_KEY}"}

#     try:
#         print(f"📥 Fetching transcript metadata from REST API: {rest_api_url}")
#         res = requests.get(rest_api_url, headers=headers)

#         if res.status_code != 200:
#             print(f"⚠️ REST API returned status code: {res.status_code}")
#             return None

#         data = res.json()
#         print("✅ Successfully retrieved transcript metadata from REST API")

#         # Create a structure similar to what the GraphQL would have returned
#         transcript = {
#             "title": data.get("title", "Untitled"),
#             "meeting_link": data.get("recording_url", ""),
#             "meeting_attendees": [],
#             "summary": {
#                 "overview": data.get("summary", ""),
#                 "action_items": ""
#             }
#         }

#         # Extract attendees if available
#         if "attendees" in data and isinstance(data["attendees"], list):
#             transcript["meeting_attendees"] = [
#                 {"displayName": attendee.get("name", ""),
#                  "email": attendee.get("email", "")}
#                 for attendee in data["attendees"]
#             ]

#         # Extract action items if available
#         action_items = []

#         # Try various fields where action items might be stored
#         if "action_items" in data and isinstance(data["action_items"], list):
#             action_items.extend([item.get("text", "") for item in data["action_items"] if item.get("text")])

#         if "tasks" in data and isinstance(data["tasks"], list):
#             global FIRE_TASKS
#             FIRE_TASKS = data["tasks"]
#             print(f"📝 Retrieved {len(FIRE_TASKS)} Fireflies 'Tasks'")
#             action_items.extend([task for task in FIRE_TASKS if task])

#         if "ai_insights" in data and isinstance(data["ai_insights"], dict):
#             insights = data["ai_insights"]
#             if "action_items" in insights and isinstance(insights["action_items"], list):
#                 action_items.extend([item for item in insights["action_items"] if item])

#         # Join all action items
#         if action_items:
#             transcript["summary"]["action_items"] = "\n".join(action_items)

#         # Ensure we also have the transcript_text for processing
#         if "transcript_text" in data and data["transcript_text"]:
#             transcript["full_text"] = data["transcript_text"]

#         return transcript

#     except Exception as e:
#         print(f"❌ REST API error: {e}")
#         return None


# def extract_transcript_content_rest_api(transcript_id):
#     """Extract transcript content using the Fireflies REST API instead of GraphQL"""

#     # Fireflies REST API for full transcript
#     rest_api_url = f"{FIREFLIES_REST_API_URL}/transcripts/{transcript_id}"

#     headers = {"Authorization": f"Bearer {FIREFLIES_API_KEY}"}

#     try:
#         # First, try to get transcript from the REST API
#         print(f"📥 Fetching transcript from REST API: {rest_api_url}")
#         res = requests.get(rest_api_url, headers=headers)

#         if res.status_code == 200:
#             data = res.json()

#             # Check if we have transcript text directly
#             if "transcript_text" in data and data["transcript_text"]:
#                 print("✅ Successfully retrieved transcript text from REST API")
#                 if "tasks" in data and isinstance(data["tasks"], list):
#                     global FIRE_TASKS
#                     FIRE_TASKS = data["tasks"]
#                     print(f"📝 Retrieved {len(FIRE_TASKS)} Fireflies 'Tasks'")

#                 return data["transcript_text"]

#             # Check for transcript items (used in some API versions)
#             if "transcript_items" in data and data["transcript_items"]:
#                 transcript_text = ""
#                 for item in data["transcript_items"]:
#                     speaker = item.get("speaker", {}).get("name", "Unknown")
#                     text = item.get("text", "")
#                     start_time = item.get("start_time", 0)

#                     # Format time as MM:SS
#                     minutes = int(start_time / 60)
#                     seconds = int(start_time % 60)
#                     time_str = f"({minutes:02d}:{seconds:02d})"

#                     transcript_text += f"{time_str} {speaker}: {text}\n"

#                 print("✅ Successfully retrieved transcript from REST API items")
#                 return transcript_text

#             # Check for conversation property (used in newer API versions)
#             if "conversation" in data and data["conversation"]:
#                 conversation = data["conversation"]
#                 if isinstance(conversation, list) and len(conversation) > 0:
#                     transcript_text = ""
#                     for entry in conversation:
#                         speaker = entry.get("speaker", {}).get("name", "Unknown")
#                         text = entry.get("text", "")
#                         start_time = entry.get("start_time", 0)

#                         # Format time as MM:SS
#                         minutes = int(start_time / 60)
#                         seconds = int(start_time % 60)
#                         time_str = f"({minutes:02d}:{seconds:02d})"

#                         transcript_text += f"{time_str} {speaker}: {text}\n"

#                     print("✅ Successfully retrieved transcript from conversation data")
#                     return transcript_text

#             # If we can get the raw JSON but none of the specific fields matched
#             print("⚠️ Got response from REST API but couldn't find transcript text in known fields")
#             print("Available top-level fields:", list(data.keys()))

#             # Try to extract any text we can find
#             raw_text = ""
#             # Try to look for text fields in the data structure
#             for key, value in data.items():
#                 if isinstance(value, str) and len(value) > 100:
#                     raw_text += value + "\n\n"

#             if raw_text:
#                 print("✅ Extracted potential transcript text from raw fields")
#                 return raw_text

#         # If we got here, we couldn't find the transcript in the response
#         print(f"⚠️ REST API response code: {res.status_code}")

#         # Try fallback to the /raw endpoint which sometimes works
#         fallback_url = f"{FIREFLIES_REST_API_URL}/transcripts/{transcript_id}/raw"
#         print(f"📥 Trying fallback URL: {fallback_url}")

#         fallback_res = requests.get(fallback_url, headers=headers)
#         if fallback_res.status_code == 200:
#             data = fallback_res.json()
#             if "text" in data and data["text"]:
#                 print("✅ Successfully retrieved transcript from fallback /raw endpoint")
#                 return data["text"]

#         return ""

#     except Exception as e:
#         print(f"❌ REST API error: {e}")
#         return ""

def extract_name_from_text(text):
    """Try to extract team member names from text without assuming they're the assignee"""
    text_lower = text.lower()
    found_names = []

    # Look for exact names first
    for name in NAME_TO_EMAIL.keys():
        # Pattern: name followed by word boundary or possessive
        pattern = rf'\b{re.escape(name)}\b(?:\'s)?'
        if re.search(pattern, text_lower):
            found_names.append(name)

    # Then check variations
    for variation, canonical in NAME_VARIATIONS.items():
        pattern = rf'\b{re.escape(variation)}\b(?:\'s)?'
        if re.search(pattern, text_lower) and canonical in NAME_TO_EMAIL:
            found_names.append(canonical)

    return found_names


def detect_name_context(text, name):
    """Check if name appears in a context indicating they are the ASSIGNEE not just mentioned"""
    text_lower = text.lower()
    name_lower = name.lower()

    # Negative contexts - these indicate the name is NOT the assignee
    negative_contexts = [
        # Someone talking to the person
        rf"(?:call|meeting|sync) with\s+{re.escape(name_lower)}",
        rf"speak(?:\s+to)?\s+{re.escape(name_lower)}",
        rf"(?:talk|chat) to\s+{re.escape(name_lower)}",
        rf"ask\s+{re.escape(name_lower)}",
        # The person is mentioned but not assigned
        rf"about\s+{re.escape(name_lower)}",
        rf"(?:like|as)\s+{re.escape(name_lower)}",
        rf"by\s+{re.escape(name_lower)}"
    ]

    for pattern in negative_contexts:
        if re.search(pattern, text_lower):
            return False

    # Positive contexts - these indicate the name IS the assignee
    positive_contexts = [
        # Direct assignment
        rf"{re.escape(name_lower)}\s+(?:will|should|needs to|has to|is going to)",
        rf"{re.escape(name_lower)}\s+to\s+(?:handle|manage|take care of|do|complete|finish)",
        rf"assign(?:ed)?\s+to\s+{re.escape(name_lower)}",
        rf"{re.escape(name_lower)}(?:'s)?\s+task",
        rf"{re.escape(name_lower)}(?:'s)?\s+responsibility"
    ]

    for pattern in positive_contexts:
        if re.search(pattern, text_lower):
            return True

    # If no clear context, return None (unknown)
    return None

def get_ai_project(transcript):
    project_description = "\n".join([f'- "{key}": {desc}' for key, desc in PROJECT_DESCRIPTIONS.items()])
    prompt = f"""
Your task is to analyze the given transcript and extract actionable tasks in JSON format. Each task must include the following fields:
- "assign_to": The name of the person assigned to the task.
- "task": A clear description of the task.
- "project": The project the task belongs to. Use the project name from the list below if it matches the task context. If you're even 10% unsure, assign the task to the "default" project.

Here is the complete list of valid project keywords and their descriptions:
{project_description}

Rules:
1. Do NOT guess the project. If you're unsure, assign the task to the "default" project.
2. Ensure the JSON is valid and contains no extra text or formatting.
3. If the assignee is unclear, assign the task to "all team members".

---
Transcript Excerpt:
{transcript}

Return only valid JSON in this format:
[
  {{
    "assign_to": "Name of the person assigned to the task",
    "task": "Description of the task",
    "project": "Project name (or 'default' if unsure)"
  }}
]
"""
    try:
        result = model.invoke(prompt)
        tasks = result.content.strip()

        # Debug: Print the raw response
        print("Raw AI Response:")
        print(tasks)

        # Remove any backticks or unwanted characters
        tasks = tasks.replace("```", "").strip()

        # Ensure the response is not empty
        if not tasks:
            print("⚠️ AI model returned an empty response.")
            return "[]"

        # Validate and return the cleaned response
        return tasks
    except Exception as e:
        print("❌ Azure OpenAI (project) error:", e)
        return "[]"

def get_latest_transcript_id():
    query = """query { transcripts(limit: 5) { id title } }"""
    headers = {"Authorization": f"Bearer {FIREFLIES_API_KEY}"}
    try:
        res = requests.post(FIREFLIES_API_URL, json={"query": query}, headers=headers)
        return res.json()["data"]["transcripts"][0]["id"]
    except Exception as e:
        print("❌ Fireflies error:", e)
        return None


def get_fireflies_meeting_summary(transcript_id):
    """Get meeting summary from Fireflies with improved tasks extraction"""
    # First, try a more specific query that might capture tasks data
    query = """
    query Transcript($transcriptId: String!) {
      transcript(id: $transcriptId) {
        id
        title
        sentences {
          speaker_name
          text
        }
        summary {
          overview
          action_items
        }
        ai_filters {
        task
        pricing
        metric
        question
        date_and_time
        text_cleanup
        sentiment
      }
      }
    }
    """
    headers = {"Authorization": f"Bearer {FIREFLIES_API_KEY}"}

    try:
        # Attempt the enhanced query
        res = requests.post(
            FIREFLIES_API_URL,
            json={"query": query, "variables": {"transcriptId": transcript_id}},
            headers=headers
        )

        # Debug the response
        print("📥 Fireflies GraphQL API response (Enhanced Query):")
        print(json.dumps(res.json(), indent=2))

        # Check if we got valid data and no errors
        if "errors" not in res.json() and "data" in res.json() and res.json()["data"]["transcript"]:
            return res.json()["data"]["transcript"]

        # If the enhanced query fails, try the simplified query
        print("⚠️ Enhanced GraphQL query failed, trying simplified query")
        simplified_query = """
        query GetSummary($id: String!) {
          transcript(id: $id) {
            title
            meeting_link
            meeting_attendees { displayName email }
            summary {
              overview
              action_items
            }
          }
        }
        """
        res = requests.post(
            FIREFLIES_API_URL,
            json={"query": simplified_query, "variables": {"id": transcript_id}},
            headers=headers
        )

        # Debug the response
        print("📥 Fireflies GraphQL API response (Simplified Query):")
        print(json.dumps(res.json(), indent=2))

        # Check if we got valid data and no errors
        if "errors" not in res.json() and "data" in res.json() and res.json()["data"]["transcript"]:
            return res.json()["data"]["transcript"]

    except Exception as e:
        print(f"❌ Fireflies error: {e}")

    # If both queries fail, return None
    return None
    

def create_asana_task(task_name, description, project_id, assignee_gid):
    def _post():
        due_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
        payload = {
            "data": {
                "name": task_name,
                "notes": description,
                "projects": [project_id],
                "due_on": due_date
            }
        }
        if assignee_gid:
            payload["data"]["assignee"] = assignee_gid

        headers = {"Authorization": f"Bearer {ASANA_PAT}", "Content-Type": "application/json"}
        return requests.post(ASANA_API_URL, json=payload, headers=headers, timeout=30)

    try:
        res = _post()
        res.raise_for_status()
        return res.json()
    except requests.exceptions.ReadTimeout:
        print("⏳ Timeout. Retrying in 3 seconds...")
        time.sleep(3)
        try:
            res = _post()
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"❌ Second attempt failed: {e}")
            return None
    except Exception as e:
        print(f"❌ Asana task creation error: {e}")
        return None

def main():
    transcript_id = get_latest_transcript_id()
    print(f"Transcript ID: {transcript_id}")
    if not transcript_id:
        print("❌ Failed to retrieve the latest transcript ID.")
        return

    # Get transcript data (will fall back to REST API if GraphQL fails)
    transcript = get_fireflies_meeting_summary(transcript_id)
    if not transcript:
        print("❌ Failed to get transcript data from both GraphQL and REST API")
        return

    # Check if the response contains sentences or summary
    if "sentences" in transcript:
        # Extract detailed transcript content
        transcript_content = ""
        for sentence in transcript["sentences"]:
            speaker_name = sentence.get("speaker_name", "Unknown")
            text = sentence.get("text", "")
            transcript_content += f"{speaker_name}: {text}\n"
    elif "summary" in transcript and "action_items" in transcript["summary"]:
        # Use action items from the summary
        transcript_content = transcript["summary"]["action_items"]
    else:
        print("⚠️ No sentences or action items found in the transcript.")
        return

    print("Transcript Content:")
    print(transcript_content)

    # Process the transcript content to extract tasks
    tasks = get_ai_project(transcript=transcript_content)
    print("Extracted Tasks:")
    print(tasks)

    try:
        # Debugging: Print the raw response
        print("Raw AI Response:")
        print(tasks)
        print(f"Response Length: {len(tasks)}")

        # Remove any backticks or unwanted characters
        tasks = tasks.replace("```", "").strip()

        # Remove the "json" prefix if it exists
        if tasks.startswith("json"):
            tasks = tasks[4:].strip()  # Remove the first 4 characters ("json")

        # Ensure the response is not empty
        if not tasks:
            print("⚠️ AI model returned an empty response.")
            return

        # Parse the tasks into a Python list
        tasks = json.loads(tasks)
        print("Parsed Tasks:")
        print(json.dumps(tasks, indent=4))  # Pretty-print the tasks for debugging

        if not isinstance(tasks, list):
            print("⚠️ Tasks are not in the expected format.")
            return

        if not tasks:
            print("⚠️ No tasks found in the transcript.")
            return

        # Process the tasks
        for task in tasks:
            task_name = task.get("task", "Untitled Task")
            description = task.get("task", "No description provided.")
            print(f"Task: {task_name}, Description: {description}")

            print(f"Project Name from Task: '{task.get('project')}'")  # Print raw project name

            # Normalize the project field
            project_name = task.get("project", "default").strip().lower()

            # Map the project name to a project ID
            project_id = PROJECT_ROUTING.get(project_name, ASANA_PROJECT_GID)

            # Log the mapping process
            print(f"🔍 Mapping project: {project_name} -> {project_id}")

            assignee_email = task.get("assign_to", "")

            # Normalize the assignee email or name
            assignee_name_or_email = task.get("assign_to", "").strip().lower()

            # Try to map the name or email to an email address
            if "@" in assignee_name_or_email:
                assignee_email = assignee_name_or_email
            else:
                # Normalize the name using NAME_VARIATIONS
                normalized_name = NAME_VARIATIONS.get(assignee_name_or_email, assignee_name_or_email)
                assignee_email = NAME_TO_EMAIL.get(normalized_name, None)

            # Check if the assignee is in the routing dictionary
            assignee_gid = ASSIGNEE_ROUTING.get(assignee_email, None)

            # Log the mapping process
            print(f"🔍 Mapping assignee: {assignee_name_or_email} -> {assignee_email} -> {assignee_gid}")

            # Handle missing assignees
            if not assignee_gid:
                if assignee_name_or_email == "all team members":
                    print(f"⚠️ Special case: Assigning 'All Team Members' task to the project manager.")
                    assignee_gid = None
               
                else:
                    print(f"⚠️ Assignee {assignee_name_or_email} not found or not a team member. Creating task without an assignee.")
                    assignee_gid = None

            # Create the task
            print(f"Creating Asana task: {task_name}, Project: {project_name}, Assignee: {assignee_email or 'None'}")
            create_asana_task(task_name, description, project_id, assignee_gid)

    except json.JSONDecodeError as e:
        print(f"❌ Error decoding JSON from AI project response: {e}")
        return

if __name__ == "__main__":
    required = [
        FIREFLIES_API_KEY, ASANA_PAT, ASANA_PROJECT_GID,
        AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
        AZURE_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION
    ]
    if not all(required):
        print("❌ Missing required environment variables.")
    else:
        main()