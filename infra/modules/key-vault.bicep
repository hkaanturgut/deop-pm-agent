// Key Vault for secrets management

@description('Base name for resources')
param baseName string

@description('Azure region')
param location string

@description('Resource tags')
param tags object

@description('Managed Identity principal ID for RBAC')
param managedIdentityPrincipalId string

@secure()
@description('Bot app password to store')
param botAppPassword string

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${baseName}-kv'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true
  }
}

// Grant Managed Identity Key Vault Secrets User role
resource kvSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentityPrincipalId, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    principalId: managedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalType: 'ServicePrincipal'
  }
}

// Store bot password as secret
resource botPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'BotAppPassword'
  properties: {
    value: botAppPassword
  }
}

output name string = keyVault.name
output uri string = keyVault.properties.vaultUri
