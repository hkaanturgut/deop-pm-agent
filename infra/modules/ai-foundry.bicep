// Azure OpenAI (AI Foundry) — GPT-4o + Embeddings

@description('Base name for resources')
param baseName string

@description('Azure region for OpenAI (may differ from other resources due to model availability)')
param location string

@description('Resource tags')
param tags object

@description('Chat model deployment name')
param openAiModelName string

@description('Embedding model deployment name')
param embeddingModelName string

@description('Managed Identity principal ID for RBAC')
param managedIdentityPrincipalId string

resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${baseName}-oai'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${baseName}-oai'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// GPT-4o deployment
resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: openAiModelName
  sku: {
    name: 'GlobalStandard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

// Embedding model deployment
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: embeddingModelName
  sku: {
    name: 'GlobalStandard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
  }
  dependsOn: [chatDeployment]
}

// Grant Managed Identity Cognitive Services OpenAI User role
resource openAiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAi.id, managedIdentityPrincipalId, 'CognitiveServicesOpenAIUser')
  scope: openAi
  properties: {
    principalId: managedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalType: 'ServicePrincipal'
  }
}

output endpoint string = openAi.properties.endpoint
output name string = openAi.name
