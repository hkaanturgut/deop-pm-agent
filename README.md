# 🤖 Deop PM Agent

AI-powered Project Management Agent for Microsoft Teams — built with Teams SDK v2, Azure AI Foundry (GPT-4o), Cosmos DB, and the Memory Module.

> **Built by [deop.ca](https://deop.ca)** — DevOps consulting, simplified.

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────────────────┐
│  Teams User │ ←→  │  Azure Bot Svc   │ ←→  │  Python App (App Service)    │
└─────────────┘     │  (F0 free tier)  │     │                              │
                    └──────────────────┘     │  ┌─ Teams SDK v2 (bot logic) │
                                              │  ├─ GPT-4o (AI Foundry)     │
┌─────────────┐                               │  ├─ Memory Module (context) │
│  Outlook    │ ←→  Microsoft Graph  ←──────→ │  ├─ Graph API (calendar)    │
│  Calendar   │     (SSO / OBO flow)          │  └─ Cosmos DB (data store)  │
└─────────────┘                               └──────────────────────────────┘
```

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📋 **Task Management** | Create, update, assign, and track tasks across projects and clients |
| 📊 **Project Status** | Real-time progress and blocker visibility per client |
| 📅 **Meeting Prep** | Auto-summarize relevant context before meetings (pulls from Outlook calendar via SSO) |
| 📝 **Daily Standups** | LLM-generated summaries aggregating updates across all projects |
| ⏰ **Smart Reminders** | Proactive alerts for overdue tasks, approaching deadlines, and blockers |
| 📈 **Client Reports** | Auto-generate professional status reports per client |
| 🧠 **Conversation Memory** | Remembers client preferences, project context, and meeting history |
| 🔐 **Teams SSO** | On-behalf-of flow for accessing user's calendar without extra sign-in |

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- **Azure subscription** with:
  - Azure AI Foundry (OpenAI) — GPT-4o + text-embedding-3-small
  - Cosmos DB (serverless)
  - App Service (B1 Linux)
  - Azure Bot Service (F0)
  - Key Vault
- **Microsoft Teams** with sideloading enabled (or M365 dev tenant)
- **Azure CLI** (`az`) and **GitHub CLI** (`gh`)

### 1. Clone & Install

```bash
git clone https://github.com/hkaanturgut/deop-pm-agent.git
cd deop-pm-agent
cp sample.env .env
# Fill in your .env values (see Configuration section below)
pip install -r requirements.txt
```

### 2. Deploy Infrastructure (Bicep)

```bash
# Register the bot app in Entra ID
chmod +x infra/scripts/register-bot-app.sh
./infra/scripts/register-bot-app.sh

# Deploy Azure resources
az deployment sub create \
  --location canadacentral \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json \
  --parameters botAppId=$BOT_APP_ID botAppPassword=$BOT_APP_PASSWORD
```

### 3. Run Locally

```bash
# Start the bot
python3 app.py

# In another terminal, start a dev tunnel (for Teams to reach localhost)
devtunnel host -p 3978 --allow-anonymous
```

### 4. Sideload in Teams

1. Zip the `appPackage/` folder contents (manifest.json + icons)
2. In Teams → Apps → Manage your apps → Upload a custom app
3. Select the zip and start chatting with the agent!

## ⚙️ Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_ID` | Bot's Entra ID App ID | ✅ |
| `BOT_PASSWORD` | Bot's client secret | ✅ |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | ✅ |
| `AZURE_OPENAI_DEPLOYMENT` | GPT-4o deployment name | ✅ |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model deployment | ✅ |
| `AZURE_OPENAI_API_BASE` | Azure OpenAI endpoint URL | ✅ |
| `AZURE_OPENAI_API_VERSION` | API version (e.g. `2024-08-01-preview`) | ✅ |
| `COSMOS_ENDPOINT` | Cosmos DB account endpoint | ✅ |
| `COSMOS_KEY` | Cosmos DB key (or use Managed Identity) | ✅ |
| `COSMOS_DATABASE` | Database name (default: `deop-pm-db`) | |
| `GRAPH_CLIENT_ID` | Graph app client ID (for app-only fallback) | |
| `GRAPH_CLIENT_SECRET` | Graph app client secret | |
| `GRAPH_TENANT_ID` | Entra ID tenant ID | |
| `SSO_CONNECTION_NAME` | OAuth connection name in Bot Service (default: `GraphConnection`) | |

## 📁 Project Structure

```
deop-pm-agent/
├── app.py                        # aiohttp entry point + health check
├── bot.py                        # Bot config, middleware, event handlers
├── config.py                     # Environment variable configuration
├── pm_agent/
│   ├── agent.py                  # Base Agent ABC class
│   ├── primary_agent.py          # PMAgent orchestrator with tool dispatch
│   ├── prompts.py                # System prompt & agent persona
│   ├── models.py                 # Pydantic models (Task, Project, Client)
│   ├── cosmos_client.py          # Cosmos DB async CRUD operations
│   ├── graph_client.py           # Microsoft Graph calendar client (SSO + app-only)
│   ├── smart_features.py         # Standup, reports, reminders, meeting prep
│   ├── adaptive_cards.py         # Adaptive Card templates for Teams UI
│   ├── auth.py                   # Teams SSO / On-behalf-of auth
│   └── tools.py                  # Tool schemas & function definitions
├── infra/
│   ├── main.bicep                # Main Bicep orchestrator
│   ├── main.parameters.json      # Default parameter values
│   ├── modules/
│   │   ├── identity.bicep        # User-assigned Managed Identity
│   │   ├── monitoring.bicep      # Log Analytics + App Insights
│   │   ├── key-vault.bicep       # Key Vault with RBAC
│   │   ├── ai-foundry.bicep      # Azure OpenAI + model deployments
│   │   ├── cosmos-db.bicep       # Cosmos DB (serverless) + containers
│   │   ├── app-service.bicep     # App Service Plan + Web App
│   │   └── bot-service.bicep     # Bot Service + Teams channel
│   └── scripts/
│       └── register-bot-app.sh   # Entra ID app registration script
├── appPackage/
│   └── manifest.json             # Teams app manifest (v1.17)
├── tests/
│   └── test_models.py            # Unit tests for data models
├── .github/
│   └── workflows/
│       └── ci-cd.yml             # Lint → Test → Deploy pipeline
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Project metadata
└── sample.env                    # Environment variable template
```

## 🧰 Azure Resources

| Resource | SKU/Tier | Purpose |
|----------|----------|---------|
| Azure AI Foundry (OpenAI) | GPT-4o + text-embedding-3-small | LLM reasoning + memory embeddings |
| Cosmos DB | Serverless | Tasks, projects, clients data store |
| App Service | B1 Linux (Python 3.12) | Host the bot application |
| Azure Bot Service | F0 (free) | Teams channel registration |
| Key Vault | Standard | Secrets management (RBAC-based) |
| Application Insights | Pay-as-you-go | Monitoring & diagnostics |
| Managed Identity | User-assigned | Passwordless auth to Azure resources |

## 🔒 Security

- **Managed Identity** with RBAC for all Azure resource access
- **No local auth** on Cosmos DB (`disableLocalAuth: true`)
- **Key Vault references** for bot password in App Service
- **Teams SSO** with on-behalf-of flow for Graph access
- **OIDC** federated credentials for GitHub Actions deployment

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push and open a PR

## 📜 License

MIT
