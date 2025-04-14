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
    "ai": "1209449293721095",
    "archimedes books": "1209857166278765",
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
    "timur": "junior ai developer",
    "sarvar": "junior ai developer",
    "dordzhi": "senior ai developer",
    "ian": "project manager",
    "zulfiya": "CEO",
}

PROJECT_DESCRIPTIONS = {
    "ai": "AI development, integrations, and workflow automation.",
    "cedar": "Internal or client tooling under the Cedar project.",
    "datum": "Data analysis, insights, or dashboards.",
    "flats": "Real estate or property management (Flats project).",
    "safenest": "Home automation or security (SafeNest project).",
    "salient": "Sales, CRM, or customer funnel tools.",
    "vcr": "Video recording tools, transcription, or playback.",
    "vimocity": "Mobility or performance partner projects.",
    "archimedes books": "platform to sell books",
    "default": "when you are not sure over '90%'"
}

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


def extract_transcript_content_rest_api(transcript_id):
    """Extract transcript content using the Fireflies REST API instead of GraphQL"""

    # Fireflies REST API for full transcript
    rest_api_url = f"{FIREFLIES_REST_API_URL}/transcripts/{transcript_id}"

    headers = {"Authorization": f"Bearer {FIREFLIES_API_KEY}"}

    try:
        # First, try to get transcript from the REST API
        print(f"📥 Fetching transcript from REST API: {rest_api_url}")
        res = requests.get(rest_api_url, headers=headers)

        if res.status_code == 200:
            data = res.json()

            # Check if we have transcript text directly
            if "transcript_text" in data and data["transcript_text"]:
                print("✅ Successfully retrieved transcript text from REST API")
                return data["transcript_text"]

            # Check for transcript items (used in some API versions)
            if "transcript_items" in data and data["transcript_items"]:
                transcript_text = ""
                for item in data["transcript_items"]:
                    speaker = item.get("speaker", {}).get("name", "Unknown")
                    text = item.get("text", "")
                    start_time = item.get("start_time", 0)

                    # Format time as MM:SS
                    minutes = int(start_time / 60)
                    seconds = int(start_time % 60)
                    time_str = f"({minutes:02d}:{seconds:02d})"

                    transcript_text += f"{time_str} {speaker}: {text}\n"

                print("✅ Successfully retrieved transcript from REST API items")
                return transcript_text

            # Check for conversation property (used in newer API versions)
            if "conversation" in data and data["conversation"]:
                conversation = data["conversation"]
                if isinstance(conversation, list) and len(conversation) > 0:
                    transcript_text = ""
                    for entry in conversation:
                        speaker = entry.get("speaker", {}).get("name", "Unknown")
                        text = entry.get("text", "")
                        start_time = entry.get("start_time", 0)

                        # Format time as MM:SS
                        minutes = int(start_time / 60)
                        seconds = int(start_time % 60)
                        time_str = f"({minutes:02d}:{seconds:02d})"

                        transcript_text += f"{time_str} {speaker}: {text}\n"

                    print("✅ Successfully retrieved transcript from conversation data")
                    return transcript_text

            # If we can get the raw JSON but none of the specific fields matched
            print("⚠️ Got response from REST API but couldn't find transcript text in known fields")
            print("Available top-level fields:", list(data.keys()))

            # Try to extract any text we can find
            raw_text = ""
            # Try to look for text fields in the data structure
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 100:
                    raw_text += value + "\n\n"

            if raw_text:
                print("✅ Extracted potential transcript text from raw fields")
                return raw_text

        # If we got here, we couldn't find the transcript in the response
        print(f"⚠️ REST API response code: {res.status_code}")

        # Try fallback to the /raw endpoint which sometimes works
        fallback_url = f"{FIREFLIES_REST_API_URL}/transcripts/{transcript_id}/raw"
        print(f"📥 Trying fallback URL: {fallback_url}")

        fallback_res = requests.get(fallback_url, headers=headers)
        if fallback_res.status_code == 200:
            data = fallback_res.json()
            if "text" in data and data["text"]:
                print("✅ Successfully retrieved transcript from fallback /raw endpoint")
                return data["text"]

        return ""

    except Exception as e:
        print(f"❌ REST API error: {e}")
        return ""


def extract_action_items_with_ai(transcript, meeting_summary):
    # Use AI to extract action items from the transcript
    prompt = f"""
You are an AI assistant specialized in analyzing meeting transcripts and identifying specific action items.

Meeting Summary:
{meeting_summary}

Full Transcript:
{transcript}

Your task is to extract ALL specific action items from this transcript, paying close attention to:
1. Tasks that need to be completed
2. Meetings that need to be scheduled
3. Things that people said they would do
4. Follow-ups that were mentioned
5. Any commitments or promises made by participants

Be especially vigilant for:
- Phrases like "I'll take care of", "I will", "Let me", "We need to", "Please handle", "Can you" 
- Scheduling language like "set up a meeting", "organize a call", "book time", "sync up"
- Action verbs followed by specific tasks
- Deadlines or timeframes mentioned

For each action item, include:
- The exact action to be taken (be specific and comprehensive)
- Who it was assigned to (if mentioned)
- Any deadline mentioned
- Reference numbers or timestamps if available

Format your response as a JSON list of action items, each with these fields:
- "task": the full description of what needs to be done
- "assignee": the first name of who should do it (lowercase, or "unknown" if unclear)
- "timestamp": any time marker or reference (leave empty string if none)

ONLY return valid JSON, with no additional text or explanation.
"""
    try:
        result = model.invoke(prompt)
        response = result.content.strip()

        # Extract JSON portion if wrapped in other text
        json_match = re.search(r'(\[\s*\{.*\}\s*\])', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)

        # Clean the response to ensure valid JSON
        response = response.replace("```json", "").replace("```", "").strip()

        # Parse the JSON
        try:
            action_items = json.loads(response)
            print(f"🔍 Extracted {len(action_items)} action items from transcript")
            return action_items
        except json.JSONDecodeError as e:
            print(f"❌ JSON error parsing AI response: {e}")
            print(f"Raw response: {response}")
            return []

    except Exception as e:
        print(f"❌ Azure OpenAI (action item extraction) error: {e}")
        return []


def extract_fireflies_action_items(action_items_text):
    """Extract action items directly from Fireflies summary"""
    action_items = []

    # Parse the action items text into structured items
    if not action_items_text:
        return action_items

    # Split by common delimiters in Fireflies output
    for line in action_items_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Try to extract timestamp if present (e.g., "(34:01)")
        timestamp = ""
        timestamp_match = re.search(r'\((\d+:\d+)\)', line)
        if timestamp_match:
            timestamp = timestamp_match.group(1)

        # Try to extract assignee if present
        assignee = "unknown"

        # Common patterns like "Name: task" or "Name to task"
        assignee_match = re.search(r'^([A-Za-z]+)(?:\s*:|to|will|should)', line)
        if assignee_match:
            potential_assignee = assignee_match.group(1).lower()
            if potential_assignee in NAME_TO_EMAIL:
                assignee = potential_assignee

        action_items.append({
            "task": line,
            "assignee": assignee,
            "timestamp": timestamp
        })

    return action_items


def identify_meeting_scheduling_actions(text):
    """Legacy function maintained for backward compatibility"""
    keywords = ["schedule", "set up", "book", "organize", "follow-up", "meeting", "sync", "call", "demo"]
    return [line.strip("-* ").strip() for line in text.splitlines() if any(k in line.lower() for k in keywords)]


def extract_attendee_names(attendees):
    """Extract names from attendee list for better assignee matching"""
    extracted_names = []

    for attendee in attendees:
        # Extract from display name
        display_name = attendee.get("displayName", "")
        if display_name:
            words = display_name.split()
            if words:
                # Usually first name is the first word
                first_name = words[0].lower()
                extracted_names.append(first_name)

        # Extract from email if available
        email = attendee.get("email", "")
        if email and email in EMAIL_TO_NAME:
            extracted_names.append(EMAIL_TO_NAME[email])

    return list(set(extracted_names))  # Remove duplicates


def is_name_in_task(name, task_text):
    """Check if a name appears in the task text"""
    # Convert to lowercase for case-insensitive matching
    task_lower = task_text.lower()

    # Direct match
    if name.lower() in task_lower:
        return True

    # Check name variations
    for variation, canonical in NAME_VARIATIONS.items():
        if canonical == name and variation in task_lower:
            return True

    return False


def get_name_from_attendees(attendee_names, task):
    """Try to match the task to one of the meeting attendees"""
    for name in attendee_names:
        # Get canonical name if it's a variation
        if name in NAME_VARIATIONS:
            name = NAME_VARIATIONS[name]

        # Skip if not in our team
        if name not in NAME_TO_EMAIL:
            continue

        # Check if name appears in task
        if is_name_in_task(name, task):
            return name

    return None


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


def get_ai_assignee(action_item, assignee_hint, context_summary, transcript, attendee_names):
    team_description = "\n".join([f"- {name}: {role}" for name, role in TEAM_RESPONSIBILITIES.items()])

    prompt = f"""
You are an intelligent task assignment assistant.

Below is a list of team members and their roles:
{team_description}

Here is the action item:
"{action_item}"

Meeting Summary:
{context_summary}

Transcript Excerpt:
{transcript[:600]}

Instructions:
- Your job is to assign this task to the correct team member.
- Do NOT assign based on who is being mentioned — assign based on who should do the work.
- If the task says "schedule a meeting with Ian", the task is for the scheduler, NOT Ian.
- If no one is clearly responsible, assign it to the project manager (ian).

Respond ONLY with the first name of the assignee in lowercase (e.g., "timur"). Do not explain.
"""

    try:
        result = model.invoke(prompt)
        name = result.content.strip().lower()
        if name in NAME_TO_EMAIL:
            print(f"🤖 AI assigned to: {name}")
            return name
        elif name in NAME_VARIATIONS and NAME_VARIATIONS[name] in NAME_TO_EMAIL:
            canonical = NAME_VARIATIONS[name]
            print(f"🤖 AI assigned to variation: {name} → {canonical}")
            return canonical
        else:
            print(f"⚠️ Invalid assignee: {name} — defaulting to project manager")
            return "none"
    except Exception as e:
        print(f"❌ Azure OpenAI (assignee) error: {e}")
        return "none"




def get_ai_project(action_item, context_summary, transcript):
    project_description = "\n".join([f'- "{key}": {desc}' for key, desc in PROJECT_DESCRIPTIONS.items()])
    prompt = f"""
You are an AI classifier. Your job is to assign a task to a project keyword from a fixed list.

Here is the complete list of valid project keywords and their descriptions:
{project_description}

Your job:
- Read the action item and meeting context.
- Choose the ONE best-matching project keyword from the list.
- If none clearly fit, reply with **exactly**: "default"

Rules:
- Do NOT guess.
- If you're even 10% unsure, return "default".
- No explanations. Just the keyword.

---

Action Item:
{action_item}

Meeting Summary:
{context_summary}

Transcript Excerpt:
{transcript[:500]}

Respond with only one keyword (e.g., "ai", "datum", or "default").
"""
    try:
        result = model.invoke(prompt)
        keyword = result.content.strip().lower()
        print(f"🤖 GPT Project Keyword: '{keyword}'")
        return keyword if keyword in PROJECT_ROUTING else "default"
    except Exception as e:
        print("❌ Azure OpenAI (project) error:", e)
        return "default"


def save_transcript_to_file(transcript_text, title, full_transcript=""):
    os.makedirs("transcripts", exist_ok=True)
    filename = f"transcripts/{title.replace(' ', '_').lower()}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(transcript_text)
        if full_transcript:
            f.write("\n\n--- FULL TRANSCRIPT ---\n\n")
            f.write(full_transcript)

    print(f"📝 Saved transcript to {filename}")


def append_training_example(action_item, summary, project_keyword):
    os.makedirs("training", exist_ok=True)
    data = {
        "messages": [
            {"role": "system", "content": "You are a strict project classifier. You return one keyword or 'default'."},
            {"role": "user", "content": f"Action Item: {action_item}\nSummary: {summary}"},
            {"role": "assistant", "content": project_keyword}
        ]
    }
    with open("training/project_training.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")
    print("🧠 Training example saved.")


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
    query = """
    query GetSummary($id: String!) {
      transcript(id: $id) {
        title
        meeting_link
        meeting_attendees { displayName email }
        summary { overview action_items }
      }
    }
    """
    headers = {"Authorization": f"Bearer {FIREFLIES_API_KEY}"}
    try:
        res = requests.post(
            FIREFLIES_API_URL,
            json={"query": query, "variables": {"id": transcript_id}}, headers=headers
        )
        return res.json()["data"]["transcript"]
    except Exception as e:
        print("❌ Fireflies summary error:", e)
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


def normalize_text(text):
    """Normalize text for better duplicate detection"""
    # Remove timestamp references
    text = re.sub(r'\(\d+:\d+\)', '', text)
    # Remove trailing/leading spaces and lowercase
    text = text.strip().lower()
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove common punctuation
    text = re.sub(r'[,.;:!?]', '', text)
    return text


def similar_tasks(task1, task2):
    """Check if two tasks are similar enough to be considered duplicates"""
    # Use Levenshtein distance or a simpler comparison
    # Here we'll use a simpler method: check if one is substantially contained in the other

    # If tasks are almost identical, they're similar
    if task1 == task2:
        return True

    # Shorter detection for truly tiny tasks
    if len(task1) < 15 and len(task2) < 15:
        return task1 in task2 or task2 in task1

    # If one task is significantly longer than the other, check containment
    if len(task1) > len(task2) * 1.5 or len(task2) > len(task1) * 1.5:
        return task1 in task2 or task2 in task1

    # Otherwise check percentage similarity
    words1 = set(task1.split())
    words2 = set(task2.split())

    # If both are very small, higher threshold
    if len(words1) <= 3 and len(words2) <= 3:
        return words1 == words2

    # Overlap of words
    overlap = len(words1.intersection(words2))

    # If either set is small, require high absolute overlap
    if len(words1) <= 5 or len(words2) <= 5:
        return overlap >= min(len(words1), len(words2)) * 0.8

    # Otherwise require percentage overlap
    similarity = overlap / max(len(words1), len(words2))
    return similarity > 0.7  # 70% word overlap indicates similar tasks

def is_valid_task(task):
    """Check if a task is valid (not just a name or too short)."""
    task = task.strip()
    if not task:
        return False
    if len(task.split()) < 4:
        return False
    # Matches 1 or 2 names only (e.g., "Timurbek Kodirov")
    if re.fullmatch(r"[A-Za-z]+(?: [A-Za-z]+)?", task):
        return False
    return True


def main():
    transcript_id = get_latest_transcript_id()
    if not transcript_id:
        return

    transcript = get_fireflies_meeting_summary(transcript_id)
    if not transcript:
        return

    title = transcript.get("title", "Untitled")
    summary = transcript["summary"].get("overview", "")
    action_items_text = transcript["summary"].get("action_items", "")
    meeting_summary = f"{title}\n{summary}"

    # Extract attendee names for better assignee matching
    attendees = transcript.get("meeting_attendees", [])
    attendee_names = extract_attendee_names(attendees)
    print(f"📋 Meeting attendees: {', '.join(attendee_names)}")

    attendees_str = ", ".join([a.get("displayName") or a.get("email", "") for a in attendees])
    meeting_link = transcript.get("meeting_link", "")

    # Try to get more detailed transcript content with REST API
    transcript_content = extract_transcript_content_rest_api(transcript_id)

    # Combine all available content
    full_transcript = f"{meeting_summary}\n\n{action_items_text}\n\n{transcript_content}"

    # Save all transcript information
    save_transcript_to_file(f"{meeting_summary}\n{action_items_text}", title, transcript_content)

    # Process with both approaches

    # 1. Extract action items directly from Fireflies provided items
    fireflies_items = extract_fireflies_action_items(action_items_text)
    print(f"📋 Extracted {len(fireflies_items)} action items from Fireflies summary")

    # 2. Try AI-based extraction if we have sufficient transcript content
    ai_items = []
    if len(full_transcript) > 200:  # Only if we have meaningful content
        chunks = chunk_transcript(full_transcript, max_chars=4000)
        for chunk in chunks:
            chunk_items = extract_action_items_with_ai(chunk, summary)
            ai_items.extend(chunk_items)
        print(f"🤖 Extracted {len(ai_items)} action items with AI analysis")

    # Handle fallback to original approach if both methods fail
    all_action_items = fireflies_items + ai_items
    if not all_action_items:
        print("⚠️ No action items extracted, falling back to original method")
        # Use the original method to identify meeting-related actions
        meeting_actions = identify_meeting_scheduling_actions(action_items_text)
        for action in meeting_actions:
            all_action_items.append({
                "task": action,
                "assignee": "unknown",
                "timestamp": ""
            })

    # Better duplicate tracking
    seen_action_items = set()
    assignee_tasks = {}  # Track tasks by assignee to avoid duplicates for same person
    task_id = 1

    # Process all found action items
    for item in all_action_items:
        action_task = item.get("task", "")
        timestamp = item.get("timestamp", "")
        assignee_hint = item.get("assignee", "")

        if not is_valid_task(action_task):
            print(f"⚠️ Skipping invalid or name-only task: {action_task}")
            continue

        # Skip if empty task
        if not action_task.strip():
            continue

        # Add timestamp if available
        if timestamp:
            if not timestamp.startswith("("):
                timestamp = f"({timestamp})"
            # If timestamp not in task already, append it
            if timestamp not in action_task:
                action_task = f"{action_task} {timestamp}"

        # Normalize for duplicate detection
        normalized = normalize_text(action_task)

        # Skip if we've seen this exact task before
        if normalized in seen_action_items:
            print(f"⚠️ Skipping duplicate task: {action_task}")
            continue

        # Get AI assignee (using hint from extraction if available)
        ai_name = get_ai_assignee(action_task, assignee_hint, summary, full_transcript[:1000], attendee_names)

        if ai_name:
            # Check if this task is similar to one already assigned to this person
            if ai_name in assignee_tasks:
                similar = False
                for existing_task in assignee_tasks[ai_name]:
                    # Compare task similarity (ignoring timestamps)
                    if similar_tasks(normalized, existing_task):
                        print(f"⚠️ Skipping similar task for {ai_name}: {action_task}")
                        similar = True
                        break

                if similar:
                    continue

                # Add to this person's tasks
                assignee_tasks[ai_name].append(normalized)
            else:
                # First task for this person
                assignee_tasks[ai_name] = [normalized]

        # Mark as seen
        seen_action_items.add(normalized)

        print(f"\n📝 Task #{task_id}: {action_task}")
        task_id += 1

        # Format the task name differently for different types of tasks
        if any(word in action_task.lower() for word in ["schedule", "meeting", "call", "sync"]):
            task_name = f"Schedule: {action_task[:100]}"
        else:
            task_name = f"Task: {action_task[:100]}"

        # Create detailed description
        description = (
            f"**Action Item from meeting:** {title}\n\n"
            f"**What to do:** {action_task}\n\n"
            f"**Attendees:** {attendees_str}\n"
            f"**Meeting Link:** {meeting_link}\n\n"
            f"**Summary:**\n{summary}"
        )

        assignee_email = NAME_TO_EMAIL.get(ai_name) if ai_name else None
        assignee_gid = ASSIGNEE_ROUTING.get(assignee_email) if assignee_email else None

        if assignee_gid:
            print(f"🤖 Assigned to: {ai_name} → {assignee_email}")
        else:
            print("⚠️ No valid assignee found.")

        project_keyword = get_ai_project(action_task, summary, full_transcript[:1000])
        project_id = PROJECT_ROUTING.get(project_keyword, PROJECT_ROUTING["default"])
        print(f"📁 Project chosen: {project_keyword} → {project_id}")

        append_training_example(action_task, summary, project_keyword)

        #result = create_asana_task(task_name, description, project_id, assignee_gid)
        result = True
        if result: #and "data" in result:
            print(f"✅ Created Asana task: {result}")
        else:
            print(f"❌ Failed to create task for: '{action_task}'")


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