import os
import requests
import openai
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

# Load environment variables
load_dotenv()

FIREFLIES_API_KEY = os.getenv("FIREFLIES_API_KEY")
ASANA_PAT = os.getenv("ASANA_PAT")
ASANA_PROJECT_GID = os.getenv("ASANA_PROJECT_GID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

FIREFLIES_API_URL = "https://api.fireflies.ai/graphql"
ASANA_API_URL = "https://app.asana.com/api/1.0/tasks"

openai.api_key = OPENAI_API_KEY

# === Constants (unchanged) ===
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
    "archimedes": "1209857166278765",
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
    "Ogabek": "oshomurotov@omadligroup.com",
    "timur": "tkodirov@omadligroup.com",
    "Sarvar": "sruzikulov@omadligroup.com",
    "rico": "rmukhammadjonov@omadligroup.com",
    "omadli": "og@omadligroup.com",
    "dordzhi": "dlidzhiev@omadligroup.com",
    "victoria": "vtailor@omadligroup.com",
    "ian": "iforsythe@omadligroup.com",
    "zulfiya": "zforsythe@omadligroup.com",
    "Muhammadqodir": "msotvoldiyev@omadligroup.com",
    "Shohruh": "smamatov@omadligroup.com",
    "Sukhrob": "syusup@omadligroup.com"
}

TEAM_RESPONSIBILITIES = {
    "rasul": "Leads AI projects and integrations",
    "Ogabek": "Manages sales and client relationships",
    "shohruh": "Responsible for engineering architecture",
    "timur": "Handles data analytics and reporting",
    "Sarvar": "Project and operations manager",
    "dordzhi": "Customer support and onboarding",
}

# === OpenAI Functions ===
def get_ai_assignee(action_item, context_summary, transcript):
    team_description = "\n".join([f"- {name}: {role}" for name, role in TEAM_RESPONSIBILITIES.items()])
    prompt = f"""
Action Item:
{action_item}

Summary:
{context_summary}

Transcript:
{transcript}

Team:
{team_description}

Respond only with the best-suited team member's first name (lowercase).
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        name = response["choices"][0]["message"]["content"].strip().lower()
        return name if name in NAME_TO_EMAIL else None
    except Exception as e:
        print("❌ OpenAI (assignee) error:", e)
        return None

def get_ai_project(action_item, context_summary, transcript):
    prompt = f"""
Available project keywords: {', '.join(PROJECT_ROUTING.keys())}

Action Item:
{action_item}

Summary:
{context_summary}

Transcript:
{transcript}

Return only the best-matching project keyword from the list, or "default" if no match.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        keyword = response["choices"][0]["message"]["content"].strip().lower()
        return keyword if keyword in PROJECT_ROUTING else "default"
    except Exception as e:
        print("❌ OpenAI (project) error:", e)
        return "default"

# === Fireflies ===
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
            json={"query": query, "variables": {"id": transcript_id}},
            headers=headers
        )
        return res.json()["data"]["transcript"]
    except Exception as e:
        print("❌ Fireflies summary error:", e)
        return None

# === Asana with Retry ===
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
        print("⏳ Timeout. Retrying after 3 seconds...")
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

def identify_meeting_scheduling_actions(text):
    keywords = ["schedule", "set up", "book", "organize", "follow-up", "meeting", "sync", "call", "demo"]
    return [line.strip("-* ").strip() for line in text.splitlines() if any(k in line.lower() for k in keywords)]

# === Main Runner ===
def main():
    transcript_id = get_latest_transcript_id()
    if not transcript_id:
        return

    transcript = get_fireflies_meeting_summary(transcript_id)
    if not transcript:
        return

    title = transcript.get("title", "Untitled")
    summary = transcript["summary"].get("overview", "")
    action_items = transcript["summary"].get("action_items", "")
    full_transcript = f"{title}\n{summary}\n{action_items}"
    attendees = transcript.get("meeting_attendees", [])
    attendees_str = ", ".join([a.get("displayName") or a.get("email", "") for a in attendees])
    meeting_link = transcript.get("meeting_link", "")

    actions = identify_meeting_scheduling_actions(action_items)
    if not actions:
        print("✅ No relevant action items.")
        return

    for action_item in actions:
        print(f"\n📝 Processing: {action_item}")
        task_name = f"Schedule: {action_item[:100]}"
        description = (
            f"**Action Item from meeting:** {title}\n\n"
            f"**What to do:** {action_item}\n\n"
            f"**Attendees:** {attendees_str}\n"
            f"**Meeting Link:** {meeting_link}\n\n"
            f"**Summary:**\n{summary}"
        )

        # AI-powered routing
        ai_name = get_ai_assignee(action_item, summary, full_transcript)
        assignee_email = NAME_TO_EMAIL.get(ai_name)
        assignee_gid = ASSIGNEE_ROUTING.get(assignee_email)

        if assignee_gid:
            print(f"🤖 Assigned to: {ai_name} → {assignee_email}")
        else:
            print("⚠️ No valid assignee found.")

        project_keyword = get_ai_project(action_item, summary, full_transcript)
        project_id = PROJECT_ROUTING.get(project_keyword, PROJECT_ROUTING["default"])
        print(f"📁 Project chosen: {project_keyword} → {project_id}")

        result = create_asana_task(task_name, description, project_id, assignee_gid)
        if result and "data" in result:
            print(f"✅ Created Asana task: {result['data']['gid']}")
        else:
            print(f"❌ Failed to create task for: '{action_item}'")

if __name__ == "__main__":
    if not FIREFLIES_API_KEY or not ASANA_PAT or not ASANA_PROJECT_GID or not OPENAI_API_KEY:
        print("❌ Missing required environment variables.")
    else:
        main()
