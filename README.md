# 🤖 Deop PM Agent

AI-powered Project Management Agent for Microsoft Teams — built with Teams SDK v2, Azure AI Foundry, and Cosmos DB.

## 🏗️ Architecture

```
Teams User ↔ Azure Bot Service ↔ Python App (App Service)
                                       ├── Teams SDK v2 (bot logic)
                                       ├── Azure AI Foundry / GPT-4o (LLM)
                                       ├── Memory Module (conversation memory)
                                       ├── Microsoft Graph (calendar, meetings)
                                       └── Cosmos DB (tasks, projects, clients)
```

## ✨ Features

- 📋 **Task Management** — Create, update, track tasks across projects and clients
- 📊 **Project Status** — Real-time progress and blocker visibility per client
- 📅 **Meeting Prep** — Auto-summarize context before meetings
- 📝 **Daily Standups** — Aggregate updates across all projects
- ⏰ **Smart Reminders** — Proactive overdue/deadline notifications
- 🧠 **Memory** — Remembers client preferences and project context

## 🚀 Getting Started

> Full setup guide coming soon.

### Prerequisites

- Python 3.12+
- Azure subscription with AI Foundry & Cosmos DB
- Microsoft Teams with sideloading enabled
- Node.js (for Teams Test Tool)

### Quick Start

```bash
# Clone and install
git clone https://github.com/hkaanturgut/deop-pm-agent.git
cd deop-pm-agent
cp sample.env .env
# Fill in .env values
uv sync  # or pip install -r requirements.txt
python app.py
```

## 📁 Project Structure

```
deop-pm-agent/
├── app.py                    # Application entry point
├── bot.py                    # Bot config & middleware
├── config.py                 # Environment configuration
├── pm_agent/                 # Core agent logic
│   ├── agent.py              # Base agent class
│   ├── primary_agent.py      # Main PM orchestrator
│   ├── prompts.py            # System prompts & persona
│   ├── models.py             # Cosmos DB data models
│   ├── cosmos_client.py      # Cosmos DB CRUD operations
│   └── tools.py              # Agent tool definitions
├── infra/                    # Bicep IaC modules
├── appPackage/               # Teams app manifest
├── tests/                    # Test suite
└── .github/workflows/        # CI/CD pipelines
```

## 📜 License

MIT
