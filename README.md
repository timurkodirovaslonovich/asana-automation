# Create README.md with structured documentation content
readme_content = """# 🧠 Asana Automation with Azure OpenAI + Fireflies

This project automates daily meeting workflows by:

- 🔍 Extracting meeting action items from [Fireflies.ai](https://fireflies.ai)
- 🧠 Using Azure OpenAI to classify tasks by project and assign them to the right teammate
- 📋 Creating tasks automatically in [Asana](https://asana.com)
- 📝 Logging training data for fine-tuning project classification in the future

---

## 📦 Features

✅ Daily task processing at 6 PM (Uzbekistan time)  
✅ GPT-based assignee and project classification  
✅ Auto-saving transcripts and training data (`.jsonl`)  
✅ Fully integrated with Azure OpenAI and Fireflies API  
✅ Fine-tuning ready for GPT-3.5 Turbo on Azure

---

## 🧰 Tech Stack

- Python 3.10+
- LangChain + Azure OpenAI (`gpt-4` / `gpt-35-turbo`)
- Fireflies.ai GraphQL API
- Asana REST API
- Cron (for scheduling)

---


---

## ⚙️ Setup

1. Clone the repo:
```bash
git clone https://github.com/your-username/asana-automation.git
cd asana-automation
```
## ⚙️ Requirements
pip install -r requirements.txt

## Create .env file

# Fireflies
FIREFLIES_API_KEY=your_fireflies_key

# Asana
ASANA_PAT=your_asana_token
ASANA_PROJECT_GID=your_default_project_id

# Azure OpenAI
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview


## To run every day at 6:00 PM Uzbekistan time:

```angular2html
0 18 * * * python3 /Users/yourname/Desktop/integration/trained_azure.py >> ~/cron_logs/daily.log 2>&1

```

## 📬 Contact

Feel free to reach out if you’d like help configuring this repo or deploying it in production.

— Maintained by https://github.com/timurkodirovaslonovich/


