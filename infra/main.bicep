// Deop PM Agent — Main Infrastructure Deployment
// Deploys all Azure resources for the Teams PM Agent

targetScope = 'resourceGroup'

@description('Base name for all resources')
param baseName string = 'deoopmagent'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Azure region for OpenAI (model availability varies by region)')
param openAiLocation string = 'eastus2'

@description('Bot display name in Teams')
param botDisplayName string = 'Deop PM Agent'

@description('Microsoft App ID for the bot (Entra ID app registration)')
param botAppId string

@secure()
@description('Microsoft App Password for the bot')
param botAppPassword string

@description('Azure OpenAI model deployment name')
param openAiModelName string = 'gpt-4o'

@description('Azure OpenAI embedding model deployment name')
param embeddingModelName string = 'text-embedding-3-small'

@description('Tags applied to all resources')
param tags object = {
  project: 'deop-pm-agent'
  environment: 'dev'
  managedBy: 'bicep'
}

// --- Managed Identity ---
module identity 'modules/identity.bicep' = {
  name: 'identity-deployment'
  params: {
    baseName: baseName
    location: location
    tags: tags
  }
}

// --- Monitoring (Log Analytics + App Insights) ---
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  params: {
    baseName: baseName
    location: location
    tags: tags
  }
}

// --- Key Vault ---
module keyVault 'modules/key-vault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    baseName: baseName
    location: location
    tags: tags
    managedIdentityPrincipalId: identity.outputs.principalId
    botAppPassword: botAppPassword
  }
}

// --- Azure OpenAI (AI Foundry) ---
module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'ai-foundry-deployment'
  params: {
    baseName: baseName
    location: openAiLocation
    tags: tags
    openAiModelName: openAiModelName
    embeddingModelName: embeddingModelName
    managedIdentityPrincipalId: identity.outputs.principalId
  }
}

// --- Cosmos DB ---
module cosmosDb 'modules/cosmos-db.bicep' = {
  name: 'cosmos-db-deployment'
  params: {
    baseName: baseName
    location: location
    tags: tags
    managedIdentityPrincipalId: identity.outputs.principalId
  }
}

// --- App Service ---
module appService 'modules/app-service.bicep' = {
  name: 'app-service-deployment'
  params: {
    baseName: baseName
    location: location
    tags: tags
    managedIdentityId: identity.outputs.id
    managedIdentityClientId: identity.outputs.clientId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    cosmosEndpoint: cosmosDb.outputs.endpoint
    openAiEndpoint: aiFoundry.outputs.endpoint
    openAiModelName: openAiModelName
    embeddingModelName: embeddingModelName
    botAppId: botAppId
    keyVaultName: keyVault.outputs.name
  }
}

// --- Bot Service ---
module botService 'modules/bot-service.bicep' = {
  name: 'bot-service-deployment'
  params: {
    baseName: baseName
    location: location
    tags: tags
    botAppId: botAppId
    botDisplayName: botDisplayName
    appServiceEndpoint: appService.outputs.defaultHostName
  }
}

// --- Outputs ---
output appServiceUrl string = appService.outputs.defaultHostName
output cosmosEndpoint string = cosmosDb.outputs.endpoint
output openAiEndpoint string = aiFoundry.outputs.endpoint
output botServiceName string = botService.outputs.name
output keyVaultName string = keyVault.outputs.name
output managedIdentityClientId string = identity.outputs.clientId
