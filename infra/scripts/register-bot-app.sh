#!/bin/bash
# Register an Entra ID application for the Teams Bot
# Usage: ./register-bot-app.sh [app-name]

set -euo pipefail

APP_NAME="${1:-deop-pm-agent-bot}"

echo "🔐 Registering Entra ID application: $APP_NAME"

# Create the app registration
APP_ID=$(az ad app create \
  --display-name "$APP_NAME" \
  --sign-in-audience "AzureADMyOrg" \
  --query appId -o tsv)

echo "✅ App registered with ID: $APP_ID"

# Create a client secret
SECRET=$(az ad app credential reset \
  --id "$APP_ID" \
  --display-name "bot-secret" \
  --query password -o tsv)

echo "🔑 Client secret created (save this — it won't be shown again)"

# Add Microsoft Graph permissions (Calendars.Read, Mail.Read)
echo "📅 Adding Microsoft Graph permissions..."

# Calendars.Read (delegated) - ID: 465a38f9-76ea-45b9-9f34-9e8b0d4b0b42
az ad app permission add \
  --id "$APP_ID" \
  --api "00000003-0000-0000-c000-000000000000" \
  --api-permissions "465a38f9-76ea-45b9-9f34-9e8b0d4b0b42=Scope" 2>/dev/null || true

# Calendars.Read (application) - ID: 798ee544-9d2d-430c-a058-570e29e34338
az ad app permission add \
  --id "$APP_ID" \
  --api "00000003-0000-0000-c000-000000000000" \
  --api-permissions "798ee544-9d2d-430c-a058-570e29e34338=Role" 2>/dev/null || true

echo ""
echo "========================================="
echo "📋 Save these values for your .env file:"
echo "========================================="
echo "BOT_ID=$APP_ID"
echo "BOT_PASSWORD=$SECRET"
echo "GRAPH_CLIENT_ID=$APP_ID"
echo "GRAPH_CLIENT_SECRET=$SECRET"
echo "GRAPH_TENANT_ID=$(az account show --query tenantId -o tsv)"
echo "========================================="
echo ""
echo "⚠️  Next steps:"
echo "  1. Grant admin consent: az ad app permission admin-consent --id $APP_ID"
echo "  2. Update infra/main.parameters.json with the BOT_ID and BOT_PASSWORD"
echo "  3. Update your .env file with the values above"
