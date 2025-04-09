import os
import json
import requests
import time
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
ASANA_API_URL = "https://app.asana.com/api/1.0/tasks"

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
    "rasul": "Senior ai developer and data analyst",
    "Ogabek": "outsorce developer and ui designer",
    "shohruh": "Responsible for engineering architecture",
    "timur": "junior ai developer",
    "Sarvar": "unior ai developer",
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

# === Azure OpenAI model setup
model = AzureChatOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_deployment=AZURE_DEPLOYMENT_NAME,
    temperature=0
)

def get_ai_assignee(action_item, context_summary, transcript):
    team_description = "\n".join([f"- {name}: {role}" for name, role in TEAM_RESPONSIBILITIES.items()])
    prompt = f"""
You are an assistant. Based on the task below, return the best-matching team member from the list.

Team:
{team_description}

Action Item:
{action_item}

Meeting Summary:
{context_summary}



Respond ONLY with one team member's first name (lowercase). No explanation.
"""
    try:
        result = model.invoke(prompt)
        name = result.content.strip().lower()
        return name if name in NAME_TO_EMAIL else None
    except Exception as e:
        print("❌ Azure OpenAI (assignee) error:", e)
        return None


def get_ai_project(action_item, context_summary, transcript):
    project_description = "\n".join(
        [f'- "{key}": {desc}' for key, desc in PROJECT_DESCRIPTIONS.items()]
    )

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

def save_transcript_to_file(transcript_text, title):
    os.makedirs("transcripts", exist_ok=True)
    filename = f"transcripts/{title.replace(' ', '_').lower()}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(transcript_text)
    print(f"📝 Saved transcript to {filename}")

def append_training_example(action_item, summary, project_keyword):
    os.makedirs("training", exist_ok=True)
    prompt = f"Action Item: {action_item}\nSummary: {summary}"
    training_data = {
        "messages": [
            {"role": "system", "content": "You are a strict project classifier. You return one keyword or 'default'."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": project_keyword}
        ]
    }
    with open("training/project_training.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(training_data) + "\n")
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
        res = requests.post(FIREFLIES_API_URL, json={"query": query, "variables": {"id": transcript_id}}, headers=headers)
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

def identify_meeting_scheduling_actions(text):
    keywords = ["schedule", "set up", "book", "organize", "follow-up", "meeting", "sync", "call", "demo"]
    return [line.strip("-* ").strip() for line in text.splitlines() if any(k in line.lower() for k in keywords)]

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

    # ✅ Save transcript
    save_transcript_to_file(full_transcript, title)

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

        # ✅ Save training data
        append_training_example(action_item, summary, project_keyword)

        result = create_asana_task(task_name, description, project_id, assignee_gid)
        if result and "data" in result:
            print(f"✅ Created Asana task: {result['data']['gid']}")
        else:
            print(f"❌ Failed to create task for: '{action_item}'")

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
