// App Service Plan + Web App for hosting the Python bot

@description('Base name for resources')
param baseName string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('User-assigned Managed Identity resource ID')
param managedIdentityId string

@description('User-assigned Managed Identity client ID')
param managedIdentityClientId string

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Cosmos DB endpoint')
param cosmosEndpoint string

@description('Azure OpenAI endpoint')
param openAiEndpoint string

@description('Azure OpenAI chat model deployment name')
param openAiModelName string

@description('Azure OpenAI embedding model deployment name')
param embeddingModelName string

@description('Bot App ID (Entra ID)')
param botAppId string

@description('Key Vault name for secret references')
param keyVaultName string

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${baseName}-plan'
  location: location
  tags: tags
  kind: 'linux'
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  properties: {
    reserved: true
  }
}

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: '${baseName}-app'
  location: location
  tags: tags
  kind: 'app,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      pythonVersion: '3.12'
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'python app.py'
      alwaysOn: true
      ftpsState: 'Disabled'
      appSettings: [
        { name: 'BOT_ID', value: botAppId }
        { name: 'BOT_PASSWORD', value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=BotAppPassword)' }
        { name: 'AZURE_OPENAI_API_BASE', value: openAiEndpoint }
        { name: 'AZURE_OPENAI_DEPLOYMENT', value: openAiModelName }
        { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: embeddingModelName }
        { name: 'AZURE_OPENAI_API_VERSION', value: '2024-08-01-preview' }
        { name: 'COSMOS_ENDPOINT', value: cosmosEndpoint }
        { name: 'COSMOS_DATABASE', value: 'deop-pm-db' }
        { name: 'AZURE_CLIENT_ID', value: managedIdentityClientId }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
      ]
    }
  }
}

output defaultHostName string = 'https://${webApp.properties.defaultHostName}'
output name string = webApp.name
